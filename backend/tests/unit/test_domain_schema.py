from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app.database.base import Base
import app.models


def test_domain_metadata_registers_mvp_tables() -> None:
    expected_tables = {
        "learners",
        "courses",
        "credential_rules",
        "credential_rule_versions",
        "completion_records",
        "assessment_attempts",
        "eligibility_decisions",
        "credentials",
        "credential_awards",
        "issuers",
        "issuer_signing_keys",
        "verification_requests",
        "revocations",
        "audit_events",
    }

    assert expected_tables <= Base.metadata.tables.keys()


def test_all_mvp_tables_compile_for_postgresql() -> None:
    dialect = postgresql.dialect()

    for table in Base.metadata.sorted_tables:
        sql = str(CreateTable(table).compile(dialect=dialect))
        assert f"CREATE TABLE {table.name}" in sql


def test_credential_award_enforces_learner_scope_identity() -> None:
    award = Base.metadata.tables["credential_awards"]

    assert any(
        constraint.name == "uq_awards_learner_scope"
        for constraint in award.constraints
    )
