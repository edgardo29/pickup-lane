import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas import AdminUserRead, SelfUserRead, UserUpdate
from backend.services.auth_service import get_current_app_user, require_active_admin
from backend.services.user_service import (
    get_current_user_profile,
    get_user_profile_or_404,
    list_user_profiles,
    reject_generic_user_mutation,
    update_current_user_profile,
)
from backend.services.query_pagination import (
    DEFAULT_ADMIN_COLLECTION_LIMIT,
    MAX_ADMIN_COLLECTION_LIMIT,
)

router = APIRouter(prefix="/users", tags=["users"])


# This route returns all user profiles currently stored in the app database.
@router.get("", response_model=list[AdminUserRead], status_code=status.HTTP_200_OK)
def list_users(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(
        default=DEFAULT_ADMIN_COLLECTION_LIMIT,
        ge=1,
        le=MAX_ADMIN_COLLECTION_LIMIT,
    ),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> list[User]:
    return list_user_profiles(db, limit=limit, offset=offset)


# Generic user mutations are intentionally disabled. Account creation, profile
# edits, and admin support actions must use narrower authenticated workflows
# instead of client-supplied identity CRUD.
@router.post("", response_model=AdminUserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    current_admin: User = Depends(require_active_admin),
) -> User:
    del current_admin
    reject_generic_user_mutation()


@router.get("/me", response_model=SelfUserRead, status_code=status.HTTP_200_OK)
def get_my_user_profile(
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> User:
    return get_current_user_profile(db, current_user)


@router.patch("/me", response_model=SelfUserRead, status_code=status.HTTP_200_OK)
def update_my_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> User:
    return update_current_user_profile(
        db,
        current_user,
        user_update.model_dump(exclude_unset=True),
    )


# This route fetches a single user profile by the app's internal UUID.
@router.get("/{user_id}", response_model=AdminUserRead, status_code=status.HTTP_200_OK)
def get_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> User:
    return get_user_profile_or_404(db, user_id)


@router.patch("/{user_id}", response_model=AdminUserRead, status_code=status.HTTP_200_OK)
def update_user(
    user_id: uuid.UUID,
    current_admin: User = Depends(require_active_admin),
) -> User:
    del user_id, current_admin
    reject_generic_user_mutation()


@router.delete("/{user_id}", response_model=AdminUserRead, status_code=status.HTTP_200_OK)
def delete_user(
    user_id: uuid.UUID,
    current_admin: User = Depends(require_active_admin),
) -> User:
    del user_id, current_admin
    reject_generic_user_mutation()
