from fastapi import APIRouter, Depends, status

from backend.models import User
from backend.schemas import AdminMeRead
from backend.services.auth_service import require_active_admin

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/me", response_model=AdminMeRead, status_code=status.HTTP_200_OK)
def read_admin_me(
    current_admin: User = Depends(require_active_admin),
) -> AdminMeRead:
    return AdminMeRead(
        user_id=current_admin.id,
        role=current_admin.role,
        account_status=current_admin.account_status,
        role_updated_at=current_admin.updated_at,
    )
