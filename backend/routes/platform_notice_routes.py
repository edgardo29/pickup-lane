import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas.platform_notice_schema import (
    PlatformNoticeCancel,
    PlatformNoticeCreate,
    PlatformNoticeCreateResultRead,
    PlatformNoticeListRead,
    PlatformNoticeRead,
    PlatformNoticeRecipientListRead,
)
from backend.services.auth_service import require_active_admin
from backend.services.platform_notice_service import (
    cancel_platform_notice,
    create_platform_notice,
    get_platform_notice,
    list_platform_notice_recipients,
    list_platform_notices,
)

router = APIRouter(prefix="/admin/platform-notices", tags=["platform_notices"])


@router.post(
    "",
    response_model=PlatformNoticeCreateResultRead,
    status_code=status.HTTP_201_CREATED,
)
def create_platform_notice_route(
    payload: PlatformNoticeCreate,
    current_user: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> PlatformNoticeCreateResultRead:
    return create_platform_notice(db, creator_user=current_user, payload=payload)


@router.get("", response_model=PlatformNoticeListRead, status_code=status.HTTP_200_OK)
def list_platform_notices_route(
    audience_type: str | None = None,
    cursor: str | None = Query(default=None, max_length=2000),
    limit: int = Query(default=30, ge=1, le=30),
    search: str | None = Query(default=None, max_length=200),
    status_filter: str | None = Query(default=None, alias="status"),
    current_user: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> PlatformNoticeListRead:
    del current_user
    return list_platform_notices(
        db,
        audience_type=audience_type,
        cursor=cursor,
        limit=limit,
        search=search,
        status_filter=status_filter,
    )


@router.get(
    "/{notice_id}",
    response_model=PlatformNoticeRead,
    status_code=status.HTTP_200_OK,
)
def get_platform_notice_route(
    notice_id: uuid.UUID,
    current_user: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> PlatformNoticeRead:
    del current_user
    return get_platform_notice(db, notice_id=notice_id)


@router.get(
    "/{notice_id}/recipients",
    response_model=PlatformNoticeRecipientListRead,
    status_code=status.HTTP_200_OK,
)
def list_platform_notice_recipients_route(
    notice_id: uuid.UUID,
    cursor: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> PlatformNoticeRecipientListRead:
    del current_user
    return list_platform_notice_recipients(
        db,
        cursor=cursor,
        limit=limit,
        notice_id=notice_id,
    )


@router.post(
    "/{notice_id}/cancel",
    response_model=PlatformNoticeRead,
    status_code=status.HTTP_200_OK,
)
def cancel_platform_notice_route(
    notice_id: uuid.UUID,
    payload: PlatformNoticeCancel,
    current_user: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> PlatformNoticeRead:
    return cancel_platform_notice(
        db,
        admin_user=current_user,
        notice_id=notice_id,
        payload=payload,
    )
