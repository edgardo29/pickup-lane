import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import SupportFlag, User
from backend.schemas import SupportFlagRead, SupportFlagResolve
from backend.services.admin_permission_service import PERMISSION_ACTION_CENTER_VIEW
from backend.services.auth_service import require_admin_permission
from backend.services.support_flag_service import (
    get_support_flag_for_viewer_or_404,
    list_support_flags,
    resolve_support_flag,
)

router = APIRouter(prefix="/admin/support-flags", tags=["support_flags"])


@router.get("", response_model=list[SupportFlagRead], status_code=status.HTTP_200_OK)
def list_support_flags_route(
    flag_status: str = "open",
    flag_type: str | None = None,
    limit: int = Query(default=100, ge=1, le=200),
    current_user: User = Depends(require_admin_permission(PERMISSION_ACTION_CENTER_VIEW)),
    db: Session = Depends(get_db),
) -> list[SupportFlag]:
    return list_support_flags(
        db,
        viewer_user=current_user,
        flag_status=flag_status,
        flag_type=flag_type,
        limit=limit,
    )


@router.get(
    "/{support_flag_id}",
    response_model=SupportFlagRead,
    status_code=status.HTTP_200_OK,
)
def get_support_flag_route(
    support_flag_id: uuid.UUID,
    current_user: User = Depends(require_admin_permission(PERMISSION_ACTION_CENTER_VIEW)),
    db: Session = Depends(get_db),
) -> SupportFlag:
    return get_support_flag_for_viewer_or_404(db, support_flag_id, current_user)


@router.post(
    "/{support_flag_id}/resolve",
    response_model=SupportFlagRead,
    status_code=status.HTTP_200_OK,
)
def resolve_support_flag_route(
    support_flag_id: uuid.UUID,
    payload: SupportFlagResolve,
    current_user: User = Depends(require_admin_permission(PERMISSION_ACTION_CENTER_VIEW)),
    db: Session = Depends(get_db),
) -> SupportFlag:
    return resolve_support_flag(
        db,
        support_flag_id=support_flag_id,
        resolver_user=current_user,
        payload=payload,
    )
