import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas import (
    AdminNotificationLookupDetailRead,
    AdminNotificationLookupListRead,
)
from backend.services.admin_notification_service import (
    get_admin_notification_lookup_detail,
    list_admin_notification_lookup,
)
from backend.services.auth_service import require_active_admin

router = APIRouter(prefix="/admin/notifications", tags=["admin_notifications"])
ADMIN_NOTIFICATION_LOOKUP_QUERY_PARAMS = {"user_id", "cursor"}


def reject_unsupported_lookup_params(request: Request) -> None:
    unsupported_params = sorted(
        set(request.query_params.keys()) - ADMIN_NOTIFICATION_LOOKUP_QUERY_PARAMS
    )
    if unsupported_params:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "notification_lookup_unsupported_query_param",
                "message": (
                    "Notification Lookup only supports recipient history "
                    "parameters."
                ),
                "params": unsupported_params,
            },
        )


@router.get(
    "",
    response_model=AdminNotificationLookupListRead,
    status_code=status.HTTP_200_OK,
)
def list_admin_notifications_route(
    request: Request,
    user_id: uuid.UUID | None = None,
    cursor: str | None = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> AdminNotificationLookupListRead:
    reject_unsupported_lookup_params(request)
    return list_admin_notification_lookup(
        db,
        viewer_user=current_admin,
        cursor=cursor,
        user_id=user_id,
    )


@router.get(
    "/{notification_id}",
    response_model=AdminNotificationLookupDetailRead,
    status_code=status.HTTP_200_OK,
)
def get_admin_notification_route(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> AdminNotificationLookupDetailRead:
    return get_admin_notification_lookup_detail(
        db,
        notification_id=notification_id,
        viewer_user=current_admin,
    )
