import base64
import binascii
import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from backend.models import (
    AdminAction,
    Booking,
    ChatMessage,
    Game,
    GameChat,
    GameParticipant,
    Notification,
    Payment,
    Refund,
    SubPost,
    SubPostChat,
    SubPostChatMessage,
    SubPostPosition,
    SubPostRequest,
    User,
)
from backend.schemas.admin_notification_schema import (
    AdminNotificationActionStateRead,
    AdminNotificationAuditActionRead,
    AdminNotificationCompactRelatedRecordRead,
    AdminNotificationLookupDetailRead,
    AdminNotificationLookupItemRead,
    AdminNotificationLookupListRead,
    AdminNotificationRecipientRead,
    AdminNotificationRelatedRecordRead,
)
from backend.services.notification_display_service import (
    format_row_subject,
    serialize_notification,
)
from backend.services.notification_policy import (
    ICON_BY_NOTIFICATION_TYPE,
    SEVERITY_BY_NOTIFICATION_TYPE,
    SOURCE_LABEL_BY_TYPE,
)

NOTIFICATION_LOOKUP_RELATED_FIELDS: dict[str, tuple[str, str]] = {
    "game": ("related_game_id", "Game"),
    "game_chat": ("related_chat_id", "Game chat"),
    "booking": ("related_booking_id", "Booking"),
    "payment": ("related_payment_id", "Payment"),
    "refund": ("related_refund_id", "Refund"),
    "participant": ("related_participant_id", "Participant"),
    "game_message": ("related_message_id", "Game message"),
    "need_a_sub_post": ("related_sub_post_id", "Need a Sub post"),
    "need_a_sub_chat": ("related_sub_post_chat_id", "Need a Sub chat"),
    "need_a_sub_chat_message": (
        "related_sub_post_chat_message_id",
        "Need a Sub chat message",
    ),
    "need_a_sub_request": ("related_sub_post_request_id", "Need a Sub request"),
    "need_a_sub_position": ("related_sub_post_position_id", "Need a Sub position"),
}

NOTIFICATION_LOOKUP_RELATED_MODELS = {
    "game": Game,
    "game_chat": GameChat,
    "booking": Booking,
    "payment": Payment,
    "refund": Refund,
    "participant": GameParticipant,
    "game_message": ChatMessage,
    "need_a_sub_post": SubPost,
    "need_a_sub_chat": SubPostChat,
    "need_a_sub_chat_message": SubPostChatMessage,
    "need_a_sub_request": SubPostRequest,
    "need_a_sub_position": SubPostPosition,
}

MEANINGFUL_AGGREGATE_COUNT_NOTIFICATION_TYPES = {
    "chat_message",
    "sub_chat_message",
}

ACTION_TARGET_RELATED_TYPE_BY_KEY = {
    "view_game": "game",
    "view_sub_post": "need_a_sub_post",
}

NOTIFICATION_LOOKUP_CURSOR_VERSION = 1
NOTIFICATION_LOOKUP_SORT_VERSION = "created_at_desc_id_desc"
ADMIN_NOTIFICATION_LOOKUP_PAGE_LIMIT = 50


def normalize_optional_exact_filter(value: str | None) -> str | None:
    if value is None:
        return None

    normalized_value = value.strip()
    return normalized_value or None


def lookup_validation_error(*, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "code": code,
            "message": message,
        },
    )


def invalid_notification_cursor_error() -> HTTPException:
    return lookup_validation_error(
        code="invalid_notification_lookup_cursor",
        message="cursor is invalid.",
    )


def query_context_hash(context: dict[str, object]) -> str:
    raw_context = json.dumps(
        context,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw_context).hexdigest()


def encode_notification_cursor(
    notification: Notification,
    *,
    context_hash: str,
) -> str:
    payload = {
        "cursor_version": NOTIFICATION_LOOKUP_CURSOR_VERSION,
        "sort_version": NOTIFICATION_LOOKUP_SORT_VERSION,
        "created_at": notification.created_at.isoformat(),
        "id": str(notification.id),
        "query_context_hash": context_hash,
    }
    raw_payload = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw_payload).decode("ascii")


def decode_notification_cursor(
    cursor: str | None,
    *,
    expected_context_hash: str,
) -> dict[str, Any] | None:
    normalized_cursor = normalize_optional_exact_filter(cursor)
    if normalized_cursor is None:
        return None

    try:
        raw_payload = base64.urlsafe_b64decode(normalized_cursor.encode("ascii"))
        payload = json.loads(raw_payload.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("cursor payload must be an object")
        if payload.get("cursor_version") != NOTIFICATION_LOOKUP_CURSOR_VERSION:
            raise ValueError("unsupported cursor version")
        if payload.get("sort_version") != NOTIFICATION_LOOKUP_SORT_VERSION:
            raise ValueError("unsupported sort version")
        if payload.get("query_context_hash") != expected_context_hash:
            raise ValueError("cursor context mismatch")
        return {
            "created_at": datetime.fromisoformat(payload["created_at"]),
            "id": uuid.UUID(payload["id"]),
        }
    except (
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
        binascii.Error,
    ) as exc:
        raise invalid_notification_cursor_error() from exc


def build_cursor_filter(cursor_data: dict[str, Any] | None):
    if cursor_data is None:
        return None

    return or_(
        Notification.created_at < cursor_data["created_at"],
        and_(
            Notification.created_at == cursor_data["created_at"],
            Notification.id < cursor_data["id"],
        ),
    )


def build_admin_notification_filters(
    *,
    user_id: uuid.UUID | None = None,
) -> tuple[list[object], str]:
    if user_id is None:
        raise lookup_validation_error(
            code="notification_lookup_user_required",
            message="Search by recipient.",
        )

    context = {
        "user_id": str(user_id),
    }

    return [Notification.user_id == user_id], query_context_hash(context)


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

    actions_by_notification_id: dict[uuid.UUID, list[AdminAction]] = {}
    for action in audit_actions:
        if action.target_notification_id is None:
            continue
        actions_by_notification_id.setdefault(action.target_notification_id, []).append(
            action
        )

    return actions_by_notification_id


def users_by_id(db: Session, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, User]:
    if not user_ids:
        return {}

    return {
        user.id: user
        for user in db.scalars(select(User).where(User.id.in_(user_ids))).all()
    }


def user_display_name(user: User | None) -> str:
    if user is None:
        return "Unknown user"

    name = " ".join(
        part for part in (user.first_name, user.last_name) if part
    ).strip()
    return name or user.email or str(user.id)


def serialize_admin_notification_recipient(
    user: User | None,
    *,
    fallback_user_id: uuid.UUID,
) -> AdminNotificationRecipientRead:
    return AdminNotificationRecipientRead(
        user_id=user.id if user is not None else fallback_user_id,
        display_name=user_display_name(user),
        email=user.email if user is not None else None,
        account_status=user.account_status if user is not None else None,
    )


def related_record_exists(
    db: Session,
    *,
    related_type: str,
    related_id: uuid.UUID,
) -> bool | None:
    model = NOTIFICATION_LOOKUP_RELATED_MODELS.get(related_type)
    if model is None:
        return None
    return db.get(model, related_id) is not None


def related_records_for_notification(
    db: Session | None,
    notification: Notification,
    *,
    include_exists: bool = False,
) -> list[AdminNotificationRelatedRecordRead]:
    related_records: list[AdminNotificationRelatedRecordRead] = []
    for related_type, (field_name, display_label) in (
        NOTIFICATION_LOOKUP_RELATED_FIELDS.items()
    ):
        related_id = getattr(notification, field_name)
        if related_id is None:
            continue
        related_records.append(
            AdminNotificationRelatedRecordRead(
                type=related_type,
                id=related_id,
                display_label=display_label,
                exists=related_record_exists(
                    db,
                    related_type=related_type,
                    related_id=related_id,
                )
                if include_exists and db is not None
                else None,
            )
        )

    return related_records


def compact_related_records_for_notification(
    notification: Notification,
) -> list[AdminNotificationCompactRelatedRecordRead]:
    related_records: list[AdminNotificationCompactRelatedRecordRead] = []
    for related_type, (field_name, display_label) in (
        NOTIFICATION_LOOKUP_RELATED_FIELDS.items()
    ):
        related_id = getattr(notification, field_name)
        if related_id is None:
            continue
        related_records.append(
            AdminNotificationCompactRelatedRecordRead(
                type=related_type,
                id=related_id,
                display_label=display_label,
            )
        )

    return related_records


def action_target_record_for_notification(
    db: Session,
    notification: Notification,
    *,
    evaluate_exists: bool,
) -> AdminNotificationRelatedRecordRead | None:
    if notification.action_key is None:
        return None

    related_type = ACTION_TARGET_RELATED_TYPE_BY_KEY.get(notification.action_key)
    if related_type is None:
        return None

    field_name, display_label = NOTIFICATION_LOOKUP_RELATED_FIELDS[related_type]
    related_id = getattr(notification, field_name)
    if related_id is None:
        return None

    return AdminNotificationRelatedRecordRead(
        type=related_type,
        id=related_id,
        display_label=display_label,
        exists=(
            related_record_exists(
                db,
                related_type=related_type,
                related_id=related_id,
            )
            if evaluate_exists
            else None
        ),
    )


def serialize_admin_notification_action_state(
    db: Session,
    notification: Notification,
    notification_data: dict[str, object],
    *,
    include_detail: bool,
) -> AdminNotificationActionStateRead:
    action_key = notification_data["action_key"]
    action = notification_data["action"]
    evaluated_at = datetime.now(timezone.utc) if include_detail else None
    target_record = action_target_record_for_notification(
        db,
        notification,
        evaluate_exists=include_detail or action is None,
    )
    detail_target_record = target_record if include_detail else None

    if action_key is None:
        return AdminNotificationActionStateRead(
            action_key=None,
            status="not_applicable",
            reason_code="no_action" if include_detail else None,
            explanation=(
                "This notification does not have an Inbox action."
                if include_detail
                else None
            ),
            evaluated_at=evaluated_at,
            target_record=detail_target_record,
        )

    if action is None and target_record is not None and target_record.exists is True:
        return AdminNotificationActionStateRead(
            action_key=str(action_key),
            status="unavailable",
            reason_code="action_unavailable" if include_detail else None,
            explanation=(
                "The stored action target exists but is no longer available "
                "in the current product state."
                if include_detail
                else None
            ),
            evaluated_at=evaluated_at,
            target_record=detail_target_record,
        )

    if action is None:
        return AdminNotificationActionStateRead(
            action_key=str(action_key),
            status="broken",
            reason_code="action_target_broken" if include_detail else None,
            explanation=(
                "The stored action no longer resolves to an available target."
                if include_detail
                else None
            ),
            evaluated_at=evaluated_at,
            target_record=detail_target_record,
        )

    action_payload = dict(action)
    if action_payload.get("disabled"):
        disabled_reason = action_payload.get("disabled_reason")
        return AdminNotificationActionStateRead(
            action_key=str(action_key),
            status="unavailable",
            disabled_reason=disabled_reason if include_detail else None,
            reason_code="action_disabled" if include_detail else None,
            explanation=str(disabled_reason or "The action is currently disabled.")
            if include_detail
            else None,
            evaluated_at=evaluated_at,
            target_record=detail_target_record,
        )

    return AdminNotificationActionStateRead(
        action_key=str(action_key),
        status="available",
        path=action_payload.get("path") if include_detail else None,
        reason_code="action_available" if include_detail else None,
        explanation="The action currently resolves to an available target."
        if include_detail
        else None,
        evaluated_at=evaluated_at,
        target_record=detail_target_record,
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


def serialize_admin_notification_lookup_item(
    db: Session,
    notification: Notification,
    *,
    recipients: dict[uuid.UUID, User],
) -> AdminNotificationLookupItemRead:
    related_records = compact_related_records_for_notification(notification)

    return AdminNotificationLookupItemRead(
        id=notification.id,
        user_id=notification.user_id,
        recipient=serialize_admin_notification_recipient(
            recipients.get(notification.user_id),
            fallback_user_id=notification.user_id,
        ),
        title=notification.title,
        subject_label=notification.subject_label,
        row_subject=format_row_subject(notification),
        notification_type=notification.notification_type,
        notification_category=notification.notification_category,
        notification_domain=notification.notification_domain,
        source_type=notification.source_type,
        source_label=SOURCE_LABEL_BY_TYPE.get(notification.source_type, "Pickup Lane"),
        icon=ICON_BY_NOTIFICATION_TYPE.get(notification.notification_type, "Bell"),
        severity=SEVERITY_BY_NOTIFICATION_TYPE.get(
            notification.notification_type,
            "default",
        ),
        event_at=notification.event_at,
        created_at=notification.created_at,
        is_read=notification.is_read,
        read_at=notification.read_at,
        primary_related_record=related_records[0] if related_records else None,
    )


def serialize_admin_notification_lookup_detail(
    db: Session,
    notification: Notification,
    *,
    audit_actions: list[AdminAction] | None = None,
) -> AdminNotificationLookupDetailRead:
    notification_data = serialize_notification(db, notification)
    if (
        notification.notification_type
        not in MEANINGFUL_AGGREGATE_COUNT_NOTIFICATION_TYPES
    ):
        notification_data["aggregate_count"] = None
    serialized_audit_actions = [
        serialize_admin_notification_audit_action(action)
        for action in (audit_actions or [])
    ]

    return AdminNotificationLookupDetailRead(
        **notification_data,
        action_state=serialize_admin_notification_action_state(
            db,
            notification,
            notification_data,
            include_detail=True,
        ),
        related_records=related_records_for_notification(
            db,
            notification,
            include_exists=True,
        ),
        audit_actions=serialized_audit_actions,
        audit_action_count=len(serialized_audit_actions),
    )


def list_admin_notification_lookup(
    db: Session,
    *,
    viewer_user: User,
    cursor: str | None = None,
    user_id: uuid.UUID | None = None,
) -> AdminNotificationLookupListRead:
    filters, context_hash = build_admin_notification_filters(
        user_id=user_id,
    )

    cursor_filter = build_cursor_filter(
        decode_notification_cursor(
            cursor,
            expected_context_hash=context_hash,
        )
    )
    if cursor_filter is not None:
        filters.append(cursor_filter)

    query_limit = ADMIN_NOTIFICATION_LOOKUP_PAGE_LIMIT
    notifications = list(
        db.scalars(
            select(Notification)
            .where(*filters)
            .order_by(
                Notification.created_at.desc(),
                Notification.id.desc(),
            )
            .limit(query_limit + 1)
        ).all()
    )

    has_more = len(notifications) > query_limit
    page_notifications = notifications[:query_limit]
    recipients = users_by_id(
        db,
        sorted({notification.user_id for notification in page_notifications}, key=str),
    )

    next_cursor = (
        encode_notification_cursor(
            page_notifications[-1],
            context_hash=context_hash,
        )
        if has_more and page_notifications
        else None
    )

    return AdminNotificationLookupListRead(
        notifications=[
            serialize_admin_notification_lookup_item(
                db,
                notification,
                recipients=recipients,
            )
            for notification in page_notifications
        ],
        limit=query_limit,
        next_cursor=next_cursor,
        has_more=has_more,
    )


def get_admin_notification_lookup_detail(
    db: Session,
    *,
    notification_id: uuid.UUID,
    viewer_user: User,
) -> AdminNotificationLookupDetailRead:
    notification = db.get(Notification, notification_id)
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )

    audit_actions = list_admin_notification_audit_actions(db, [notification.id])
    return serialize_admin_notification_lookup_detail(
        db,
        notification,
        audit_actions=audit_actions.get(notification.id, []),
    )
