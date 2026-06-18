"""Shared user helpers used by user-adjacent routes and services."""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import User, UserSettings, UserStats

GENERIC_USER_MUTATION_DISABLED_DETAIL = (
    "Generic user mutations are disabled. Use dedicated account support workflows."
)


def reject_generic_user_mutation() -> None:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=GENERIC_USER_MUTATION_DISABLED_DETAIL,
    )


def build_user_conflict_detail(exc: IntegrityError) -> str:
    # Map known unique-constraint failures to clearer API messages so local
    # API testing returns actionable errors instead of raw database text.
    error_text = str(exc.orig)

    constraint_messages = {
        "uq_users_auth_user_id": "A user with this auth_user_id already exists.",
        "uq_users_email": "A user with this email already exists.",
        "uq_users_phone": "A user with this phone already exists.",
        "uq_users_stripe_customer_id": (
            "A user with this stripe_customer_id already exists."
        ),
    }

    for constraint_name, message in constraint_messages.items():
        if constraint_name in error_text:
            return message

    return error_text


def get_current_user_profile(db: Session, current_user: User) -> User:
    db_user = db.get(User, current_user.id)

    if db_user is None or db_user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return db_user


def update_current_user_profile(
    db: Session,
    current_user: User,
    update_data: dict[str, object],
) -> User:
    db_user = get_current_user_profile(db, current_user)

    if (
        "email" in update_data
        and update_data["email"] != db_user.email
        and "email_verified_at" not in update_data
    ):
        db_user.email_verified_at = None

    for field_name, field_value in update_data.items():
        setattr(db_user, field_name, field_value)

    db_user.updated_at = datetime.now(timezone.utc)

    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_user_conflict_detail(exc),
        ) from exc

    return db_user


def build_default_user_settings(user_id) -> UserSettings:
    return UserSettings(
        user_id=user_id,
        push_notifications_enabled=False,
        email_notifications_enabled=False,
        sms_notifications_enabled=False,
        marketing_opt_in=False,
        location_permission_status="unknown",
    )


def get_current_user_settings(db: Session, current_user: User) -> UserSettings:
    db_user = get_current_user_profile(db, current_user)
    db_user_settings = db.get(UserSettings, db_user.id)

    if db_user_settings is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User settings not found.",
        )

    return db_user_settings


def update_current_user_settings(
    db: Session,
    current_user: User,
    update_data: dict[str, object],
) -> UserSettings:
    db_user = get_current_user_profile(db, current_user)
    db_user_settings = db.get(UserSettings, db_user.id)

    if db_user_settings is None:
        db_user_settings = build_default_user_settings(db_user.id)

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


def build_user_settings_conflict_detail(exc: IntegrityError) -> str:
    # user_id is both the primary key and foreign key, so a create conflict
    # usually means settings already exist for that user.
    error_text = str(exc.orig)

    if "user_settings_pkey" in error_text:
        return "Settings already exist for this user."

    return error_text


def get_current_user_stats(db: Session, current_user: User) -> UserStats:
    db_user = get_current_user_profile(db, current_user)
    db_user_stats = db.get(UserStats, db_user.id)

    if db_user_stats is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User stats not found.",
        )

    return db_user_stats
