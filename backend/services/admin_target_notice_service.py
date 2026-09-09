"""Durable, user-facing notices created from admin enforcement actions."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, object_session

from backend.models import (
    AdminAction,
    AdminTargetNotice,
    Notification,
    SubPostRequest,
)
from backend.services.need_a_sub_rules import now_utc
from backend.services.notification_event_service import build_app_notification_fields

COMMUNITY_NOTICE_ACTION_TYPES = {
    "community_game_hidden": "hide_community_game",
    "community_game_restored": "restore_community_game",
    "community_game_joining_paused": "pause_community_game_joining",
    "community_game_joining_resumed": "resume_community_game_joining",
    "community_game_payment_info_hidden": "hide_unsafe_community_payment_text",
    "community_game_payment_info_restored": "restore_community_payment_text",
    "community_game_cancelled": "admin_cancel_community_game",
}
NEED_SUB_NOTICE_ACTION_TYPES = {
    "need_sub_post_hidden": "hide_need_sub_post",
    "need_sub_post_restored": "restore_need_sub_post",
    "need_sub_post_removed": "remove_sub_post",
}
GAME_CHAT_NOTICE_ACTION_TYPES = {
    "game_chat_message_removed": "remove_chat_message",
    "game_chat_message_restored": "restore_chat_message",
}
NEED_SUB_CHAT_NOTICE_ACTION_TYPES = {
    "need_sub_chat_message_removed": "remove_chat_message",
    "need_sub_chat_message_restored": "restore_chat_message",
}
WS03_05C_NOTICE_TYPES = {
    *COMMUNITY_NOTICE_ACTION_TYPES,
    *NEED_SUB_NOTICE_ACTION_TYPES,
    *GAME_CHAT_NOTICE_ACTION_TYPES,
    *NEED_SUB_CHAT_NOTICE_ACTION_TYPES,
}


def validate_ws03_05c_notice_contract(
    db: Session,
    *,
    notice_type: str,
    title: str,
    body: str,
    recipient_user_id: uuid.UUID | None,
    created_by_user_id: uuid.UUID | None,
    admin_action: AdminAction | None,
    target_user_id: uuid.UUID | None,
    target_game_id: uuid.UUID | None,
    target_sub_post_id: uuid.UUID | None,
    target_sub_post_request_id: uuid.UUID | None,
) -> None:
    if notice_type not in WS03_05C_NOTICE_TYPES:
        return
    if not title.strip() or not body.strip():
        raise ValueError("WS03-05C notice title and body are required.")
    if admin_action is None or object_session(admin_action) is not db:
        raise ValueError("WS03-05C notices require a live linked admin action.")
    if created_by_user_id is None or created_by_user_id != admin_action.admin_user_id:
        raise ValueError("WS03-05C notice creator must match its admin action.")
    if recipient_user_id is None or target_user_id != recipient_user_id:
        raise ValueError("WS03-05C notice recipient and target user must match.")

    expected_action_type = (
        COMMUNITY_NOTICE_ACTION_TYPES.get(notice_type)
        or NEED_SUB_NOTICE_ACTION_TYPES.get(notice_type)
        or GAME_CHAT_NOTICE_ACTION_TYPES.get(notice_type)
        or NEED_SUB_CHAT_NOTICE_ACTION_TYPES.get(notice_type)
    )
    if admin_action.action_type != expected_action_type:
        raise ValueError("WS03-05C notice action type does not match.")

    if notice_type in COMMUNITY_NOTICE_ACTION_TYPES:
        valid_target = (
            target_game_id is not None
            and target_game_id == admin_action.target_game_id
            and target_sub_post_id is None
            and target_sub_post_request_id is None
            and target_user_id == admin_action.target_user_id
        )
    elif notice_type in GAME_CHAT_NOTICE_ACTION_TYPES:
        valid_target = (
            target_game_id is not None
            and target_game_id == admin_action.target_game_id
            and admin_action.target_message_id is not None
            and target_sub_post_id is None
            and target_sub_post_request_id is None
            and target_user_id == admin_action.target_user_id
        )
    elif notice_type in NEED_SUB_CHAT_NOTICE_ACTION_TYPES:
        valid_target = (
            target_sub_post_id is not None
            and target_sub_post_id == admin_action.target_sub_post_id
            and admin_action.target_sub_chat_message_id is not None
            and target_game_id is None
            and target_sub_post_request_id is None
            and target_user_id == admin_action.target_user_id
        )
    elif notice_type != "need_sub_post_removed":
        valid_target = (
            target_sub_post_id is not None
            and target_sub_post_id == admin_action.target_sub_post_id
            and target_game_id is None
            and target_sub_post_request_id is None
            and target_user_id == admin_action.target_user_id
        )
    elif target_sub_post_request_id is None:
        valid_target = (
            target_sub_post_id is not None
            and target_sub_post_id == admin_action.target_sub_post_id
            and target_game_id is None
            and target_user_id == admin_action.target_user_id
        )
    else:
        sub_request = db.get(SubPostRequest, target_sub_post_request_id)
        valid_target = (
            sub_request is not None
            and target_sub_post_id == admin_action.target_sub_post_id
            and sub_request.sub_post_id == target_sub_post_id
            and sub_request.requester_user_id == target_user_id
            and target_game_id is None
        )

    if not valid_target:
        raise ValueError("WS03-05C notice target shape does not match its action.")


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
        "admin_enforcement_notice",
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
        notification_type="admin_enforcement_notice",
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
    notice_metadata: dict | None = None,
) -> AdminTargetNotice:
    validate_ws03_05c_notice_contract(
        db,
        notice_type=notice_type,
        title=title,
        body=body,
        recipient_user_id=recipient_user_id,
        created_by_user_id=created_by_user_id,
        admin_action=admin_action,
        target_user_id=target_user_id,
        target_game_id=target_game_id,
        target_sub_post_id=target_sub_post_id,
        target_sub_post_request_id=target_sub_post_request_id,
    )
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
        user_safe_reason=None,
        notice_metadata=notice_metadata,
        created_by_user_id=created_by_user_id,
        created_at=current_time,
        updated_at=current_time,
    )
    db.add(notice)
    create_admin_target_notice_notification(db, notice=notice)
    return notice
