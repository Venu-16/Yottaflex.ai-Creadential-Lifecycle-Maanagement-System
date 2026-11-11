from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.models.domain import AuditEvent


def record_event(
    db: Session,
    *,
    event_type: str,
    actor_reference: str,
    target_type: str | None,
    target_reference: str | None,
    actor_user_id: UUID | None = None,
    outcome: str = "success",
    reason_code: str | None = None,
    event_data: dict[str, Any] | None = None,
    correlation_id: UUID | None = None,
) -> AuditEvent:
    event = AuditEvent(
        id=uuid4(),
        event_type=event_type,
        outcome=outcome,
        actor_user_id=actor_user_id,
        actor_reference=actor_reference,
        target_type=target_type,
        target_reference=target_reference,
        reason_code=reason_code,
        event_data=event_data,
        correlation_id=correlation_id or uuid4(),
    )
    db.add(event)
    return event
