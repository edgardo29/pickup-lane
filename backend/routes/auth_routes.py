from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas import (
    AuthDeleteAccountRequest,
    AuthEmailAvailabilityRead,
    UserRead,
)
from backend.services.account_deletion_service import delete_account_workflow
from backend.services.auth_account_service import (
    check_email_availability_workflow,
    cleanup_unfinished_account_workflow,
    sync_user_workflow,
)
from backend.services.auth_service import get_current_app_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get(
    "/email-availability",
    response_model=AuthEmailAvailabilityRead,
    status_code=status.HTTP_200_OK,
)
def check_email_availability(
    email: str = Query(..., min_length=3), db: Session = Depends(get_db)
) -> AuthEmailAvailabilityRead:
    return check_email_availability_workflow(email, db)


@router.get("/me", response_model=UserRead, status_code=status.HTTP_200_OK)
def read_current_app_user(
    current_user: User = Depends(get_current_app_user),
) -> User:
    return current_user


@router.post(
    "/sync-user",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
)
def sync_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    return sync_user_workflow(authorization, db)


@router.delete("/unfinished-account", status_code=status.HTTP_204_NO_CONTENT)
def cleanup_unfinished_account(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> None:
    cleanup_unfinished_account_workflow(authorization, db)


@router.delete("/account", response_model=UserRead, status_code=status.HTTP_200_OK)
def delete_account(
    payload: AuthDeleteAccountRequest,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    return delete_account_workflow(payload, authorization, db)
