from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas.account_suspension_schema import SuspendedAccountRead
from backend.services.account_suspension_service import get_suspended_account_notice
from backend.services.auth_service import require_active_or_suspended_user

router = APIRouter(prefix="/account-suspended", tags=["account_suspended"])


@router.get("", response_model=SuspendedAccountRead, status_code=status.HTTP_200_OK)
def read_suspended_account_notice(
    current_user: User = Depends(require_active_or_suspended_user),
    db: Session = Depends(get_db),
) -> SuspendedAccountRead:
    return get_suspended_account_notice(db, user=current_user)
