import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.routes.retired_route_helpers import raise_retired_mutation_route
from backend.schemas.notification_schema import NotificationRead
from backend.services.auth_service import get_current_app_user, require_active_admin
from backend.services.notification_service import (
    get_notification_workflow,
    list_user_notifications_workflow,
    mark_notification_read_workflow,
)
from backend.services.query_pagination import (
    DEFAULT_COLLECTION_LIMIT,
    MAX_COLLECTION_LIMIT,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _raise_admin_notification_scaffold_removed() -> None:
    raise_retired_mutation_route(
        code="notification_admin_scaffold_removed",
        message=(
            "Admin notification creation, broad listing, and mutation are "
            "not supported. Use Notification Lookup or product-owned "
            "notification workflows."
        ),
    )


@router.post("", status_code=status.HTTP_410_GONE)
def create_notification(
    current_user: User = Depends(require_active_admin),
) -> None:
    del current_user
    _raise_admin_notification_scaffold_removed()


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
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_COLLECTION_LIMIT, ge=1, le=MAX_COLLECTION_LIMIT),
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
        limit=limit,
        offset=offset,
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


@router.get("", status_code=status.HTTP_410_GONE)
def list_notifications(
    current_user: User = Depends(require_active_admin),
) -> None:
    del current_user
    _raise_admin_notification_scaffold_removed()


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
    status_code=status.HTTP_410_GONE,
)
def update_notification(
    notification_id: uuid.UUID,
    current_user: User = Depends(require_active_admin),
) -> None:
    del notification_id, current_user
    _raise_admin_notification_scaffold_removed()
