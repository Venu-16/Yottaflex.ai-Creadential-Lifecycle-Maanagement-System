from __future__ import annotations

import base64
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from sqlalchemy import Integer, cast, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ServiceError
from app.models.domain import (
    Credential,
    CredentialAward,
    CredentialScope,
    EligibilityDecision,
    IdempotencyRecord,
    Issuer,
    IssuerSigningKey,
    Learner,
    Revocation,
)
from app.services.audit import record_event
from app.services.eligibility import canonical_json, evaluate_and_record


def _configured_signing_material(
    db: Session,
) -> tuple[Issuer, IssuerSigningKey, Ed25519PrivateKey]:
    if not (
        settings.credential_signing_private_key
        and settings.credential_signing_issuer_code
        and settings.credential_signing_key_id
    ):
        raise ServiceError(
            503,
            "Credential signing is unavailable; configure issuer, key ID, and private key.",
        )
    try:
        private_bytes = base64.b64decode(
            settings.credential_signing_private_key, validate=True
        )
        private_key = Ed25519PrivateKey.from_private_bytes(private_bytes)
    except (ValueError, TypeError) as exc:
        raise ServiceError(503, "Configured Ed25519 private key is invalid.") from exc
    issuer = db.scalar(
        select(Issuer).where(
            Issuer.issuer_code == settings.credential_signing_issuer_code,
            Issuer.status == "active",
            Issuer.archived_at.is_(None),
        )
    )
    if issuer is None:
        raise ServiceError(503, "Configured active signing issuer is unavailable.")
    key = db.scalar(
        select(IssuerSigningKey).where(
            IssuerSigningKey.issuer_id == issuer.id,
            IssuerSigningKey.key_id == settings.credential_signing_key_id,
            IssuerSigningKey.algorithm == "Ed25519",
            IssuerSigningKey.status == "active",
        )
    )
    if key is None:
        raise ServiceError(503, "Configured active issuer signing key is not registered.")
    public_bytes = private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    if public_bytes != key.public_key or hashlib.sha256(public_bytes).digest() != key.fingerprint:
        raise ServiceError(503, "Configured private key does not match the registered key.")
    now = datetime.now(timezone.utc)
    key_valid_from = _as_utc(key.valid_from)
    key_valid_until = _as_utc(key.valid_until) if key.valid_until else None
    if key_valid_from > now or (key_valid_until is not None and key_valid_until <= now):
        raise ServiceError(503, "Configured issuer signing key is outside its validity period.")
    return issuer, key, private_key


def _allocate_credential_id(db: Session, issued_at: datetime) -> str:
    year = issued_at.astimezone(timezone.utc).year
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(
            select(func.pg_advisory_xact_lock(func.hashtext(f"credential-id-{year}")))
        )
    prefix = f"CRD-{year}-"
    last_number = db.scalar(
        select(func.max(cast(func.substr(Credential.credential_id, 10), Integer))).where(
            Credential.credential_id.like(f"{prefix}%")
        )
    )
    next_number = int(last_number or 0) + 1
    if next_number > 999_999:
        raise ServiceError(409, f"Credential ID sequence for {year} is exhausted.")
    return f"{prefix}{next_number:06d}"


def issue_credential(
    db: Session,
    *,
    learner_id: UUID,
    rule_code: str,
    actor_id: UUID,
    actor_reference: str,
    idempotency_key: str,
) -> Credential:
    if not 8 <= len(idempotency_key) <= 200:
        raise ServiceError(400, "Idempotency-Key must be between 8 and 200 characters.")
    issuer, signing_key, private_key = _configured_signing_material(db)
    learner = db.get(Learner, learner_id)
    if learner is None or learner.archived_at is not None:
        raise ServiceError(404, "Active learner was not found.")
    request_fingerprint = hashlib.sha256(
        canonical_json({"learner_id": str(learner_id), "rule_code": rule_code})
    ).digest()
    key_digest = hashlib.sha256(idempotency_key.encode("utf-8")).digest()
    now = datetime.now(timezone.utc)
    inserted_idempotency_record = True
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        statement = (
            pg_insert(IdempotencyRecord)
            .values(
                id=uuid4(),
                principal_key=str(actor_id),
                operation="credential.issue",
                idempotency_key_digest=key_digest,
                request_fingerprint=request_fingerprint,
                state="in_progress",
                created_at=now,
                expires_at=now + timedelta(hours=24),
            )
            .on_conflict_do_nothing(
                constraint="uq_idempotency_scope_key"
            )
        )
        inserted_idempotency_record = (
            db.execute(statement.returning(IdempotencyRecord.id)).scalar_one_or_none()
            is not None
        )
    else:
        record = IdempotencyRecord(
            id=uuid4(),
            principal_key=str(actor_id),
            operation="credential.issue",
            idempotency_key_digest=key_digest,
            request_fingerprint=request_fingerprint,
            state="in_progress",
            created_at=now,
            expires_at=now + timedelta(hours=24),
        )
        db.add(record)
        db.flush()
    idem = db.scalar(
        select(IdempotencyRecord)
        .where(
            IdempotencyRecord.principal_key == str(actor_id),
            IdempotencyRecord.operation == "credential.issue",
            IdempotencyRecord.idempotency_key_digest == key_digest,
        )
        .with_for_update()
    )
    if idem is None:
        raise ServiceError(503, "Idempotency record could not be established.")
    if idem.request_fingerprint != request_fingerprint:
        raise ServiceError(409, "Idempotency-Key was already used for a different request.")
    if idem.created_at < now - timedelta(hours=24):
        idem.request_fingerprint = request_fingerprint
        idem.state = "in_progress"
        idem.credential_id_fk = None
        idem.created_at = now
        idem.expires_at = now + timedelta(hours=24)
    elif idem.state == "completed" and idem.credential_id_fk is not None:
        existing_result = db.get(Credential, idem.credential_id_fk)
        if existing_result is not None:
            return existing_result
        raise ServiceError(409, "Idempotency record points to a missing credential.")
    elif idem.state == "in_progress" and not inserted_idempotency_record:
        raise ServiceError(409, "An equivalent issuance request is already in progress.")

    decision, reasons, _ = evaluate_and_record(
        db,
        learner=learner,
        rule_code=rule_code,
        evaluator_user_id=actor_id,
        evaluator_reference=actor_reference,
    )
    if decision.outcome != "eligible":
        idem.state = "failed"
        record_event(
            db,
            event_type="credential.issuance_rejected",
            actor_reference=actor_reference,
            actor_user_id=actor_id,
            target_type="learner",
            target_reference=learner.learner_id,
            outcome="rejected",
            reason_code=reasons[0] if reasons else decision.outcome.upper(),
            event_data={"decision_id": str(decision.id), "rule_code": rule_code},
        )
        db.commit()
        raise ServiceError(
            422,
            "Learner is not eligible for issuance: "
            + (", ".join(reasons) if reasons else decision.outcome),
        )
    award = db.scalar(
        select(CredentialAward)
        .where(
            CredentialAward.learner_id == learner.id,
            CredentialAward.credential_scope_id == decision.credential_scope_id,
        )
        .with_for_update()
    )
    if award is None:
        award = CredentialAward(
            id=uuid4(),
            learner_id=learner.id,
            credential_scope_id=decision.credential_scope_id,
        )
        db.add(award)
        db.flush()
    existing_credential = db.scalar(
        select(Credential)
        .where(
            Credential.award_id == award.id,
            Credential.replacement_of_credential_id.is_(None),
        )
        .with_for_update()
    )
    if existing_credential is not None:
        raise ServiceError(
            409,
            "A credential already occupies this learner and credential-scope award slot.",
        )

    issued_at = datetime.now(timezone.utc)
    credential_id = _allocate_credential_id(db, issued_at)
    snapshot = decision.evidence_snapshot
    payload: dict[str, Any] = {
        "credential_id": credential_id,
        "payload_version": "credential-v1",
        "signing_key_id": signing_key.key_id,
        "learner_id": learner.learner_id,
        "course_code": _course_code_for_scope(db, decision.credential_scope_id),
        "issuer": {"issuer_code": issuer.issuer_code, "issuer_name": issuer.name},
        "rule_version": str(decision.rule_version_id),
        "issued_at": issued_at.isoformat(),
        "completion": {
            "completed_at": next(
                (
                    item.get("completed_at")
                    for item in snapshot.get("evidence", [])
                    if "completed_at" in item
                ),
                None,
            )
        },
    }
    payload_bytes = canonical_json(payload)
    digest = hashlib.sha256(payload_bytes).digest()
    try:
        signature = private_key.sign(payload_bytes)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        raise ServiceError(503, "Credential signing failed.") from exc
    credential = Credential(
        id=uuid4(),
        credential_id=credential_id,
        award_id=award.id,
        learner_id=learner.id,
        credential_scope_id=decision.credential_scope_id,
        issuer_id=issuer.id,
        rule_version_id=decision.rule_version_id,
        eligibility_decision_id=decision.id,
        issued_at=issued_at,
        payload_version="credential-v1",
        canonical_payload=payload_bytes,
        sha256_digest=digest,
        signature=signature,
        signature_algorithm="Ed25519",
        signing_key_id=signing_key.id,
    )
    db.add(credential)
    db.flush()
    idem.credential_id_fk = credential.id
    idem.state = "completed"
    record_event(
        db,
        event_type="credential.issued",
        actor_reference=actor_reference,
        actor_user_id=actor_id,
        target_type="credential",
        target_reference=credential_id,
        event_data={"learner_id": learner.learner_id, "rule_code": rule_code},
    )
    db.flush()
    return credential


def _course_code_for_scope(db: Session, scope_id: UUID) -> str:
    from app.models.domain import Course

    course = db.scalar(
        select(Course)
        .join(CredentialScope, CredentialScope.course_id == Course.id)
        .where(CredentialScope.id == scope_id)
    )
    if course is None:
        idem.state = "failed"
        record_event(
            db,
            event_type="credential.issuance_rejected",
            actor_reference=actor_reference,
            actor_user_id=actor_id,
            target_type="learner",
            target_reference=learner.learner_id,
            outcome="rejected",
            reason_code=reasons[0] if reasons else decision.outcome.upper(),
            event_data={"decision_id": str(decision.id), "rule_code": rule_code},
        )
        db.commit()
        raise ServiceError(409, "Credential scope references an unavailable course.")
    return course.course_code


def _verification_record(
    db: Session,
    *,
    mode: str,
    submitted_id: str | None,
    credential: Credential | None,
    issuer: Issuer | None,
    key: IssuerSigningKey | None,
    digest: bytes | None,
    integrity: str,
    trust: str,
    lifecycle: str,
    overall: str,
    requester: str,
) -> str:
    from app.models.domain import VerificationRequest

    now = datetime.now(timezone.utc)
    verification_id = _allocate_verification_id(db, now)
    db.add(
        VerificationRequest(
            id=uuid4(),
            verification_id=verification_id,
            mode=mode,
            submitted_credential_id=submitted_id,
            credential_id_fk=credential.id if credential else None,
            resolved_issuer_id=issuer.id if issuer else None,
            resolved_signing_key_id=key.id if key else None,
            input_digest=digest,
            integrity_result=integrity,
            issuer_trust_result=trust,
            lifecycle_result=lifecycle,
            overall_result=overall,
            requester_reference=requester,
            requested_at=now,
            completed_at=now,
        )
    )
    record_event(
        db,
        event_type="credential.verification",
        actor_reference=requester,
        target_type="credential",
        target_reference=submitted_id,
        outcome=overall.lower(),
        event_data={"mode": mode, "integrity": integrity, "trust": trust, "lifecycle": lifecycle},
    )
    return verification_id


def _allocate_verification_id(db: Session, requested_at: datetime) -> str:
    year = requested_at.astimezone(timezone.utc).year
    prefix = f"VER-{year}-"
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(
            select(func.pg_advisory_xact_lock(func.hashtext(f"verification-id-{year}")))
        )
    from app.models.domain import VerificationRequest

    last_number = db.scalar(
        select(
            func.max(cast(func.substr(VerificationRequest.verification_id, 10), Integer))
        ).where(VerificationRequest.verification_id.like(f"{prefix}%"))
    )
    next_number = int(last_number or 0) + 1
    if next_number > 999_999:
        raise ServiceError(409, f"Verification ID sequence for {year} is exhausted.")
    return f"{prefix}{next_number:06d}"


def _resolve_key(
    db: Session, issuer_code: str | None, key_id: str | None
) -> tuple[Issuer | None, IssuerSigningKey | None]:
    if (
        not isinstance(issuer_code, str)
        or not issuer_code
        or not isinstance(key_id, str)
        or not key_id
    ):
        return None, None
    row = db.execute(
        select(Issuer, IssuerSigningKey)
        .join(IssuerSigningKey, IssuerSigningKey.issuer_id == Issuer.id)
        .where(
            Issuer.issuer_code == issuer_code,
            IssuerSigningKey.key_id == key_id,
            IssuerSigningKey.algorithm == "Ed25519",
        )
    ).first()
    return (row[0], row[1]) if row else (None, None)


def _trust_result(
    issuer: Issuer | None, key: IssuerSigningKey | None, signed_at: datetime | None
) -> str:
    if issuer is None or key is None:
        return "unavailable"
    if len(key.public_key) != 32 or hashlib.sha256(key.public_key).digest() != key.fingerprint:
        return "untrusted"
    if issuer.status != "active" or issuer.archived_at is not None or key.status == "revoked":
        return "untrusted"
    reference_time = _as_utc(signed_at) if signed_at else datetime.now(timezone.utc)
    valid_from = _as_utc(key.valid_from)
    valid_until = _as_utc(key.valid_until) if key.valid_until else None
    if valid_from > reference_time or (
        valid_until is not None and valid_until <= reference_time
    ):
        return "expired"
    if signed_at is None and valid_until is not None and valid_until <= datetime.now(timezone.utc):
        return "expired"
    return "trusted" if key.status in {"active", "retired", "expired"} else "untrusted"


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def verify_credential_id(
    db: Session, credential_id: str, requester: str
) -> dict[str, Any]:
    credential = db.scalar(
        select(Credential).where(Credential.credential_id == credential_id)
    )
    if credential is None:
        verification_id = _verification_record(
            db,
            mode="credential_id",
            submitted_id=credential_id,
            credential=None,
            issuer=None,
            key=None,
            digest=hashlib.sha256(credential_id.encode("utf-8")).digest(),
            integrity="not_found",
            trust="unavailable",
            lifecycle="unknown",
            overall="NOT_FOUND",
            requester=requester,
        )
        db.flush()
        return {
            "verification_id": verification_id,
            "overall_result": "NOT_FOUND",
            "integrity_result": "not_found",
            "issuer_trust_result": "unavailable",
            "lifecycle_result": "unknown",
            "credential_id": credential_id,
            "issuer_code": None,
            "message": "Credential was not found.",
        }
    issuer = db.get(Issuer, credential.issuer_id)
    key = db.get(IssuerSigningKey, credential.signing_key_id)
    integrity = "valid"
    try:
        payload_digest = hashlib.sha256(credential.canonical_payload).digest()
        if payload_digest != credential.sha256_digest:
            integrity = "tampered"
        elif key is None:
            integrity = "unavailable"
        else:
            Ed25519PublicKey.from_public_bytes(key.public_key).verify(
                credential.signature, credential.canonical_payload
            )
    except InvalidSignature:
        integrity = "invalid_signature"
    except ValueError:
        integrity = "unavailable"
    # This is an issuer-registry claim about recorded issuance, not independent timestamp proof.
    trust = _trust_result(issuer, key, credential.issued_at)
    revocation = db.scalar(
        select(Revocation).where(
            Revocation.credential_id == credential.id,
            Revocation.effective_at <= datetime.now(timezone.utc),
        )
    )
    lifecycle = "revoked" if revocation else "active"
    if integrity == "tampered":
        overall = "TAMPERED"
    elif integrity == "invalid_signature":
        overall = "INVALID_SIGNATURE"
    elif integrity != "valid" or trust != "trusted":
        overall = "UNVERIFIABLE"
    elif lifecycle == "revoked":
        overall = "REVOKED"
    else:
        overall = "VALID"
    verification_id = _verification_record(
        db,
        mode="credential_id",
        submitted_id=credential_id,
        credential=credential,
        issuer=issuer,
        key=key,
        digest=hashlib.sha256(credential.canonical_payload).digest(),
        integrity=integrity,
        trust=trust,
        lifecycle=lifecycle,
        overall=overall,
        requester=requester,
    )
    db.flush()
    return {
        "verification_id": verification_id,
        "overall_result": overall,
        "integrity_result": integrity,
        "issuer_trust_result": trust,
        "lifecycle_result": lifecycle,
        "credential_id": credential.credential_id,
        "issuer_code": issuer.issuer_code if issuer else None,
        "message": _verification_message(overall),
    }


def verify_portable_payload(
    db: Session, payload: dict[str, Any], signature_base64: str, requester: str
) -> dict[str, Any]:
    try:
        encoded = canonical_json(payload)
    except (RecursionError, TypeError, ValueError) as exc:
        raise ServiceError(422, "Portable credential payload must contain valid JSON values.") from exc
    digest = hashlib.sha256(encoded).digest()
    credential_id = payload.get("credential_id")
    issuer_claim = payload.get("issuer")
    issuer_code = (
        issuer_claim.get("issuer_code")
        if isinstance(issuer_claim, dict)
        else None
    )
    signing_key_id = payload.get("signing_key_id")
    issuer, key = _resolve_key(db, issuer_code, signing_key_id)
    integrity = "unavailable"
    if key is not None:
        try:
            signature = base64.b64decode(signature_base64, validate=True)
            Ed25519PublicKey.from_public_bytes(key.public_key).verify(signature, encoded)
            integrity = "valid"
        except (InvalidSignature, ValueError):
            integrity = "invalid_signature"
    credential = (
        db.scalar(select(Credential).where(Credential.credential_id == credential_id))
        if isinstance(credential_id, str)
        else None
    )
    if credential is not None and credential.canonical_payload != encoded:
        integrity = "tampered"
    # Portable payload timestamps are self-asserted; they cannot prove historical key validity.
    trust = _trust_result(issuer, key, None)
    lifecycle = "unknown"
    if credential is not None:
        revocation = db.scalar(
            select(Revocation).where(
                Revocation.credential_id == credential.id,
                Revocation.effective_at <= datetime.now(timezone.utc),
            )
        )
        lifecycle = "revoked" if revocation else "active"
    if integrity == "tampered":
        overall = "TAMPERED"
    elif integrity == "invalid_signature":
        overall = "INVALID_SIGNATURE"
    elif integrity != "valid" or trust != "trusted":
        overall = "UNVERIFIABLE"
    elif lifecycle == "revoked":
        overall = "REVOKED"
    elif lifecycle != "active":
        overall = "UNVERIFIABLE"
    else:
        overall = "VALID"
    verification_id = _verification_record(
        db,
        mode="portable_payload",
        submitted_id=credential_id if isinstance(credential_id, str) else None,
        credential=credential,
        issuer=issuer,
        key=key,
        digest=digest,
        integrity=integrity,
        trust=trust,
        lifecycle=lifecycle,
        overall=overall,
        requester=requester,
    )
    db.flush()
    return {
        "verification_id": verification_id,
        "overall_result": overall,
        "integrity_result": integrity,
        "issuer_trust_result": trust,
        "lifecycle_result": lifecycle,
        "credential_id": credential_id if isinstance(credential_id, str) else None,
        "issuer_code": issuer_code if isinstance(issuer_code, str) else None,
        "message": _verification_message(overall),
    }


def revoke_credential(
    db: Session,
    *,
    credential_id: str,
    reason_code: str,
    reason_detail: str | None,
    actor_id: UUID,
    actor_reference: str,
) -> Revocation:
    credential = db.scalar(
        select(Credential)
        .where(Credential.credential_id == credential_id)
        .with_for_update()
    )
    if credential is None:
        raise ServiceError(404, "Credential was not found.")
    existing = db.scalar(
        select(Revocation).where(Revocation.credential_id == credential.id)
    )
    if existing is not None:
        raise ServiceError(409, "Credential has already been revoked.")
    now = datetime.now(timezone.utc)
    revocation = Revocation(
        id=uuid4(),
        credential_id=credential.id,
        reason_code=reason_code,
        reason_detail=reason_detail,
        recorded_by_user_id=actor_id,
        actor_reference=actor_reference,
        effective_at=now,
        recorded_at=now,
    )
    db.add(revocation)
    record_event(
        db,
        event_type="credential.revoked",
        actor_reference=actor_reference,
        actor_user_id=actor_id,
        target_type="credential",
        target_reference=credential.credential_id,
        reason_code=reason_code,
    )
    db.flush()
    return revocation


def _verification_message(result: str) -> str:
    return {
        "VALID": "Credential signature and current lifecycle status are valid.",
        "REVOKED": "Credential signature is valid, but the credential is revoked.",
        "NOT_FOUND": "Credential was not found in the authoritative registry.",
        "INVALID_SIGNATURE": "Credential signature is invalid.",
        "TAMPERED": "Stored credential payload digest does not match.",
        "UNVERIFIABLE": "Issuer trust, signing key, or authoritative lifecycle status could not be established.",
    }.get(result, "Credential could not be verified.")
