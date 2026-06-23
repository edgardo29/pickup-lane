"""User stats validation, reads, and protected create/update workflows."""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import User, UserStats
from backend.schemas.user_stats_schema import UserStatsCreate, UserStatsUpdate
from backend.services.user_service import get_current_user_profile

COUNT_FIELDS = {
    "games_played_count",
    "games_hosted_completed_count",
    "no_show_count",
    "late_cancel_count",
    "host_cancel_count",
}


def build_user_stats_conflict_detail(exc: IntegrityError) -> str:
    error_text = str(exc.orig)

    if "user_stats_pkey" in error_text:
        return "This user already has stats."

    return error_text


def get_active_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    db_user = db.get(User, user_id)

    if db_user is None or db_user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return db_user


def get_user_stats_or_404(db: Session, user_id: uuid.UUID) -> UserStats:
    db_user_stats = db.get(UserStats, user_id)

    if db_user_stats is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User stats not found.",
        )

    return db_user_stats


def validate_user_stats_business_rules(stats_data: dict[str, object]) -> None:
    if stats_data["user_id"] is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id cannot be null.",
        )

    for field_name in COUNT_FIELDS:
        if stats_data[field_name] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} cannot be null.",
            )

        if stats_data[field_name] < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} must be greater than or equal to 0.",
            )


def validate_user_stats_update_rules(update_data: dict[str, object]) -> None:
    for field_name, field_value in update_data.items():
        if field_name in COUNT_FIELDS:
            if field_value is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{field_name} cannot be null.",
                )

            if field_value < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{field_name} must be greater than or equal to 0.",
                )

    if "last_calculated_at" in update_data and update_data["last_calculated_at"] is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="last_calculated_at cannot be null.",
        )


def normalize_user_stats_fields(stats_data: dict[str, object]) -> dict[str, object]:
    normalized_data = dict(stats_data)

    if normalized_data["last_calculated_at"] is None:
        normalized_data["last_calculated_at"] = datetime.now(timezone.utc)

    return normalized_data


def validate_user_stats_references(db: Session, stats_data: dict[str, object]) -> None:
    get_active_user_or_404(db, stats_data["user_id"])


def create_user_stats_workflow(
    db: Session,
    user_stats: UserStatsCreate,
) -> UserStats:
    stats_data = normalize_user_stats_fields(user_stats.model_dump())
    validate_user_stats_business_rules(stats_data)
    validate_user_stats_references(db, stats_data)

    new_user_stats = UserStats(**stats_data)

    try:
        db.add(new_user_stats)
        db.commit()
        db.refresh(new_user_stats)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_user_stats_conflict_detail(exc),
        ) from exc

    return new_user_stats


def get_current_user_stats(db: Session, current_user: User) -> UserStats:
    db_user = get_current_user_profile(db, current_user)
    return get_user_stats_or_404(db, db_user.id)


def get_user_stats_record(db: Session, user_id: uuid.UUID) -> UserStats:
    db_user_stats = get_user_stats_or_404(db, user_id)
    get_active_user_or_404(db, db_user_stats.user_id)
    return db_user_stats


def list_user_stats(
    db: Session,
    *,
    user_id: uuid.UUID | None = None,
) -> list[UserStats]:
    statement = select(UserStats).join(User, UserStats.user_id == User.id).where(
        User.deleted_at.is_(None)
    )

    if user_id is not None:
        statement = statement.where(UserStats.user_id == user_id)

    user_stats_rows = db.scalars(
        statement.order_by(UserStats.last_calculated_at.desc())
    ).all()
    return list(user_stats_rows)


def update_user_stats_workflow(
    db: Session,
    user_id: uuid.UUID,
    user_stats_update: UserStatsUpdate,
) -> UserStats:
    db_user_stats = get_user_stats_record(db, user_id)
    update_data = user_stats_update.model_dump(exclude_unset=True)
    validate_user_stats_update_rules(update_data)

    for field_name, field_value in update_data.items():
        setattr(db_user_stats, field_name, field_value)

    db_user_stats.last_calculated_at = update_data.get(
        "last_calculated_at",
        datetime.now(timezone.utc),
    )

    try:
        db.add(db_user_stats)
        db.commit()
        db.refresh(db_user_stats)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_user_stats_conflict_detail(exc),
        ) from exc

    return db_user_stats
