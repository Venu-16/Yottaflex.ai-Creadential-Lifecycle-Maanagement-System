from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.engine import create_engine

from app.models.domain import Credential, Revocation
from scripts.full_dataset_common import full_dataset_database_url


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    base_url = os.environ.get(
        "ANALYTICS_API_BASE_URL", "http://127.0.0.1:8000/api/v1"
    ).rstrip("/")
    principal = os.environ.get("ANALYTICS_DEMO_USER")
    password = os.environ.get("ANALYTICS_DEMO_PASSWORD")
    if not principal or not password:
        raise RuntimeError(
            "Set ANALYTICS_DEMO_USER and ANALYTICS_DEMO_PASSWORD for API acceptance queries."
        )
    parsed_url = urlparse(base_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise ValueError("ANALYTICS_API_BASE_URL must be an absolute HTTP(S) URL.")

    client = httpx.Client(base_url=base_url, timeout=60.0)
    login = client.post(
        "/auth/login",
        json={"principal_key": principal, "password": password},
    )
    require(login.status_code == 200, f"Login failed with HTTP {login.status_code}.")
    client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"
    checks: list[str] = []
    entity_samples: dict[str, int] = {}

    def get(path: str, **params):
        response = client.get(path, params=params)
        require(response.status_code == 200, f"{path} returned HTTP {response.status_code}.")
        return response.json()

    for name, path, offsets in (
        ("learners", "/learners", (0, 10000, 19900)),
        ("courses", "/courses", (0, 500, 900)),
        ("credentials", "/credentials", (0, 5000, 9900)),
    ):
        samples = []
        for offset in offsets:
            page = get(path, limit=100, offset=offset)
            require(len(page) == 100, f"{path} returned an incomplete sample at offset {offset}.")
            samples.extend(page)
        entity_samples[name] = len(samples)
        checks.append(f"{name}_start_middle_end_pages")

    for path in (
        "/credential-rules",
        "/issuers",
        "/enrollments",
        "/completions",
        "/assessment-attempts",
        "/revocations",
        "/verification/requests",
        "/audit",
    ):
        rows = get(path, limit=100, offset=0)
        require(bool(rows), f"{path} returned no imported records.")
        checks.append(f"{path.strip('/').replace('/', '_')}_first_page")

    learner = get("/learners", limit=1, offset=0)[0]
    course = get("/courses", limit=1, offset=0)[0]
    credential = get("/credentials", limit=1, offset=0)[0]
    require(
        client.get(f"/learners/{learner['id']}").status_code == 200,
        "Representative learner detail request failed.",
    )
    require(
        client.get(f"/courses/{course['id']}").status_code == 200,
        "Representative course detail request failed.",
    )
    require(
        client.get(f"/credentials/{credential['credential_id']}").status_code == 200,
        "Representative credential detail request failed.",
    )
    require(
        client.get("/learners", params={"limit": 101}).status_code == 422,
        "Invalid pagination did not return HTTP 422.",
    )
    require(
        client.get("/learners/00000000-0000-0000-0000-000000000000").status_code == 404,
        "Unknown learner lookup did not return HTTP 404.",
    )
    require(
        client.get("/courses/00000000-0000-0000-0000-000000000000").status_code == 404,
        "Unknown course lookup did not return HTTP 404.",
    )
    checks.extend(
        ["learner_course_credential_details", "invalid_page_size_422", "unknown_entity_404"]
    )

    database_url = full_dataset_database_url(require_confirmation=False)
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("SET TRANSACTION READ ONLY")
            revoked_credential_id = connection.execute(
                select(Credential.credential_id)
                .join(Revocation, Revocation.credential_id == Credential.id)
                .where(Revocation.effective_at <= datetime.now(timezone.utc))
                .order_by(Revocation.effective_at)
                .limit(1)
            ).scalar_one()
            active_credential_id = connection.execute(
                select(Credential.credential_id)
                .where(
                    Credential.id.not_in(
                        select(Revocation.credential_id)
                    )
                )
                .order_by(Credential.credential_id)
                .limit(1)
            ).scalar_one()
    finally:
        engine.dispose()

    public_client = httpx.Client(base_url=base_url, timeout=60.0)
    active_result = public_client.post(
        "/verification/credential-id",
        params={"credential_id": active_credential_id},
    )
    require(active_result.status_code == 200, "Public active-credential verification failed.")
    require(
        active_result.json()["overall_result"] == "VALID",
        "An active imported credential did not verify as VALID.",
    )
    require(
        "learner_id" not in active_result.json()
        and "learner" not in active_result.text.lower(),
        "Public verification exposed learner information.",
    )
    revoked_result = public_client.post(
        "/verification/credential-id",
        params={"credential_id": revoked_credential_id},
    )
    require(revoked_result.status_code == 200, "Public revoked-credential verification failed.")
    require(
        revoked_result.json()["overall_result"] == "REVOKED",
        "A revoked imported credential did not verify as REVOKED.",
    )
    unknown_result = public_client.post(
        "/verification/credential-id",
        params={"credential_id": "CRD-2099-999999"},
    )
    require(
        unknown_result.status_code == 200
        and unknown_result.json()["overall_result"] == "NOT_FOUND",
        "Unknown public credential verification did not return NOT_FOUND.",
    )
    checks.extend(
        ["public_active_verification", "public_revoked_verification", "public_unknown_verification"]
    )

    quality = get("/reports/data-quality")
    require(quality["status"] == "failed", "Expected known source-provenance drift was hidden.")
    failed_checks = [check["name"] for check in quality["checks"] if not check["passed"]]
    require(
        failed_checks == ["source_file_hashes_match"],
        f"Unexpected dataset validation failures: {failed_checks}.",
    )
    require(
        all(row["matches"] is True for row in quality["row_counts"]),
        "Imported row-count snapshot did not reconcile after API verification activity.",
    )
    require("ground_truth" not in json.dumps(quality).lower(), "Ground truth leaked in analytics.")
    checks.append("data_quality_import_snapshot_and_ground_truth_isolation")

    public_client.close()
    client.close()
    print(
        json.dumps(
            {
                "status": "passed",
                "checks": checks,
                "entity_samples": entity_samples,
                "active_verification": active_result.json()["overall_result"],
                "revoked_verification": revoked_result.json()["overall_result"],
                "unknown_verification": unknown_result.json()["overall_result"],
                "data_quality_status": quality["status"],
                "data_quality_failed_checks": [
                    check["name"] for check in quality["checks"] if not check["passed"]
                ],
                "credential_ids": {
                    "active": active_credential_id,
                    "revoked": revoked_credential_id,
                },
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
