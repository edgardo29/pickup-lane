import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, UserStats
from backend.routes.retired_route_helpers import raise_retired_mutation_route
from backend.schemas import UserStatsRead
from backend.services.auth_service import get_current_app_user, require_active_admin
from backend.services.user_stats_service import (
    get_current_user_stats,
    get_user_stats_record,
    list_user_stats as list_user_stats_workflow,
)

router = APIRouter(prefix="/user-stats", tags=["user_stats"])


# Retired public/admin scaffold. Stats remain internally service-owned.
@router.post("", status_code=status.HTTP_410_GONE)
def create_user_stats(
    _current_admin: User = Depends(require_active_admin),
) -> None:
    del _current_admin
    raise_retired_mutation_route(
        code="user_stats_scaffold_removed",
        message=(
            "Direct user stats creation is no longer supported. Stats are "
            "maintained by product-owned workflows."
        ),
    )


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
    _current_admin: User = Depends(require_active_admin),
) -> UserStats:
    return get_user_stats_record(db, user_id)


# Admin-only endpoint for cached user stats rows.
@router.get("", response_model=list[UserStatsRead], status_code=status.HTTP_200_OK)
def list_user_stats(
    user_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    _current_admin: User = Depends(require_active_admin),
) -> list[UserStats]:
    return list_user_stats_workflow(db, user_id=user_id)


# Retired public/admin scaffold. Stats remain internally service-owned.
@router.patch("/{user_id}", status_code=status.HTTP_410_GONE)
def update_user_stats(
    user_id: uuid.UUID,
    _current_admin: User = Depends(require_active_admin),
) -> None:
    del user_id, _current_admin
    raise_retired_mutation_route(
        code="user_stats_scaffold_removed",
        message=(
            "Direct user stats updates are no longer supported. Stats are "
            "maintained by product-owned workflows."
        ),
    )
