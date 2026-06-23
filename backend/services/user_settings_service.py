"""User settings reads and protected create/update workflows."""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import User, UserSettings
from backend.schemas.user_settings_schema import UserSettingsCreate, UserSettingsUpdate
from backend.services.user_service import get_current_user_profile


def build_default_user_settings(user_id: uuid.UUID) -> UserSettings:
    return UserSettings(
        user_id=user_id,
        push_notifications_enabled=False,
        email_notifications_enabled=False,
        sms_notifications_enabled=False,
        marketing_opt_in=False,
        location_permission_status="unknown",
    )


def build_user_settings_conflict_detail(exc: IntegrityError) -> str:
    # user_id is both the primary key and foreign key, so a create conflict
    # usually means settings already exist for that user.
    error_text = str(exc.orig)

    if "user_settings_pkey" in error_text:
        return "Settings already exist for this user."

    return error_text


def get_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    db_user = db.get(User, user_id)

    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return db_user


def get_user_settings_or_404(db: Session, user_id: uuid.UUID) -> UserSettings:
    db_user_settings = db.get(UserSettings, user_id)

    if db_user_settings is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User settings not found.",
        )

    return db_user_settings


def create_user_settings_workflow(
    db: Session,
    user_settings: UserSettingsCreate,
) -> UserSettings:
    get_user_or_404(db, user_settings.user_id)

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


def get_current_user_settings(db: Session, current_user: User) -> UserSettings:
    db_user = get_current_user_profile(db, current_user)
    return get_user_settings_or_404(db, db_user.id)


def update_current_user_settings(
    db: Session,
    current_user: User,
    user_settings_update: UserSettingsUpdate,
) -> UserSettings:
    db_user = get_current_user_profile(db, current_user)
    db_user_settings = db.get(UserSettings, db_user.id)

    if db_user_settings is None:
        db_user_settings = build_default_user_settings(db_user.id)

    update_data = user_settings_update.model_dump(exclude_unset=True)
    return update_user_settings_instance(db, db_user_settings, update_data)


def update_user_settings_instance(
    db: Session,
    db_user_settings: UserSettings,
    update_data: dict[str, object],
) -> UserSettings:
    for field_name, field_value in update_data.items():
        setattr(db_user_settings, field_name, field_value)

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


def update_user_settings_workflow(
    db: Session,
    user_id: uuid.UUID,
    user_settings_update: UserSettingsUpdate,
) -> UserSettings:
    db_user_settings = get_user_settings_or_404(db, user_id)
    update_data = user_settings_update.model_dump(exclude_unset=True)
    return update_user_settings_instance(db, db_user_settings, update_data)
