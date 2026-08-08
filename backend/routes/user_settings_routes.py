import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import UserSettings, User
from backend.routes.retired_route_helpers import raise_retired_mutation_route
from backend.schemas import UserSettingsRead, UserSettingsUpdate
from backend.services.auth_service import get_current_app_user, require_active_admin
from backend.services.user_settings_service import (
    get_current_user_settings,
    get_user_settings_or_404,
    update_current_user_settings,
)

router = APIRouter(prefix="/user-settings", tags=["user-settings"])


# Retired generic write scaffold. `/user-settings/me` remains the active surface.
@router.post("", status_code=status.HTTP_410_GONE)
def create_user_settings(
    current_admin: User = Depends(require_active_admin),
) -> None:
    del current_admin
    raise_retired_mutation_route(
        code="user_settings_scaffold_removed",
        message=(
            "Direct user settings creation is no longer supported. Use the "
            "current user's settings endpoint."
        ),
    )


@router.get("/me", response_model=UserSettingsRead, status_code=status.HTTP_200_OK)
def get_my_user_settings(
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> UserSettings:
    return get_current_user_settings(db, current_user)


@router.patch("/me", response_model=UserSettingsRead, status_code=status.HTTP_200_OK)
def update_my_user_settings(
    user_settings_update: UserSettingsUpdate,
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> UserSettings:
    return update_current_user_settings(db, current_user, user_settings_update)


# This route fetches the one-to-one settings record for a specific user.
@router.get(
    "/{user_id}", response_model=UserSettingsRead, status_code=status.HTTP_200_OK
)
def get_user_settings(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> UserSettings:
    return get_user_settings_or_404(db, user_id)


# Retired generic write scaffold. `/user-settings/me` remains the active surface.
@router.patch(
    "/{user_id}",
    status_code=status.HTTP_410_GONE,
)
def update_user_settings(
    user_id: uuid.UUID,
    current_admin: User = Depends(require_active_admin),
) -> None:
    del user_id, current_admin
    raise_retired_mutation_route(
        code="user_settings_scaffold_removed",
        message=(
            "Direct user settings updates are no longer supported. Use the "
            "current user's settings endpoint."
        ),
    )
