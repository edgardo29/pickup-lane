from fastapi import APIRouter, Depends, status

from backend.models import User
from backend.schemas import AdminMeRead
from backend.services.admin_permission_service import (
    PERMISSION_ACTION_CENTER_VIEW,
    get_admin_data_scopes_for_user,
    get_admin_permissions_for_user,
)
from backend.services.auth_service import require_admin_permission

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/me", response_model=AdminMeRead, status_code=status.HTTP_200_OK)
def read_admin_me(
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_ACTION_CENTER_VIEW)
    ),
) -> AdminMeRead:
    return AdminMeRead(
        user_id=current_admin.id,
        role=current_admin.role,
        account_status=current_admin.account_status,
        permissions=list(get_admin_permissions_for_user(current_admin)),
        data_scopes=list(get_admin_data_scopes_for_user(current_admin)),
        role_updated_at=current_admin.updated_at,
    )
