import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, UserStats
from backend.schemas import UserStatsCreate, UserStatsRead, UserStatsUpdate
from backend.services.admin_permission_service import (
    PERMISSION_USERS_MANAGE,
    PERMISSION_USERS_READ,
)
from backend.services.auth_service import get_current_app_user, require_admin_permission
from backend.services.user_stats_service import (
    create_user_stats_workflow,
    get_current_user_stats,
    get_user_stats_record,
    list_user_stats as list_user_stats_workflow,
    update_user_stats_workflow,
)

router = APIRouter(prefix="/user-stats", tags=["user_stats"])


# Admin-only endpoint for protected cached stats creation.
@router.post("", response_model=UserStatsRead, status_code=status.HTTP_201_CREATED)
def create_user_stats(
    user_stats: UserStatsCreate,
    db: Session = Depends(get_db),
    _current_admin: User = Depends(require_admin_permission(PERMISSION_USERS_MANAGE)),
) -> UserStats:
    return create_user_stats_workflow(db, user_stats)


@router.get("/me", response_model=UserStatsRead, status_code=status.HTTP_200_OK)
def get_my_user_stats(
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> UserStats:
    return get_current_user_stats(db, current_user)


# Admin-only endpoint for one user's cached stats row.
@router.get("/{user_id}", response_model=UserStatsRead, status_code=status.HTTP_200_OK)
def get_user_stats(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_admin: User = Depends(require_admin_permission(PERMISSION_USERS_READ)),
) -> UserStats:
    return get_user_stats_record(db, user_id)


# Admin-only endpoint for cached user stats rows.
@router.get("", response_model=list[UserStatsRead], status_code=status.HTTP_200_OK)
def list_user_stats(
    user_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    _current_admin: User = Depends(require_admin_permission(PERMISSION_USERS_READ)),
) -> list[UserStats]:
    return list_user_stats_workflow(db, user_id=user_id)


# Admin-only endpoint for protected cached stats updates.
@router.patch("/{user_id}", response_model=UserStatsRead, status_code=status.HTTP_200_OK)
def update_user_stats(
    user_id: uuid.UUID,
    user_stats_update: UserStatsUpdate,
    db: Session = Depends(get_db),
    _current_admin: User = Depends(require_admin_permission(PERMISSION_USERS_MANAGE)),
) -> UserStats:
    return update_user_stats_workflow(db, user_id, user_stats_update)
