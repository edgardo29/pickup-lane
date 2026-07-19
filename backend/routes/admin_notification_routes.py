import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas import (
    AdminNotificationDebugListRead,
    AdminNotificationDebugRead,
)
from backend.services.admin_notification_service import (
    get_admin_notification_debug_detail,
    list_admin_notification_debug,
)
from backend.services.auth_service import require_active_admin

router = APIRouter(prefix="/admin/notifications", tags=["admin_notifications"])


@router.get(
    "",
    response_model=AdminNotificationDebugListRead,
    status_code=status.HTTP_200_OK,
)
def list_admin_notifications_route(
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
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> AdminNotificationDebugListRead:
    return list_admin_notification_debug(
        db,
        viewer_user=current_admin,
        offset=offset,
        limit=limit,
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


@router.get(
    "/{notification_id}",
    response_model=AdminNotificationDebugRead,
    status_code=status.HTTP_200_OK,
)
def get_admin_notification_route(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> AdminNotificationDebugRead:
    return get_admin_notification_debug_detail(
        db,
        notification_id=notification_id,
        viewer_user=current_admin,
    )
