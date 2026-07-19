import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import AdminRejectedAttempt, User
from backend.schemas import AdminRejectedAttemptRead
from backend.services.admin_rejected_attempt_service import (
    get_admin_rejected_attempt_for_viewer_or_404,
    list_admin_rejected_attempts,
)
from backend.services.auth_service import require_active_admin

router = APIRouter(prefix="/admin/rejected-attempts", tags=["admin_rejected_attempts"])


@router.get(
    "",
    response_model=list[AdminRejectedAttemptRead],
    status_code=status.HTTP_200_OK,
)
def list_admin_rejected_attempts_route(
    attempt_type: str | None = None,
    rejection_mode: str | None = None,
    limit: int = Query(default=100, ge=1, le=200),
    current_user: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> list[AdminRejectedAttempt]:
    return list_admin_rejected_attempts(
        db,
        viewer_user=current_user,
        attempt_type=attempt_type,
        rejection_mode=rejection_mode,
        limit=limit,
    )


@router.get(
    "/{admin_rejected_attempt_id}",
    response_model=AdminRejectedAttemptRead,
    status_code=status.HTTP_200_OK,
)
def get_admin_rejected_attempt_route(
    admin_rejected_attempt_id: uuid.UUID,
    current_user: User = Depends(require_active_admin),
    db: Session = Depends(get_db),
) -> AdminRejectedAttempt:
    return get_admin_rejected_attempt_for_viewer_or_404(
        db,
        admin_rejected_attempt_id,
        current_user,
    )
