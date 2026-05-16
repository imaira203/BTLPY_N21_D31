from __future__ import annotations

import json

from sqlalchemy.orm import Session

from .models import Notification, UserRole


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
    target_screen: str | None = None,
    target_params: dict | None = None,
) -> Notification:
    row = Notification(
        user_id=user_id,
        title=title,
        message=message,
        category=category,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        target_screen=target_screen,
        target_params_json=json.dumps(target_params, ensure_ascii=False) if target_params else None,
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
    target_screen: str | None = None,
    target_params: dict | None = None,
) -> Notification:
    row = Notification(
        target_role=role,
        title=title,
        message=message,
        category=category,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        target_screen=target_screen,
        target_params_json=json.dumps(target_params, ensure_ascii=False) if target_params else None,
        is_read=False,
    )
    db.add(row)
    return row
