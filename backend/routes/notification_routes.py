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
    User,
)
from backend.schemas import NotificationCreate, NotificationRead, NotificationUpdate

router = APIRouter(prefix="/notifications", tags=["notifications"])

VALID_NOTIFICATION_TYPES = {
    "booking_confirmed",
    "booking_cancelled",
    "booking_refunded",
    "payment_failed",
    "game_cancelled",
    "game_updated",
    "game_reminder",
    "waitlist_joined",
    "waitlist_promoted",
    "waitlist_expired",
    "host_update",
    "chat_message",
    "deposit_paid",
    "deposit_released",
    "deposit_forfeited",
    "admin_notice",
}
IMMUTABLE_NOTIFICATION_UPDATE_FIELDS = {
    "notification_type",
    "title",
    "body",
    "related_game_id",
    "related_chat_id",
    "related_booking_id",
    "related_participant_id",
    "related_message_id",
}


def build_notification_conflict_detail(exc: IntegrityError) -> str:
    return str(exc.orig)


def get_active_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    db_user = db.get(User, user_id)

    if db_user is None or db_user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return db_user


def validate_notification_business_rules(
    notification_data: dict[str, object],
) -> None:
    for field_name in ("user_id", "notification_type", "title", "body", "is_read"):
        if notification_data[field_name] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} cannot be null.",
            )

    if notification_data["notification_type"] not in VALID_NOTIFICATION_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="notification_type is not supported.",
        )

    if not notification_data["title"].strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="title must not be empty.",
        )

    if not notification_data["body"].strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="body must not be empty.",
        )


def normalize_notification_lifecycle_fields(
    notification_data: dict[str, object],
    existing_notification: Notification | None = None,
) -> dict[str, object]:
    normalized_data = dict(notification_data)

    # read_at is derived from is_read so unread notifications cannot keep a
    # stale read timestamp, and read notifications always have one.
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

    if notification_data["related_game_id"] is not None:
        db_game = db.get(Game, notification_data["related_game_id"])

        if db_game is None or db_game.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Related game not found.",
            )

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


# This route creates one inbox/activity notification after validating the target
# user and any optional related domain records.
@router.post("", response_model=NotificationRead, status_code=status.HTTP_201_CREATED)
def create_notification(
    notification: NotificationCreate,
    db: Session = Depends(get_db),
) -> Notification:
    notification_data = normalize_notification_lifecycle_fields(
        notification.model_dump()
    )
    validate_notification_business_rules(notification_data)
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

    return new_notification


# This route fetches a single notification by its internal UUID.
@router.get(
    "/{notification_id}",
    response_model=NotificationRead,
    status_code=status.HTTP_200_OK,
)
def get_notification(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> Notification:
    db_notification = db.get(Notification, notification_id)

    if db_notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )

    return db_notification


# This route returns notification records currently stored in the app database.
@router.get("", response_model=list[NotificationRead], status_code=status.HTTP_200_OK)
def list_notifications(
    user_id: uuid.UUID | None = None,
    notification_type: str | None = None,
    is_read: bool | None = None,
    related_game_id: uuid.UUID | None = None,
    related_chat_id: uuid.UUID | None = None,
    related_booking_id: uuid.UUID | None = None,
    related_participant_id: uuid.UUID | None = None,
    related_message_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
) -> list[Notification]:
    statement = select(Notification)

    if user_id is not None:
        statement = statement.where(Notification.user_id == user_id)

    if notification_type is not None:
        if notification_type not in VALID_NOTIFICATION_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="notification_type is not supported.",
            )
        statement = statement.where(Notification.notification_type == notification_type)

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

    if related_participant_id is not None:
        statement = statement.where(
            Notification.related_participant_id == related_participant_id
        )

    if related_message_id is not None:
        statement = statement.where(
            Notification.related_message_id == related_message_id
        )

    notifications = db.scalars(statement.order_by(Notification.created_at.desc())).all()
    return list(notifications)


# This route applies partial updates to an existing notification while keeping
# the read lifecycle timestamp aligned with is_read.
@router.patch(
    "/{notification_id}",
    response_model=NotificationRead,
    status_code=status.HTTP_200_OK,
)
def update_notification(
    notification_id: uuid.UUID,
    notification_update: NotificationUpdate,
    db: Session = Depends(get_db),
) -> Notification:
    db_notification = db.get(Notification, notification_id)

    if db_notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
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
        "notification_type": update_data.get(
            "notification_type",
            db_notification.notification_type,
        ),
        "title": update_data.get("title", db_notification.title),
        "body": update_data.get("body", db_notification.body),
        "related_game_id": update_data.get(
            "related_game_id",
            db_notification.related_game_id,
        ),
        "related_chat_id": update_data.get(
            "related_chat_id",
            db_notification.related_chat_id,
        ),
        "related_booking_id": update_data.get(
            "related_booking_id",
            db_notification.related_booking_id,
        ),
        "related_participant_id": update_data.get(
            "related_participant_id",
            db_notification.related_participant_id,
        ),
        "related_message_id": update_data.get(
            "related_message_id",
            db_notification.related_message_id,
        ),
        "is_read": update_data.get("is_read", db_notification.is_read),
        "read_at": update_data.get("read_at", db_notification.read_at),
    }
    effective_notification_data = normalize_notification_lifecycle_fields(
        effective_notification_data,
        db_notification,
    )
    validate_notification_business_rules(effective_notification_data)
    validate_notification_references(db, effective_notification_data)

    # read_at is derived from the fully merged notification state so PATCH
    # payloads cannot leave stale read timestamps behind.
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

    return db_notification
