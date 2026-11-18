from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas import (
    AuthDeleteAccountRequest,
    AuthEmailAvailabilityRead,
    SelfUserRead,
)
from backend.services.account_deletion_service import delete_account_workflow
from backend.services.auth_account_service import (
    check_email_availability_workflow,
    cleanup_unfinished_account_workflow,
    sync_user_workflow,
)
from backend.services.auth_service import (
    VerifiedFirebaseIdentity,
    get_synced_current_app_user,
    get_verified_firebase_identity,
    require_recent_app_user,
)

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


@router.get("/me", response_model=SelfUserRead, status_code=status.HTTP_200_OK)
def read_current_app_user(
    current_user: User = Depends(get_synced_current_app_user),
) -> User:
    return current_user


@router.post(
    "/sync-user",
    response_model=SelfUserRead,
    status_code=status.HTTP_200_OK,
)
def sync_user(
    identity: VerifiedFirebaseIdentity = Depends(get_verified_firebase_identity),
    db: Session = Depends(get_db),
) -> User:
    return sync_user_workflow(identity, db)


@router.delete("/unfinished-account", status_code=status.HTTP_204_NO_CONTENT)
def cleanup_unfinished_account(
    identity: VerifiedFirebaseIdentity = Depends(get_verified_firebase_identity),
    db: Session = Depends(get_db),
) -> None:
    cleanup_unfinished_account_workflow(identity, db)


@router.delete("/account", response_model=SelfUserRead, status_code=status.HTTP_200_OK)
def delete_account(
    payload: AuthDeleteAccountRequest,
    current_user: User = Depends(require_recent_app_user),
    db: Session = Depends(get_db),
) -> User:
    return delete_account_workflow(payload, current_user, db)
