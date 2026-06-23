import uuid
from collections import defaultdict

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models import AdminAction, Notification, User
from backend.schemas.admin_notification_schema import (
    AdminNotificationActionStateRead,
    AdminNotificationAuditActionRead,
    AdminNotificationDebugListRead,
    AdminNotificationDebugRead,
)
from backend.services.admin_permission_service import (
    PERMISSION_NOTIFICATIONS_READ,
    require_user_admin_permission,
)
from backend.services.notification_display_service import serialize_notification
from backend.services.notification_policy import (
    VALID_ACTION_KEYS,
    VALID_NOTIFICATION_CATEGORIES,
    VALID_NOTIFICATION_DOMAINS,
    VALID_NOTIFICATION_TYPES,
    VALID_SOURCE_TYPES,
)


def normalize_optional_filter(
    value: str | None,
    *,
    allowed_values: set[str],
    field_name: str,
) -> str | None:
    if value is None:
        return None

    normalized_value = value.strip()
    if not normalized_value:
        return None

    if normalized_value not in allowed_values:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} is not supported.",
        )

    return normalized_value


def normalize_optional_exact_filter(value: str | None) -> str | None:
    if value is None:
        return None

    normalized_value = value.strip()
    return normalized_value or None


def build_admin_notification_filters(
    *,
    user_id: uuid.UUID | None = None,
    notification_type: str | None = None,
    notification_category: str | None = None,
    notification_domain: str | None = None,
    source_type: str | None = None,
    is_read: bool | None = None,
    action_key: str | None = None,
    aggregation_key: str | None = None,
    related_game_id: uuid.UUID | None = None,
    related_chat_id: uuid.UUID | None = None,
    related_booking_id: uuid.UUID | None = None,
    related_payment_id: uuid.UUID | None = None,
    related_refund_id: uuid.UUID | None = None,
    related_participant_id: uuid.UUID | None = None,
    related_message_id: uuid.UUID | None = None,
    related_sub_post_id: uuid.UUID | None = None,
    related_sub_post_chat_id: uuid.UUID | None = None,
    related_sub_post_chat_message_id: uuid.UUID | None = None,
    related_sub_post_request_id: uuid.UUID | None = None,
    related_sub_post_position_id: uuid.UUID | None = None,
) -> list[object]:
    filters: list[object] = []

    normalized_notification_type = normalize_optional_filter(
        notification_type,
        allowed_values=VALID_NOTIFICATION_TYPES,
        field_name="notification_type",
    )
    normalized_notification_category = normalize_optional_filter(
        notification_category,
        allowed_values=VALID_NOTIFICATION_CATEGORIES,
        field_name="notification_category",
    )
    normalized_notification_domain = normalize_optional_filter(
        notification_domain,
        allowed_values=VALID_NOTIFICATION_DOMAINS,
        field_name="notification_domain",
    )
    normalized_source_type = normalize_optional_filter(
        source_type,
        allowed_values=VALID_SOURCE_TYPES,
        field_name="source_type",
    )
    normalized_action_key = normalize_optional_filter(
        action_key,
        allowed_values=VALID_ACTION_KEYS,
        field_name="action_key",
    )
    normalized_aggregation_key = normalize_optional_exact_filter(aggregation_key)

    if user_id is not None:
        filters.append(Notification.user_id == user_id)
    if normalized_notification_type is not None:
        filters.append(Notification.notification_type == normalized_notification_type)
    if normalized_notification_category is not None:
        filters.append(
            Notification.notification_category == normalized_notification_category
        )
    if normalized_notification_domain is not None:
        filters.append(Notification.notification_domain == normalized_notification_domain)
    if normalized_source_type is not None:
        filters.append(Notification.source_type == normalized_source_type)
    if is_read is not None:
        filters.append(Notification.is_read == is_read)
    if normalized_action_key is not None:
        filters.append(Notification.action_key == normalized_action_key)
    if normalized_aggregation_key is not None:
        filters.append(Notification.aggregation_key == normalized_aggregation_key)
    if related_game_id is not None:
        filters.append(Notification.related_game_id == related_game_id)
    if related_chat_id is not None:
        filters.append(Notification.related_chat_id == related_chat_id)
    if related_booking_id is not None:
        filters.append(Notification.related_booking_id == related_booking_id)
    if related_payment_id is not None:
        filters.append(Notification.related_payment_id == related_payment_id)
    if related_refund_id is not None:
        filters.append(Notification.related_refund_id == related_refund_id)
    if related_participant_id is not None:
        filters.append(Notification.related_participant_id == related_participant_id)
    if related_message_id is not None:
        filters.append(Notification.related_message_id == related_message_id)
    if related_sub_post_id is not None:
        filters.append(Notification.related_sub_post_id == related_sub_post_id)
    if related_sub_post_chat_id is not None:
        filters.append(Notification.related_sub_post_chat_id == related_sub_post_chat_id)
    if related_sub_post_chat_message_id is not None:
        filters.append(
            Notification.related_sub_post_chat_message_id
            == related_sub_post_chat_message_id
        )
    if related_sub_post_request_id is not None:
        filters.append(
            Notification.related_sub_post_request_id == related_sub_post_request_id
        )
    if related_sub_post_position_id is not None:
        filters.append(
            Notification.related_sub_post_position_id == related_sub_post_position_id
        )

    return filters


def list_admin_notification_audit_actions(
    db: Session,
    notification_ids: list[uuid.UUID],
) -> dict[uuid.UUID, list[AdminAction]]:
    if not notification_ids:
        return {}

    audit_actions = db.scalars(
        select(AdminAction)
        .where(AdminAction.target_notification_id.in_(notification_ids))
        .order_by(AdminAction.created_at.desc(), AdminAction.id.desc())
    ).all()

    actions_by_notification_id: dict[uuid.UUID, list[AdminAction]] = defaultdict(list)
    for action in audit_actions:
        if action.target_notification_id is not None:
            actions_by_notification_id[action.target_notification_id].append(action)

    return dict(actions_by_notification_id)


def serialize_admin_notification_action_state(
    notification_data: dict[str, object],
) -> AdminNotificationActionStateRead:
    action_key = notification_data["action_key"]
    action = notification_data["action"]

    if action_key is None:
        return AdminNotificationActionStateRead(action_key=None, status="no_action")

    if action is None:
        return AdminNotificationActionStateRead(
            action_key=str(action_key),
            status="unavailable",
        )

    action_payload = dict(action)
    if action_payload.get("disabled"):
        return AdminNotificationActionStateRead(
            action_key=str(action_key),
            status="disabled",
            disabled_reason=action_payload.get("disabled_reason"),
        )

    return AdminNotificationActionStateRead(
        action_key=str(action_key),
        status="available",
        path=action_payload.get("path"),
    )


def serialize_admin_notification_audit_action(
    action: AdminAction,
) -> AdminNotificationAuditActionRead:
    return AdminNotificationAuditActionRead(
        id=action.id,
        action_type=action.action_type,
        admin_user_id=action.admin_user_id,
        created_at=action.created_at,
    )


def serialize_admin_notification_debug(
    db: Session,
    notification: Notification,
    *,
    audit_actions: list[AdminAction] | None = None,
) -> AdminNotificationDebugRead:
    notification_data = serialize_notification(db, notification)
    serialized_audit_actions = [
        serialize_admin_notification_audit_action(action)
        for action in (audit_actions or [])
    ]

    return AdminNotificationDebugRead(
        **notification_data,
        action_state=serialize_admin_notification_action_state(notification_data),
        audit_actions=serialized_audit_actions,
        audit_action_count=len(serialized_audit_actions),
    )


def list_admin_notification_debug(
    db: Session,
    *,
    viewer_user: User,
    offset: int = 0,
    limit: int = 50,
    user_id: uuid.UUID | None = None,
    notification_type: str | None = None,
    notification_category: str | None = None,
    notification_domain: str | None = None,
    source_type: str | None = None,
    is_read: bool | None = None,
    action_key: str | None = None,
    aggregation_key: str | None = None,
    related_game_id: uuid.UUID | None = None,
    related_chat_id: uuid.UUID | None = None,
    related_booking_id: uuid.UUID | None = None,
    related_payment_id: uuid.UUID | None = None,
    related_refund_id: uuid.UUID | None = None,
    related_participant_id: uuid.UUID | None = None,
    related_message_id: uuid.UUID | None = None,
    related_sub_post_id: uuid.UUID | None = None,
    related_sub_post_chat_id: uuid.UUID | None = None,
    related_sub_post_chat_message_id: uuid.UUID | None = None,
    related_sub_post_request_id: uuid.UUID | None = None,
    related_sub_post_position_id: uuid.UUID | None = None,
) -> AdminNotificationDebugListRead:
    require_user_admin_permission(viewer_user, PERMISSION_NOTIFICATIONS_READ)

    filters = build_admin_notification_filters(
        user_id=user_id,
        notification_type=notification_type,
        notification_category=notification_category,
        notification_domain=notification_domain,
        source_type=source_type,
        is_read=is_read,
        action_key=action_key,
        aggregation_key=aggregation_key,
        related_game_id=related_game_id,
        related_chat_id=related_chat_id,
        related_booking_id=related_booking_id,
        related_payment_id=related_payment_id,
        related_refund_id=related_refund_id,
        related_participant_id=related_participant_id,
        related_message_id=related_message_id,
        related_sub_post_id=related_sub_post_id,
        related_sub_post_chat_id=related_sub_post_chat_id,
        related_sub_post_chat_message_id=related_sub_post_chat_message_id,
        related_sub_post_request_id=related_sub_post_request_id,
        related_sub_post_position_id=related_sub_post_position_id,
    )

    count_statement = select(func.count()).select_from(Notification)
    list_statement = select(Notification)
    if filters:
        count_statement = count_statement.where(*filters)
        list_statement = list_statement.where(*filters)

    total_count = db.scalar(count_statement) or 0
    notifications = list(
        db.scalars(
            list_statement.order_by(
                Notification.event_at.desc(),
                Notification.created_at.desc(),
            )
            .offset(offset)
            .limit(limit)
        ).all()
    )
    audit_actions_by_notification_id = list_admin_notification_audit_actions(
        db,
        [notification.id for notification in notifications],
    )

    return AdminNotificationDebugListRead(
        notifications=[
            serialize_admin_notification_debug(
                db,
                notification,
                audit_actions=audit_actions_by_notification_id.get(
                    notification.id,
                    [],
                ),
            )
            for notification in notifications
        ],
        total_count=total_count,
        offset=offset,
        limit=limit,
    )


def get_admin_notification_debug_detail(
    db: Session,
    *,
    notification_id: uuid.UUID,
    viewer_user: User,
) -> AdminNotificationDebugRead:
    require_user_admin_permission(viewer_user, PERMISSION_NOTIFICATIONS_READ)

    notification = db.get(Notification, notification_id)
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )

    audit_actions = list_admin_notification_audit_actions(db, [notification.id])
    return serialize_admin_notification_debug(
        db,
        notification,
        audit_actions=audit_actions.get(notification.id, []),
    )
