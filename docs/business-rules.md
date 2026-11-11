# Business Rules

This page summarizes the rules the code enforces. The full description, with status codes and diagrams, is in [credential-lifecycle.md](credential-lifecycle.md). The reasoning behind each rule is in [DECISIONS.md](DECISIONS.md).

These rules are implementation assumptions (IA-01 to IA-21). They have not been approved as business policy.

## Credential rules

- A rule belongs to one course and has numbered versions with an effective date.
- A version must contain at least one requirement: course completion, a minimum score, or both.
- The minimum score is between 0 and 100.
- A new version never changes an earlier one. The newest version already in effect is the one used.

## Completion and assessment

- A learner has at most one active enrollment per course and one completion record per enrollment.
- Status `completed` requires `completed_at`; any other status forbids it.
- `completed_at` may not be earlier than `started_at` and may not be more than 5 minutes ahead of the server clock.
- Assessment attempts are numbered per completion and assessment. A new attempt does not overwrite an older one.
- A graded attempt needs a score from 0 to 100 and a grading time not earlier than the submission time.

## Eligibility

- The evaluation uses the latest completion from an enrollment that is not cancelled, and the latest graded attempt that has not been superseded.
- Outcomes: `eligible`, `ineligible`, `needs_review`.
- Reason codes: `MISSING_ENROLLMENT`, `MISSING_COMPLETION`, `COURSE_INCOMPLETE`, `COMPLETION_DATE_IN_FUTURE`, `MISSING_ASSESSMENT`, `ASSESSMENT_DATE_IN_FUTURE`, `ASSESSMENT_BELOW_THRESHOLD`, `RULE_HAS_NO_REQUIREMENTS`, `UNSUPPORTED_ATTEMPT_SELECTION_POLICY`.
- Every evaluation is stored with its rule version, reasons and evidence.

## Issuance

- Only an Academic Administrator can issue.
- Eligibility is evaluated again at the moment of issuing. Anything other than `eligible` is refused with `422`, and the refusal is recorded.
- The evidence must contain a completion dated on or before the evaluation time, also for rules that only require a score (`COMPLETION_REQUIRED_BEFORE_ISSUANCE`).
- One credential per learner and course.
- The credential ID is unique and has the form `CRD-YYYY-NNNNNN`.
- A repeated request with the same `Idempotency-Key` and body returns the same credential.

## Verification

- Anyone can verify, without an account.
- Result precedence: `TAMPERED`, then `INVALID_SIGNATURE`, then `UNVERIFIABLE`, then `REVOKED`, then `VALID`. An unknown credential ID gives `NOT_FOUND`.
- The response contains no learner name, learner ID or score.
- Every verification request is stored.

## Revocation

- Only an Academic Administrator can revoke.
- A reason code is required.
- A credential can be revoked once. Revocation is permanent and takes effect immediately.
- The credential row and its history are kept.

## Audit

- Every create, update, decision, issuance, refusal, verification and revocation writes an audit event in the same transaction.
- The API can read audit events and cannot change or delete them.
