from __future__ import annotations

from sqlalchemy.orm import Session

from .models import Notification, UserRole


def notify_user(db: Session, *, user_id: int, title: str, message: str) -> Notification:
    row = Notification(user_id=user_id, title=title, message=message, is_read=False)
    db.add(row)
    return row


def notify_role(db: Session, *, role: UserRole, title: str, message: str) -> Notification:
    row = Notification(target_role=role, title=title, message=message, is_read=False)
    db.add(row)
    return row
