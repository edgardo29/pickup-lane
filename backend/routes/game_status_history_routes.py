import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Game, GameStatusHistory, User
from backend.schemas import (
    GameStatusHistoryCreate,
    GameStatusHistoryRead,
    GameStatusHistoryUpdate,
)

router = APIRouter(prefix="/game-status-history", tags=["game_status_history"])

VALID_PUBLISH_STATUSES = {"draft", "published", "archived"}
VALID_GAME_STATUSES = {"scheduled", "full", "cancelled", "completed", "abandoned"}
VALID_CHANGE_SOURCES = {
    "user",
    "host",
    "admin",
    "system",
    "payment_webhook",
    "scheduled_job",
}
IMMUTABLE_HISTORY_UPDATE_FIELDS = {
    "game_id",
    "old_publish_status",
    "new_publish_status",
    "old_game_status",
    "new_game_status",
    "changed_by_user_id",
    "change_source",
}


def build_game_status_history_conflict_detail(exc: IntegrityError) -> str:
    return str(exc.orig)


def get_active_game_or_404(db: Session, game_id: uuid.UUID) -> Game:
    db_game = db.get(Game, game_id)

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    return db_game


def get_active_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    db_user = db.get(User, user_id)

    if db_user is None or db_user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Changed by user not found.",
        )

    return db_user


def validate_game_status_history_business_rules(
    history_data: dict[str, object],
) -> None:
    for field_name in (
        "game_id",
        "new_publish_status",
        "new_game_status",
        "change_source",
    ):
        if history_data[field_name] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} cannot be null.",
            )

    if (
        history_data["old_publish_status"] is not None
        and history_data["old_publish_status"] not in VALID_PUBLISH_STATUSES
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="old_publish_status must be 'draft', 'published', or 'archived'.",
        )

    if history_data["new_publish_status"] not in VALID_PUBLISH_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="new_publish_status must be 'draft', 'published', or 'archived'.",
        )

    if (
        history_data["old_game_status"] is not None
        and history_data["old_game_status"] not in VALID_GAME_STATUSES
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "old_game_status must be 'scheduled', 'full', 'cancelled', "
                "'completed', or 'abandoned'."
            ),
        )

    if history_data["new_game_status"] not in VALID_GAME_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "new_game_status must be 'scheduled', 'full', 'cancelled', "
                "'completed', or 'abandoned'."
            ),
        )

    if history_data["change_source"] not in VALID_CHANGE_SOURCES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "change_source must be 'user', 'host', 'admin', 'system', "
                "'payment_webhook', or 'scheduled_job'."
            ),
        )

    if (
        history_data["old_publish_status"] == history_data["new_publish_status"]
        and history_data["old_game_status"] == history_data["new_game_status"]
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one publish or game status must change.",
        )


def validate_game_status_history_references(
    db: Session,
    history_data: dict[str, object],
) -> None:
    get_active_game_or_404(db, history_data["game_id"])

    if history_data["changed_by_user_id"] is not None:
        get_active_user_or_404(db, history_data["changed_by_user_id"])


def validate_game_status_history_update_fields(update_data: dict[str, object]) -> None:
    immutable_fields = IMMUTABLE_HISTORY_UPDATE_FIELDS & update_data.keys()

    if immutable_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Game status history lifecycle fields cannot be changed "
                "after creation."
            ),
        )


# This route records one append-only game lifecycle audit row after validating
# the game, optional actor, status values, and change source.
@router.post(
    "",
    response_model=GameStatusHistoryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_game_status_history(
    game_status_history: GameStatusHistoryCreate,
    db: Session = Depends(get_db),
) -> GameStatusHistory:
    history_data = game_status_history.model_dump()
    validate_game_status_history_business_rules(history_data)
    validate_game_status_history_references(db, history_data)

    new_game_status_history = GameStatusHistory(
        id=uuid.uuid4(),
        **history_data,
    )

    try:
        db.add(new_game_status_history)
        db.commit()
        db.refresh(new_game_status_history)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_status_history_conflict_detail(exc),
        ) from exc

    return new_game_status_history


# This route fetches a single game status history row by its internal UUID.
@router.get(
    "/{history_id}",
    response_model=GameStatusHistoryRead,
    status_code=status.HTTP_200_OK,
)
def get_game_status_history(
    history_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> GameStatusHistory:
    db_history = db.get(GameStatusHistory, history_id)

    if db_history is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game status history not found.",
        )

    return db_history


# This route returns game status history rows currently stored in the app
# database, ordered from oldest to newest for audit readability.
@router.get(
    "",
    response_model=list[GameStatusHistoryRead],
    status_code=status.HTTP_200_OK,
)
def list_game_status_history(
    game_id: uuid.UUID | None = None,
    changed_by_user_id: uuid.UUID | None = None,
    change_source: str | None = None,
    db: Session = Depends(get_db),
) -> list[GameStatusHistory]:
    statement = select(GameStatusHistory)

    if game_id is not None:
        statement = statement.where(GameStatusHistory.game_id == game_id)

    if changed_by_user_id is not None:
        statement = statement.where(
            GameStatusHistory.changed_by_user_id == changed_by_user_id
        )

    if change_source is not None:
        if change_source not in VALID_CHANGE_SOURCES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "change_source must be 'user', 'host', 'admin', 'system', "
                    "'payment_webhook', or 'scheduled_job'."
                ),
            )
        statement = statement.where(GameStatusHistory.change_source == change_source)

    history_rows = db.scalars(
        statement.order_by(GameStatusHistory.created_at.asc())
    ).all()
    return list(history_rows)


# This route allows correcting the explanatory reason on an audit row while
# keeping the recorded lifecycle change itself immutable.
@router.patch(
    "/{history_id}",
    response_model=GameStatusHistoryRead,
    status_code=status.HTTP_200_OK,
)
def update_game_status_history(
    history_id: uuid.UUID,
    history_update: GameStatusHistoryUpdate,
    db: Session = Depends(get_db),
) -> GameStatusHistory:
    db_history = db.get(GameStatusHistory, history_id)

    if db_history is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game status history not found.",
        )

    update_data = history_update.model_dump(exclude_unset=True)
    validate_game_status_history_update_fields(update_data)

    if "change_reason" in update_data:
        db_history.change_reason = update_data["change_reason"]

    try:
        db.add(db_history)
        db.commit()
        db.refresh(db_history)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_status_history_conflict_detail(exc),
        ) from exc

    return db_history
