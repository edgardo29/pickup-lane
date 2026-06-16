import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import (
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
from backend.routes.auth_routes import get_current_app_user, is_admin
from backend.schemas import NotificationCreate, NotificationRead, NotificationUpdate
from backend.services.notification_service import (
    APP_NOTIFICATION_DOMAINS,
    APP_NOTIFICATION_TYPE_DOMAINS,
    GAME_ACTIVITY_DOMAINS,
    GAME_NOTIFICATION_TYPES,
    NEED_A_SUB_NOTIFICATION_TYPES,
    VALID_ACTION_KEYS,
    VALID_NOTIFICATION_CATEGORIES,
    VALID_NOTIFICATION_DOMAINS,
    VALID_NOTIFICATION_TYPES,
    VALID_SOURCE_TYPES,
    ensure_aware_utc,
    notification_source_domain_matches,
    serialize_notification,
    source_type_for_game,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])
GAME_RELATED_FIELDS = {
    "related_game_id",
    "related_chat_id",
    "related_booking_id",
    "related_payment_id",
    "related_refund_id",
    "related_participant_id",
    "related_message_id",
}
SUB_RELATED_FIELDS = {
    "related_sub_post_id",
    "related_sub_post_chat_id",
    "related_sub_post_chat_message_id",
    "related_sub_post_request_id",
    "related_sub_post_position_id",
}
IMMUTABLE_NOTIFICATION_UPDATE_FIELDS = {
    "notification_type",
    "notification_category",
    "notification_domain",
    "source_type",
    "title",
    "subject_label",
    "summary",
    "body",
    "action_key",
    "subject_starts_at",
    "subject_ends_at",
    "subject_timezone",
    "event_at",
    "aggregation_key",
    "aggregate_count",
    "actor_user_id",
    "related_game_id",
    "related_chat_id",
    "related_booking_id",
    "related_payment_id",
    "related_refund_id",
    "related_participant_id",
    "related_message_id",
    "related_sub_post_id",
    "related_sub_post_chat_id",
    "related_sub_post_chat_message_id",
    "related_sub_post_request_id",
    "related_sub_post_position_id",
}


def build_notification_conflict_detail(exc: IntegrityError) -> str:
    return str(exc.orig)


def get_active_user_or_404(
    db: Session,
    user_id: uuid.UUID,
    detail: str = "User not found.",
) -> User:
    db_user = db.get(User, user_id)

    if db_user is None or db_user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )

    return db_user


def require_admin_user(current_user: User) -> None:
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )


def get_visible_notification_or_404(
    db: Session,
    notification_id: uuid.UUID,
    current_user: User,
    *,
    allow_admin: bool,
) -> Notification:
    db_notification = db.get(Notification, notification_id)

    if db_notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )

    if db_notification.user_id == current_user.id:
        return db_notification

    if allow_admin and is_admin(current_user):
        return db_notification

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Notification not found.",
    )


def validate_notification_business_rules(
    notification_data: dict[str, object],
) -> None:
    for field_name in (
        "user_id",
        "notification_type",
        "notification_category",
        "notification_domain",
        "source_type",
        "title",
        "subject_label",
        "summary",
        "body",
        "event_at",
        "is_read",
    ):
        if notification_data[field_name] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} cannot be null.",
            )

    notification_type = notification_data["notification_type"]
    if notification_type not in VALID_NOTIFICATION_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="notification_type is not supported.",
        )

    notification_category = notification_data["notification_category"]
    if notification_category not in VALID_NOTIFICATION_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="notification_category is not supported.",
        )

    notification_domain = notification_data["notification_domain"]
    if notification_domain not in VALID_NOTIFICATION_DOMAINS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="notification_domain is not supported.",
        )

    source_type = notification_data["source_type"]
    if source_type not in VALID_SOURCE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="source_type is not supported.",
        )

    if not notification_source_domain_matches(notification_domain, source_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="source_type does not match notification_domain.",
        )

    action_key = notification_data.get("action_key")
    if action_key is not None and action_key not in VALID_ACTION_KEYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="action_key is not supported.",
        )

    if (
        notification_category == "app"
        and notification_domain not in APP_NOTIFICATION_DOMAINS
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="App notifications must use an app notification domain.",
        )

    if (
        notification_category == "game_activity"
        and notification_domain not in GAME_ACTIVITY_DOMAINS
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game activity notifications must use a game activity domain.",
        )

    app_type_domains = APP_NOTIFICATION_TYPE_DOMAINS.get(notification_type)
    if app_type_domains is not None:
        if (
            notification_category != "app"
            or notification_domain not in app_type_domains
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "notification_type does not match notification_category "
                    "and notification_domain."
                ),
            )
    elif notification_type in NEED_A_SUB_NOTIFICATION_TYPES:
        if (
            notification_category != "game_activity"
            or notification_domain != "need_a_sub"
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Need a Sub notification types must use the Need a Sub "
                    "game activity domain."
                ),
            )
    elif notification_type in GAME_NOTIFICATION_TYPES:
        if notification_category != "game_activity" or notification_domain != "game":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Game notification types must use the game activity domain.",
            )

    if not str(notification_data["title"]).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="title must not be empty.",
        )

    if not str(notification_data["subject_label"]).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="subject_label must not be empty.",
        )

    if not str(notification_data["summary"]).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="summary must not be empty.",
        )

    if not str(notification_data["body"]).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="body must not be empty.",
        )

    subject_timezone = notification_data.get("subject_timezone")
    if subject_timezone is not None and not str(subject_timezone).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="subject_timezone must not be empty.",
        )

    if (
        notification_data.get("subject_starts_at") is not None
        and subject_timezone is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="subject_timezone is required when subject_starts_at is set.",
        )

    subject_ends_at = notification_data.get("subject_ends_at")
    subject_starts_at = notification_data.get("subject_starts_at")
    if (
        subject_ends_at is not None
        and subject_starts_at is not None
        and subject_ends_at < subject_starts_at
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="subject_ends_at cannot be before subject_starts_at.",
        )

    aggregation_key = notification_data.get("aggregation_key")
    aggregate_count = notification_data.get("aggregate_count")
    if aggregation_key is not None and not str(aggregation_key).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="aggregation_key must not be empty.",
        )

    if aggregate_count is not None and aggregate_count < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="aggregate_count must be at least 1.",
        )

    if aggregate_count is not None and aggregation_key is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="aggregation_key is required when aggregate_count is set.",
        )

    if action_key == "view_game" and notification_data.get("related_game_id") is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="view_game notifications require related_game_id.",
        )

    if (
        action_key == "view_sub_post"
        and notification_data.get("related_sub_post_id") is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="view_sub_post notifications require related_sub_post_id.",
        )

    if (
        notification_data.get("actor_user_id") is not None
        and notification_data["actor_user_id"] == notification_data["user_id"]
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="actor_user_id cannot match user_id.",
        )

    has_game_relation = any(
        notification_data[field_name] is not None
        for field_name in GAME_RELATED_FIELDS
    )
    has_sub_relation = any(
        notification_data[field_name] is not None
        for field_name in SUB_RELATED_FIELDS
    )

    if has_game_relation and has_sub_relation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Notifications cannot mix game and Need a Sub related records.",
        )

    if has_game_relation and notification_domain != "game":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game related records require notification_domain 'game'.",
        )

    if has_sub_relation and notification_domain != "need_a_sub":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Need a Sub related records require notification_domain 'need_a_sub'.",
        )


def normalize_notification_lifecycle_fields(
    notification_data: dict[str, object],
    existing_notification: Notification | None = None,
) -> dict[str, object]:
    normalized_data = dict(notification_data)

    for field_name in (
        "event_at",
        "subject_starts_at",
        "subject_ends_at",
        "read_at",
    ):
        field_value = normalized_data.get(field_name)
        if isinstance(field_value, datetime):
            normalized_data[field_name] = ensure_aware_utc(field_value)

    if normalized_data["is_read"]:
        normalized_data["read_at"] = (
            normalized_data.get("read_at")
            or (
                existing_notification.read_at
                if existing_notification is not None
                else None
            )
            or datetime.now(timezone.utc)
        )
    else:
        normalized_data["read_at"] = None

    return normalized_data


def validate_notification_references(
    db: Session,
    notification_data: dict[str, object],
) -> None:
    get_active_user_or_404(db, notification_data["user_id"])

    if notification_data["actor_user_id"] is not None:
        get_active_user_or_404(
            db,
            notification_data["actor_user_id"],
            "Actor user not found.",
        )

    db_game = None
    if notification_data["related_game_id"] is not None:
        db_game = db.get(Game, notification_data["related_game_id"])

        if db_game is None or db_game.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Related game not found.",
            )

        expected_source_type = source_type_for_game(db_game)
        if notification_data["source_type"] != expected_source_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="source_type must match the related game's game_type.",
            )

    db_chat = None
    if notification_data["related_chat_id"] is not None:
        db_chat = db.get(GameChat, notification_data["related_chat_id"])

        if db_chat is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Related game chat not found.",
            )

        if (
            notification_data["related_game_id"] is not None
            and db_chat.game_id != notification_data["related_game_id"]
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="related_chat_id must belong to related_game_id.",
            )

    db_booking = None
    if notification_data["related_booking_id"] is not None:
        db_booking = db.get(Booking, notification_data["related_booking_id"])

        if db_booking is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Related booking not found.",
            )

        if (
            notification_data["related_game_id"] is not None
            and db_booking.game_id != notification_data["related_game_id"]
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="related_booking_id must belong to related_game_id.",
            )

    db_payment = None
    if notification_data["related_payment_id"] is not None:
        db_payment = db.get(Payment, notification_data["related_payment_id"])

        if db_payment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Related payment not found.",
            )

        if (
            notification_data["related_booking_id"] is not None
            and db_payment.booking_id != notification_data["related_booking_id"]
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="related_payment_id must belong to related_booking_id.",
            )

        if notification_data["related_game_id"] is not None:
            payment_game_matches = db_payment.game_id == notification_data["related_game_id"]
            payment_booking_game_matches = (
                db_booking is not None
                and db_payment.booking_id == db_booking.id
                and db_booking.game_id == notification_data["related_game_id"]
            )

            if not payment_game_matches and not payment_booking_game_matches:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="related_payment_id must belong to related_game_id.",
                )

    if notification_data["related_refund_id"] is not None:
        db_refund = db.get(Refund, notification_data["related_refund_id"])

        if db_refund is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Related refund not found.",
            )

        if (
            notification_data["related_payment_id"] is not None
            and db_refund.payment_id != notification_data["related_payment_id"]
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="related_refund_id must belong to related_payment_id.",
            )

        if (
            notification_data["related_booking_id"] is not None
            and db_refund.booking_id is not None
            and db_refund.booking_id != notification_data["related_booking_id"]
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="related_refund_id must belong to related_booking_id.",
            )

        if (
            notification_data["related_game_id"] is not None
            and db_refund.booking_id is not None
        ):
            refund_booking = db_booking
            if refund_booking is None or refund_booking.id != db_refund.booking_id:
                refund_booking = db.get(Booking, db_refund.booking_id)

            if (
                refund_booking is None
                or refund_booking.game_id != notification_data["related_game_id"]
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="related_refund_id must belong to related_game_id.",
                )

    if notification_data["related_participant_id"] is not None:
        db_participant = db.get(
            GameParticipant,
            notification_data["related_participant_id"],
        )

        if db_participant is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Related participant not found.",
            )

        if (
            notification_data["related_game_id"] is not None
            and db_participant.game_id != notification_data["related_game_id"]
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="related_participant_id must belong to related_game_id.",
            )

        if (
            notification_data["related_booking_id"] is not None
            and db_participant.booking_id != notification_data["related_booking_id"]
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="related_participant_id must belong to related_booking_id.",
            )

    if notification_data["related_message_id"] is not None:
        db_message = db.get(ChatMessage, notification_data["related_message_id"])

        if db_message is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Related chat message not found.",
            )

        if (
            notification_data["related_chat_id"] is not None
            and db_message.chat_id != notification_data["related_chat_id"]
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="related_message_id must belong to related_chat_id.",
            )

        if (
            notification_data["related_chat_id"] is None
            and notification_data["related_game_id"] is not None
        ):
            db_message_chat = db.get(GameChat, db_message.chat_id)

            if (
                db_message_chat is None
                or db_message_chat.game_id != notification_data["related_game_id"]
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="related_message_id must belong to related_game_id.",
                )

    db_sub_post = None
    if notification_data["related_sub_post_id"] is not None:
        db_sub_post = db.get(SubPost, notification_data["related_sub_post_id"])

        if db_sub_post is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Related Need a Sub post not found.",
            )

    db_sub_post_chat = None
    if notification_data["related_sub_post_chat_id"] is not None:
        db_sub_post_chat = db.get(
            SubPostChat,
            notification_data["related_sub_post_chat_id"],
        )

        if db_sub_post_chat is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Related Need a Sub chat not found.",
            )

        if (
            db_sub_post is not None
            and db_sub_post_chat.sub_post_id != db_sub_post.id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="related_sub_post_chat_id must belong to related_sub_post_id.",
            )

    if notification_data["related_sub_post_chat_message_id"] is not None:
        db_sub_chat_message = db.get(
            SubPostChatMessage,
            notification_data["related_sub_post_chat_message_id"],
        )

        if db_sub_chat_message is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Related Need a Sub chat message not found.",
            )

        if (
            db_sub_post_chat is not None
            and db_sub_chat_message.chat_id != db_sub_post_chat.id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "related_sub_post_chat_message_id must belong to "
                    "related_sub_post_chat_id."
                ),
            )

        if db_sub_post_chat is None and db_sub_post is not None:
            db_sub_message_chat = db.get(SubPostChat, db_sub_chat_message.chat_id)

            if (
                db_sub_message_chat is None
                or db_sub_message_chat.sub_post_id != db_sub_post.id
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "related_sub_post_chat_message_id must belong to "
                        "related_sub_post_id."
                    ),
                )

    db_sub_position = None
    if notification_data["related_sub_post_position_id"] is not None:
        db_sub_position = db.get(
            SubPostPosition,
            notification_data["related_sub_post_position_id"],
        )

        if db_sub_position is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Related Need a Sub position not found.",
            )

        if (
            db_sub_post is not None
            and db_sub_position.sub_post_id != db_sub_post.id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="related_sub_post_position_id must belong to related_sub_post_id.",
            )

    if notification_data["related_sub_post_request_id"] is not None:
        db_sub_request = db.get(
            SubPostRequest,
            notification_data["related_sub_post_request_id"],
        )

        if db_sub_request is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Related Need a Sub request not found.",
            )

        if db_sub_post is not None and db_sub_request.sub_post_id != db_sub_post.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="related_sub_post_request_id must belong to related_sub_post_id.",
            )

        if (
            db_sub_position is not None
            and db_sub_request.sub_post_position_id != db_sub_position.id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "related_sub_post_request_id must belong to "
                    "related_sub_post_position_id."
                ),
            )


def validate_notification_create_access(
    notification_data: dict[str, object],
    current_user: User,
) -> None:
    if notification_data["user_id"] != current_user.id and not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create notifications for another user.",
        )

    if (
        notification_data["actor_user_id"] is not None
        and notification_data["actor_user_id"] != current_user.id
        and not is_admin(current_user)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="actor_user_id must be the current user.",
        )


def validate_notification_update_fields(update_data: dict[str, object]) -> None:
    immutable_fields = IMMUTABLE_NOTIFICATION_UPDATE_FIELDS & update_data.keys()

    if immutable_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Notification content and related records cannot be changed "
                "after creation."
            ),
        )


def query_notifications(
    db: Session,
    *,
    user_id: uuid.UUID,
    notification_type: str | None = None,
    notification_category: str | None = None,
    notification_domain: str | None = None,
    is_read: bool | None = None,
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
) -> list[Notification]:
    statement = select(Notification).where(Notification.user_id == user_id)

    if notification_type is not None:
        if notification_type not in VALID_NOTIFICATION_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="notification_type is not supported.",
            )
        statement = statement.where(Notification.notification_type == notification_type)

    if notification_category is not None:
        if notification_category not in VALID_NOTIFICATION_CATEGORIES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="notification_category is not supported.",
            )
        statement = statement.where(
            Notification.notification_category == notification_category
        )

    if notification_domain is not None:
        if notification_domain not in VALID_NOTIFICATION_DOMAINS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="notification_domain is not supported.",
            )
        statement = statement.where(
            Notification.notification_domain == notification_domain
        )

    if is_read is not None:
        statement = statement.where(Notification.is_read == is_read)

    if related_game_id is not None:
        statement = statement.where(Notification.related_game_id == related_game_id)

    if related_chat_id is not None:
        statement = statement.where(Notification.related_chat_id == related_chat_id)

    if related_booking_id is not None:
        statement = statement.where(
            Notification.related_booking_id == related_booking_id
        )

    if related_payment_id is not None:
        statement = statement.where(
            Notification.related_payment_id == related_payment_id
        )

    if related_refund_id is not None:
        statement = statement.where(
            Notification.related_refund_id == related_refund_id
        )

    if related_participant_id is not None:
        statement = statement.where(
            Notification.related_participant_id == related_participant_id
        )

    if related_message_id is not None:
        statement = statement.where(
            Notification.related_message_id == related_message_id
        )

    if related_sub_post_id is not None:
        statement = statement.where(
            Notification.related_sub_post_id == related_sub_post_id
        )

    if related_sub_post_chat_id is not None:
        statement = statement.where(
            Notification.related_sub_post_chat_id == related_sub_post_chat_id
        )

    if related_sub_post_chat_message_id is not None:
        statement = statement.where(
            Notification.related_sub_post_chat_message_id
            == related_sub_post_chat_message_id
        )

    if related_sub_post_request_id is not None:
        statement = statement.where(
            Notification.related_sub_post_request_id == related_sub_post_request_id
        )

    if related_sub_post_position_id is not None:
        statement = statement.where(
            Notification.related_sub_post_position_id == related_sub_post_position_id
        )

    notifications = db.scalars(statement.order_by(Notification.event_at.desc())).all()
    return list(notifications)


@router.post("", response_model=NotificationRead, status_code=status.HTTP_201_CREATED)
def create_notification(
    notification: NotificationCreate,
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    notification_data = normalize_notification_lifecycle_fields(
        notification.model_dump()
    )
    validate_notification_business_rules(notification_data)
    validate_notification_create_access(notification_data, current_user)
    validate_notification_references(db, notification_data)

    new_notification = Notification(
        id=uuid.uuid4(),
        **notification_data,
    )

    try:
        db.add(new_notification)
        db.commit()
        db.refresh(new_notification)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_notification_conflict_detail(exc),
        ) from exc

    return serialize_notification(db, new_notification)


@router.get("/me", response_model=list[NotificationRead], status_code=status.HTTP_200_OK)
def list_my_notifications(
    notification_type: str | None = None,
    notification_category: str | None = None,
    notification_domain: str | None = None,
    is_read: bool | None = None,
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
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    notifications = query_notifications(
        db,
        user_id=current_user.id,
        notification_type=notification_type,
        notification_category=notification_category,
        notification_domain=notification_domain,
        is_read=is_read,
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
    return [
        serialize_notification(db, notification)
        for notification in notifications
    ]


@router.get(
    "/{notification_id}",
    response_model=NotificationRead,
    status_code=status.HTTP_200_OK,
)
def get_notification(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    notification = get_visible_notification_or_404(
        db, notification_id, current_user, allow_admin=True
    )
    return serialize_notification(db, notification)


@router.get("", response_model=list[NotificationRead], status_code=status.HTTP_200_OK)
def list_notifications(
    user_id: uuid.UUID | None = None,
    notification_type: str | None = None,
    notification_category: str | None = None,
    notification_domain: str | None = None,
    is_read: bool | None = None,
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
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    effective_user_id = current_user.id
    if user_id is not None:
        if user_id != current_user.id:
            require_admin_user(current_user)
        effective_user_id = user_id

    notifications = query_notifications(
        db,
        user_id=effective_user_id,
        notification_type=notification_type,
        notification_category=notification_category,
        notification_domain=notification_domain,
        is_read=is_read,
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
    return [
        serialize_notification(db, notification)
        for notification in notifications
    ]


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationRead,
    status_code=status.HTTP_200_OK,
)
def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return update_notification(
        notification_id,
        NotificationUpdate(is_read=True),
        current_user,
        db,
    )


@router.patch(
    "/{notification_id}",
    response_model=NotificationRead,
    status_code=status.HTTP_200_OK,
)
def update_notification(
    notification_id: uuid.UUID,
    notification_update: NotificationUpdate,
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    db_notification = get_visible_notification_or_404(
        db, notification_id, current_user, allow_admin=False
    )
    update_data = notification_update.model_dump(exclude_unset=True)

    if "user_id" in update_data and update_data["user_id"] != db_notification.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id cannot be changed for an existing notification.",
        )

    validate_notification_update_fields(update_data)

    effective_notification_data = {
        "user_id": db_notification.user_id,
        "notification_type": db_notification.notification_type,
        "notification_category": db_notification.notification_category,
        "notification_domain": db_notification.notification_domain,
        "source_type": db_notification.source_type,
        "title": db_notification.title,
        "subject_label": db_notification.subject_label,
        "summary": db_notification.summary,
        "body": db_notification.body,
        "action_key": db_notification.action_key,
        "subject_starts_at": db_notification.subject_starts_at,
        "subject_ends_at": db_notification.subject_ends_at,
        "subject_timezone": db_notification.subject_timezone,
        "event_at": db_notification.event_at,
        "aggregation_key": db_notification.aggregation_key,
        "aggregate_count": db_notification.aggregate_count,
        "actor_user_id": db_notification.actor_user_id,
        "related_game_id": db_notification.related_game_id,
        "related_chat_id": db_notification.related_chat_id,
        "related_booking_id": db_notification.related_booking_id,
        "related_payment_id": db_notification.related_payment_id,
        "related_refund_id": db_notification.related_refund_id,
        "related_participant_id": db_notification.related_participant_id,
        "related_message_id": db_notification.related_message_id,
        "related_sub_post_id": db_notification.related_sub_post_id,
        "related_sub_post_chat_id": db_notification.related_sub_post_chat_id,
        "related_sub_post_chat_message_id": (
            db_notification.related_sub_post_chat_message_id
        ),
        "related_sub_post_request_id": db_notification.related_sub_post_request_id,
        "related_sub_post_position_id": db_notification.related_sub_post_position_id,
        "is_read": update_data.get("is_read", db_notification.is_read),
        "read_at": update_data.get("read_at", db_notification.read_at),
    }
    effective_notification_data = normalize_notification_lifecycle_fields(
        effective_notification_data,
        db_notification,
    )
    validate_notification_business_rules(effective_notification_data)
    validate_notification_references(db, effective_notification_data)

    update_data["read_at"] = effective_notification_data["read_at"]

    for field_name, field_value in update_data.items():
        setattr(db_notification, field_name, field_value)

    db_notification.updated_at = datetime.now(timezone.utc)

    try:
        db.add(db_notification)
        db.commit()
        db.refresh(db_notification)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_notification_conflict_detail(exc),
        ) from exc

    return serialize_notification(db, db_notification)
