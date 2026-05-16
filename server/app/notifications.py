from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Notification, User, UserRole


def notify_user(
    db: Session,
    *,
    user_id: int,
    title: str,
    message: str,
    category: str | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
) -> Notification:
    row = Notification(
        user_id=user_id,
        title=title,
        message=message,
        category=category,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        is_read=False,
    )
    db.add(row)
    return row


def notify_role(
    db: Session,
    *,
    role: UserRole,
    title: str,
    message: str,
    category: str | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
) -> Notification:
    recipients = db.scalars(select(User).where(User.role == role, User.is_active.is_(True))).all()
    first: Notification | None = None
    for recipient in recipients:
        row = notify_user(
            db,
            user_id=int(recipient.id),
            title=title,
            message=message,
            category=category,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
        )
        if first is None:
            first = row
    if first is not None:
        return first
    row = Notification(
        target_role=role,
        title=title,
        message=message,
        category=category,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        is_read=False,
    )
    db.add(row)
    return row
