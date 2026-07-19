import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas.notification_schema import (
    NotificationCreate,
    NotificationRead,
    NotificationUpdate,
)
from backend.services.auth_service import get_current_app_user, require_active_admin
from backend.services.notification_service import (
    create_notification_workflow,
    get_notification_workflow,
    list_notifications_workflow,
    list_user_notifications_workflow,
    mark_notification_read_workflow,
    update_notification_workflow,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("", response_model=NotificationRead, status_code=status.HTTP_201_CREATED)
def create_notification(
    notification: NotificationCreate,
    current_user: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return create_notification_workflow(db, notification, current_user)


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
    return list_user_notifications_workflow(
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
    return get_notification_workflow(db, notification_id, current_user)


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
    current_user: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    return list_notifications_workflow(
        db,
        current_user,
        user_id=user_id,
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
    return mark_notification_read_workflow(db, notification_id, current_user)


@router.patch(
    "/{notification_id}",
    response_model=NotificationRead,
    status_code=status.HTTP_200_OK,
)
def update_notification(
    notification_id: uuid.UUID,
    notification_update: NotificationUpdate,
    current_user: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return update_notification_workflow(
        db,
        notification_id,
        notification_update,
        current_user,
    )
