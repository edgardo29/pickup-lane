import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import UserSettings, User
from backend.schemas import UserSettingsCreate, UserSettingsRead, UserSettingsUpdate
from backend.services.auth_service import get_current_app_user, require_active_admin
from backend.services.user_settings_service import (
    create_user_settings_workflow,
    get_current_user_settings,
    get_user_settings_or_404,
    update_current_user_settings,
    update_user_settings_workflow,
)

router = APIRouter(prefix="/user-settings", tags=["user-settings"])


# This route creates the one-to-one settings record for an existing user.
@router.post("", response_model=UserSettingsRead, status_code=status.HTTP_201_CREATED)
def create_user_settings(
    user_settings: UserSettingsCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> UserSettings:
    return create_user_settings_workflow(db, user_settings)


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


# This route applies partial updates to an existing settings record.
@router.patch(
    "/{user_id}", response_model=UserSettingsRead, status_code=status.HTTP_200_OK
)
def update_user_settings(
    user_id: uuid.UUID,
    user_settings_update: UserSettingsUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> UserSettings:
    return update_user_settings_workflow(db, user_id, user_settings_update)
