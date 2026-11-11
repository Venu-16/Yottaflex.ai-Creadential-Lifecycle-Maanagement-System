from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from cryptography.hazmat.primitives import serialization

from scripts.generate_seed_data import (
    ISSUE_DATE,
    make_anomaly_fixtures,
    profile_sizes,
    score_for_attempt,
    verify_anomaly_fixtures,
)
from scripts.seed_data_common import SEED, canonical_json, sha256, stable_id


def test_seed_ids_and_canonical_payloads_are_deterministic() -> None:
    assert SEED == 20261022
    assert stable_id("learner", 25) == stable_id("learner", 25)
    assert stable_id("learner", 25) != stable_id("learner", 26)
    assert isinstance(stable_id("learner", 25), UUID)
    assert canonical_json({"b": 2, "a": 1}) == b'{"a":1,"b":2}'


def test_profiles_meet_required_full_volumes_and_scale_starter() -> None:
    full = profile_sizes("full")
    starter = profile_sizes("starter")
    assert full == {
        "learners": 20_000,
        "courses": 1_000,
        "rules": 100,
        "issuers": 10,
        "credentials": 10_000,
        "verification_requests": 5_000,
    }
    assert starter["learners"] < full["learners"]
    assert starter["credentials"] < full["credentials"]


def test_scoring_fixture_has_passing_and_non_passing_examples() -> None:
    sizes = profile_sizes("full")
    assert score_for_attempt(0, 0, 1, sizes) == 90
    assert score_for_attempt(10, 7, 1, sizes) < 60 + 7 % 21


def test_all_anomaly_fixtures_are_isolated_and_detectable() -> None:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    private_key = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
    public_key = private_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    completed_at = datetime(2025, 2, 1, tzinfo=timezone.utc)
    issued_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    payload = {
        "credential_id": "CRD-2026-000001",
        "completion": {"completed_at": completed_at.isoformat()},
        "issued_at": issued_at.isoformat(),
    }
    payload_bytes = canonical_json(payload)
    signature = private_key.sign(payload_bytes)
    credential = {
        "id": stable_id("credential", 0),
        "credential_id": "CRD-2026-000001",
        "canonical_payload": payload_bytes,
        "sha256_digest": sha256(payload_bytes),
        "signature": signature,
        "issued_at": issued_at,
        "payload": payload,
    }
    revoked = {
        "id": stable_id("credential", 0),
        "credential_id": "CRD-2026-000001",
        "effective_at": datetime(2026, 3, 1, tzinfo=timezone.utc),
    }
    fixtures = make_anomaly_fixtures(
        credential,
        revoked,
        public_key,
        stable_id("decision", "ineligible"),
    )

    assert all(fixture["production_database_write"] is False for fixture in fixtures)
    assert all(verify_anomaly_fixtures(fixtures).values())
    assert ISSUE_DATE.year == 2026
