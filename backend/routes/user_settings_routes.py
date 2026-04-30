from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
import uuid

from backend.database import get_db
from backend.models import User, UserSettings
from backend.schemas import UserSettingsCreate, UserSettingsRead, UserSettingsUpdate
from datetime import datetime, timezone

router = APIRouter(prefix="/user-settings", tags=["user-settings"])


def build_user_settings_conflict_detail(exc: IntegrityError) -> str:
    # user_id is both the primary key and foreign key, so a create conflict
    # usually means settings already exist for that user.
    error_text = str(exc.orig)

    if "user_settings_pkey" in error_text:
        return "Settings already exist for this user."

    return error_text


# This route creates the one-to-one settings record for an existing user.
@router.post("", response_model=UserSettingsRead, status_code=status.HTTP_201_CREATED)
def create_user_settings(
    user_settings: UserSettingsCreate, db: Session = Depends(get_db)
) -> UserSettings:
    db_user = db.get(User, user_settings.user_id)

    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    new_user_settings = UserSettings(
        user_id=user_settings.user_id,
        push_notifications_enabled=user_settings.push_notifications_enabled,
        email_notifications_enabled=user_settings.email_notifications_enabled,
        sms_notifications_enabled=user_settings.sms_notifications_enabled,
        marketing_opt_in=user_settings.marketing_opt_in,
        location_permission_status=user_settings.location_permission_status,
        selected_city=user_settings.selected_city,
        selected_state=user_settings.selected_state,
    )

    try:
        db.add(new_user_settings)
        db.commit()
        db.refresh(new_user_settings)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_user_settings_conflict_detail(exc),
        ) from exc

    return new_user_settings


# This route fetches the one-to-one settings record for a specific user.
@router.get(
    "/{user_id}", response_model=UserSettingsRead, status_code=status.HTTP_200_OK
)
def get_user_settings(user_id: uuid.UUID, db: Session = Depends(get_db)) -> UserSettings:
    db_user_settings = db.get(UserSettings, user_id)

    if db_user_settings is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User settings not found.",
        )

    return db_user_settings


# This route applies partial updates to an existing settings record.
@router.patch(
    "/{user_id}", response_model=UserSettingsRead, status_code=status.HTTP_200_OK
)
def update_user_settings(
    user_id: uuid.UUID,
    user_settings_update: UserSettingsUpdate,
    db: Session = Depends(get_db),
) -> UserSettings:
    db_user_settings = db.get(UserSettings, user_id)

    if db_user_settings is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User settings not found.",
        )

    update_data = user_settings_update.model_dump(exclude_unset=True)

    for field_name, field_value in update_data.items():
        setattr(db_user_settings, field_name, field_value)

    # Keep updated_at aligned with the latest preference change so the settings
    # record has a trustworthy modification timestamp.
    db_user_settings.updated_at = datetime.now(timezone.utc)

    try:
        db.add(db_user_settings)
        db.commit()
        db.refresh(db_user_settings)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_user_settings_conflict_detail(exc),
        ) from exc

    return db_user_settings
