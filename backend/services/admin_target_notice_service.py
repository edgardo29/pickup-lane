"""Durable, user-facing notices created from admin enforcement actions."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import AdminAction, AdminTargetNotice, Notification
from backend.services.admin_record_rules import normalize_optional_text
from backend.services.need_a_sub_rules import now_utc
from backend.services.notification_event_service import build_app_notification_fields


def target_notice_notification_aggregation_key(notice_id: uuid.UUID) -> str:
    return f"admin_target_notice:{notice_id}"


def create_admin_target_notice_notification(
    db: Session,
    *,
    notice: AdminTargetNotice,
) -> Notification | None:
    if notice.recipient_user_id is None:
        return None

    aggregation_key = target_notice_notification_aggregation_key(notice.id)
    existing_notification = db.scalar(
        select(Notification).where(
            Notification.user_id == notice.recipient_user_id,
            Notification.aggregation_key == aggregation_key,
        )
    )
    if existing_notification is not None:
        return existing_notification

    notification_fields = build_app_notification_fields(
        "admin_notice",
        event_at=notice.created_at,
        source_type="pickup_lane",
        subject_label="Pickup Lane",
        title=notice.title,
        summary=notice.body,
        body=notice.body,
        force_action_null=True,
    )
    notification_fields["aggregation_key"] = aggregation_key
    notification = Notification(
        id=uuid.uuid4(),
        user_id=notice.recipient_user_id,
        notification_type="admin_notice",
        notification_category="app",
        notification_domain="admin",
        actor_user_id=None,
        is_read=False,
        read_at=None,
        created_at=notice.created_at,
        updated_at=notice.created_at,
        **notification_fields,
    )
    db.add(notification)
    metadata = dict(notice.notice_metadata or {})
    metadata["notification_id"] = str(notification.id)
    notice.notice_metadata = metadata
    return notification


def create_admin_target_notice(
    db: Session,
    *,
    notice_type: str,
    title: str,
    body: str,
    recipient_user_id: uuid.UUID | None,
    created_by_user_id: uuid.UUID | None,
    admin_action: AdminAction | None = None,
    target_user_id: uuid.UUID | None = None,
    target_game_id: uuid.UUID | None = None,
    target_sub_post_id: uuid.UUID | None = None,
    target_sub_post_request_id: uuid.UUID | None = None,
    user_safe_reason: str | None = None,
    notice_metadata: dict | None = None,
) -> AdminTargetNotice:
    current_time = now_utc()
    notice = AdminTargetNotice(
        id=uuid.uuid4(),
        recipient_user_id=recipient_user_id,
        target_user_id=target_user_id,
        target_game_id=target_game_id,
        target_sub_post_id=target_sub_post_id,
        target_sub_post_request_id=target_sub_post_request_id,
        admin_action_id=admin_action.id if admin_action is not None else None,
        notice_type=notice_type,
        notice_status="active",
        title=title.strip(),
        body=body.strip(),
        user_safe_reason=normalize_optional_text(user_safe_reason, "user_safe_reason"),
        notice_metadata=notice_metadata,
        created_by_user_id=created_by_user_id,
        created_at=current_time,
        updated_at=current_time,
    )
    db.add(notice)
    create_admin_target_notice_notification(db, notice=notice)
    return notice
