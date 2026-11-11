from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    principal_key: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=1, max_length=1024)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(APIModel):
    id: UUID
    principal_key: str
    display_name: str | None
    is_active: bool
    roles: list[str]


class LearnerCreate(BaseModel):
    learner_id: str | None = Field(default=None, pattern=r"^LRN-[0-9]{6}$")
    display_name: str = Field(min_length=1, max_length=200)
    user_id: UUID | None = None


class LearnerUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=200)
    archived: bool | None = None


class LearnerResponse(APIModel):
    id: UUID
    learner_id: str
    display_name: str
    user_id: UUID | None
    archived_at: datetime | None


class CourseCreate(BaseModel):
    course_code: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    status: str = "active"
    effective_from: datetime | None = None
    effective_to: datetime | None = None


class CourseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: str | None = None
    effective_from: datetime | None = None
    effective_to: datetime | None = None


class CourseResponse(APIModel):
    id: UUID
    course_code: str
    title: str
    description: str | None
    status: str
    effective_from: datetime | None
    effective_to: datetime | None


class IssuerCreate(BaseModel):
    issuer_code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)


class IssuerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    status: str | None = None


class IssuerResponse(APIModel):
    id: UUID
    issuer_code: str
    name: str
    status: str
    archived_at: datetime | None


class SigningKeyCreate(BaseModel):
    key_id: str = Field(min_length=1, max_length=128)
    public_key_base64: str
    algorithm: str = "Ed25519"
    valid_from: datetime
    valid_until: datetime | None = None
    supersedes_key_id: UUID | None = None


class RuleCreate(BaseModel):
    rule_code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    course_id: UUID
    criteria: dict[str, Any]
    attempt_selection_policy: str | None = "latest_graded"
    effective_from: datetime


class RuleVersionCreate(BaseModel):
    course_id: UUID
    criteria: dict[str, Any]
    attempt_selection_policy: str | None = "latest_graded"
    effective_from: datetime


class RuleResponse(APIModel):
    id: UUID
    rule_id: UUID
    version_number: int
    credential_scope_id: UUID
    course_id: UUID
    rule_code: str
    name: str
    criteria: dict[str, Any]
    attempt_selection_policy: str | None
    effective_from: datetime
    effective_to: datetime | None
    status: str


class EnrollmentCreate(BaseModel):
    learner_id: UUID
    course_id: UUID
    effective_from: datetime | None = None


class EnrollmentResponse(APIModel):
    id: UUID
    learner_id: UUID
    course_id: UUID
    status: str
    enrolled_at: datetime
    effective_from: datetime | None
    effective_to: datetime | None


class CompletionCreate(BaseModel):
    enrollment_id: UUID
    status: str = "in_progress"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    source_reference: str | None = Field(default=None, max_length=200)


class CompletionStatusUpdate(BaseModel):
    status: str
    completed_at: datetime | None = None


class CompletionResponse(APIModel):
    id: UUID
    learner_id: UUID
    course_id: UUID
    enrollment_id: UUID | None
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    recorded_at: datetime


class AssessmentAttemptCreate(BaseModel):
    completion_record_id: UUID
    assessment_key: str = Field(min_length=1, max_length=100)
    score: Decimal | None = Field(default=None, ge=0, le=100)
    score_scale: str | None = "0-100"
    result_code: str | None = Field(default=None, max_length=32)
    status: str = "graded"
    submitted_at: datetime
    graded_at: datetime | None = None
    supersedes_attempt_id: UUID | None = None


class AssessmentAttemptResponse(APIModel):
    id: UUID
    completion_record_id: UUID
    learner_id: UUID
    assessment_key: str
    attempt_number: int
    score: Decimal | None
    score_scale: str | None
    result_code: str | None
    status: str
    submitted_at: datetime
    graded_at: datetime | None
    supersedes_attempt_id: UUID | None


class EligibilityRequest(BaseModel):
    learner_id: UUID
    rule_code: str = Field(min_length=1, max_length=64)


class EligibilityResponse(BaseModel):
    decision_id: UUID
    learner_id: UUID
    rule_code: str
    rule_version_id: UUID
    outcome: str
    reason_codes: list[str]
    evaluated_at: datetime


class IssueRequest(BaseModel):
    learner_id: UUID
    rule_code: str = Field(min_length=1, max_length=64)


class CredentialResponse(APIModel):
    id: UUID
    credential_id: str
    learner_id: UUID
    issuer_id: UUID
    rule_version_id: UUID
    issued_at: datetime
    payload_version: str
    sha256_digest: str
    signature_algorithm: str
    signing_key_id: UUID
    replacement_of_credential_id: UUID | None


class PortableCredentialResponse(BaseModel):
    payload: dict[str, Any]
    signature_base64: str


class PortableVerificationRequest(BaseModel):
    payload: dict[str, Any]
    signature_base64: str


class VerificationResponse(BaseModel):
    verification_id: str | None = None
    overall_result: str
    integrity_result: str
    issuer_trust_result: str
    lifecycle_result: str
    credential_id: str | None = None
    issuer_code: str | None = None
    message: str


class RevocationCreate(BaseModel):
    reason_code: str = Field(min_length=1, max_length=64)
    reason_detail: str | None = None


class RevocationResponse(APIModel):
    id: UUID
    credential_id: UUID
    reason_code: str
    reason_detail: str | None
    actor_reference: str
    effective_at: datetime
    recorded_at: datetime


class AuditEventResponse(APIModel):
    id: UUID
    event_type: str
    outcome: str
    actor_reference: str
    target_type: str | None
    target_reference: str | None
    occurred_at: datetime
    reason_code: str | None
    event_data: dict[str, Any] | None


class ReportSummary(BaseModel):
    credentials_by_status: dict[str, int]
    total_credentials: int
    total_revocations: int
    total_verifications: int


class AnalyticsRate(BaseModel):
    percent: float | None
    numerator: int
    denominator: int
    definition: str


class AnalyticsOverview(BaseModel):
    as_of: datetime
    total_learners: int
    total_courses: int
    total_enrollments: int
    total_completed_records: int
    total_eligible_learners: int
    total_credentials_issued: int
    total_revoked_credentials: int
    total_verification_requests: int
    credential_issuance_rate: AnalyticsRate
    revocation_rate: AnalyticsRate
    verification_success_rate: AnalyticsRate
    completion_rate: AnalyticsRate


class AnalyticsBucket(BaseModel):
    key: str
    count: int


class AnalyticsTimeBucket(BaseModel):
    period: str
    outcome: str | None = None
    count: int


class CredentialLifecycleAnalytics(BaseModel):
    as_of: datetime
    credential_status: list[AnalyticsBucket]
    issuance_over_time: list[AnalyticsTimeBucket]
    revocations_over_time: list[AnalyticsTimeBucket]
    eligibility_outcomes: list[AnalyticsBucket]


class VerificationAnalytics(BaseModel):
    as_of: datetime
    total_requests: int
    outcome_counts: list[AnalyticsBucket]
    mode_counts: list[AnalyticsBucket]
    outcomes_over_time: list[AnalyticsTimeBucket]


class CourseAnalytics(BaseModel):
    course_id: UUID
    course_code: str
    title: str
    enrolled_learners: int
    completed_records: int


class AssessmentScoreBucket(BaseModel):
    score_scale: str
    range: str
    count: int


class AcademicAnalytics(BaseModel):
    as_of: datetime
    course_distribution: list[CourseAnalytics]
    assessment_score_distribution: list[AssessmentScoreBucket]
    eligibility_outcomes: list[AnalyticsBucket]


class DatasetRowCount(BaseModel):
    table: str
    expected: int
    imported: int | None
    current: int
    matches: bool | None


class DatasetCheck(BaseModel):
    name: str
    passed: bool
    details: str | None = None


class DataQualityReport(BaseModel):
    status: str
    seed: int | None
    generation_timestamp: datetime | None
    dataset_sha256: str | None
    total_expected_rows: int | None
    total_imported_rows: int | None
    missing_reference_count: int | None
    last_successful_validation_at: datetime | None
    row_counts: list[DatasetRowCount]
    checks: list[DatasetCheck]
    warnings: list[str]


class PerformanceReport(BaseModel):
    status: str
    measured: bool
    average_response_ms: float | None
    median_response_ms: float | None
    p95_response_ms: float | None
    maximum_response_ms: float | None
    slowest_endpoint: str | None
    total_tested_requests: int | None
    successful_request_percent: float | None
    last_tested_at: datetime | None
    status_distribution: dict[str, int] | None


class PaginatedResponse(BaseModel):
    items: list[Any]
    limit: int
    offset: int
