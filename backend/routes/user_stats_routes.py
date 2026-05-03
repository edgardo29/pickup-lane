import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, UserStats
from backend.schemas import UserStatsCreate, UserStatsRead, UserStatsUpdate

router = APIRouter(prefix="/user-stats", tags=["user_stats"])

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


# This route creates the cached stats row for one active user. The underlying
# source of truth remains game_participants, participant history, and games.
@router.post("", response_model=UserStatsRead, status_code=status.HTTP_201_CREATED)
def create_user_stats(
    user_stats: UserStatsCreate,
    db: Session = Depends(get_db),
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


# This route fetches the cached stats row for one user.
@router.get("/{user_id}", response_model=UserStatsRead, status_code=status.HTTP_200_OK)
def get_user_stats(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> UserStats:
    db_user_stats = db.get(UserStats, user_id)

    if db_user_stats is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User stats not found.",
        )

    get_active_user_or_404(db, db_user_stats.user_id)

    return db_user_stats


# This route returns cached user stats rows currently stored in the app database.
@router.get("", response_model=list[UserStatsRead], status_code=status.HTTP_200_OK)
def list_user_stats(
    user_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
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


# This route updates cached stats after recalculation or manual admin correction.
@router.patch("/{user_id}", response_model=UserStatsRead, status_code=status.HTTP_200_OK)
def update_user_stats(
    user_id: uuid.UUID,
    user_stats_update: UserStatsUpdate,
    db: Session = Depends(get_db),
) -> UserStats:
    db_user_stats = db.get(UserStats, user_id)

    if db_user_stats is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User stats not found.",
        )

    get_active_user_or_404(db, db_user_stats.user_id)

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
