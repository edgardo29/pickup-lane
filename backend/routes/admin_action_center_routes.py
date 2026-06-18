from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas import AdminActionCenterRead
from backend.services.admin_action_center_service import get_admin_action_center
from backend.services.admin_permission_service import PERMISSION_ACTION_CENTER_VIEW
from backend.services.auth_service import require_admin_permission

router = APIRouter(prefix="/admin/action-center", tags=["admin_action_center"])


@router.get("", response_model=AdminActionCenterRead, status_code=status.HTTP_200_OK)
def read_admin_action_center(
    current_user: User = Depends(
        require_admin_permission(PERMISSION_ACTION_CENTER_VIEW)
    ),
    db: Session = Depends(get_db),
) -> AdminActionCenterRead:
    return get_admin_action_center(db, viewer_user=current_user)
