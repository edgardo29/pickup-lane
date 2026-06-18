import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Booking, Game, User, WaitlistEntry
from backend.schemas import (
    CurrentUserWaitlistEntryRead,
    WaitlistEntryCreate,
    WaitlistEntryRead,
    WaitlistEntryUpdate,
)
from backend.services.admin_permission_service import (
    PERMISSION_OFFICIAL_GAMES_ROSTER_MANAGE,
)
from backend.services.auth_service import (
    get_current_app_user,
    require_admin_permission,
    require_user_admin_permission,
)
from backend.services.game_waitlist_service import list_current_user_waitlist_entries

router = APIRouter(prefix="/waitlist-entries", tags=["waitlist_entries"])

VALID_WAITLIST_STATUSES = {
    "active",
    "promoted",
    "accepted",
    "declined",
    "expired",
    "cancelled",
    "removed",
    "payment_processing",
    "payment_failed",
}
PROMOTION_HISTORY_WAITLIST_STATUSES = {
    "promoted",
    "accepted",
    "declined",
    "expired",
    "payment_processing",
    "payment_failed",
}
BOOKING_TIED_WAITLIST_STATUSES = {
    "accepted",
    "payment_processing",
    "payment_failed",
}
JOIN_WINDOW_MINUTES = 5


def ensure_timezone(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value


def build_waitlist_entry_conflict_detail(exc: IntegrityError) -> str:
    error_text = str(exc.orig)

    if "ux_waitlist_entries_active_user_per_game" in error_text:
        return "This user already has an active waitlist entry for this game."

    if "ux_waitlist_entries_active_position_per_game" in error_text:
        return "This game already has an active waitlist entry at this position."

    return error_text


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
            detail="User not found.",
        )

    return db_user


def get_booking_or_404(db: Session, booking_id: uuid.UUID) -> Booking:
    db_booking = db.get(Booking, booking_id)

    if db_booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Promoted booking not found.",
        )

    return db_booking


def validate_waitlist_entry_business_rules(
    waitlist_entry_data: dict[str, object],
) -> None:
    for field_name in (
        "game_id",
        "user_id",
        "party_size",
        "position",
        "waitlist_status",
    ):
        if waitlist_entry_data[field_name] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} cannot be null.",
            )

    if waitlist_entry_data["waitlist_status"] not in VALID_WAITLIST_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "waitlist_status must be 'active', 'promoted', 'accepted', "
                "'declined', 'expired', 'cancelled', 'removed', "
                "'payment_processing', or 'payment_failed'."
            ),
        )

    if waitlist_entry_data["party_size"] <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="party_size must be greater than 0.",
        )

    if waitlist_entry_data["position"] <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="position must be greater than 0.",
        )

    if (
        waitlist_entry_data["waitlist_status"] == "promoted"
        and waitlist_entry_data["promotion_expires_at"] is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Promoted waitlist entries require promotion_expires_at.",
        )

    if (
        waitlist_entry_data["waitlist_status"] == "active"
        and waitlist_entry_data["promoted_booking_id"] is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Active waitlist entries cannot include promoted_booking_id.",
        )

    if (
        waitlist_entry_data["waitlist_status"] in BOOKING_TIED_WAITLIST_STATUSES
        and waitlist_entry_data["promoted_booking_id"] is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"{waitlist_entry_data['waitlist_status']} waitlist entries "
                "require promoted_booking_id."
            ),
        )

    authorized_amount_cents = waitlist_entry_data.get("authorized_amount_cents")
    if authorized_amount_cents is not None and authorized_amount_cents < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="authorized_amount_cents must be greater than or equal to 0.",
        )


def validate_game_accepts_waitlist_status(
    db_game: Game, waitlist_status: str | None
) -> None:
    if (
        waitlist_status in {"active", "promoted", "payment_processing"}
        and not db_game.waitlist_enabled
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This game does not have waitlist enabled.",
        )

    join_window_closes_at = ensure_timezone(db_game.starts_at) + timedelta(
        minutes=JOIN_WINDOW_MINUTES
    )
    if (
        waitlist_status in {"active", "promoted", "payment_processing"}
        and datetime.now(timezone.utc) >= join_window_closes_at
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The waitlist is closed for this game.",
        )


def normalize_waitlist_entry_lifecycle_fields(
    waitlist_entry_data: dict[str, object],
    existing_waitlist_entry: WaitlistEntry | None = None,
) -> dict[str, object]:
    normalized_data = dict(waitlist_entry_data)
    now = datetime.now(timezone.utc)

    normalized_data["joined_at"] = (
        normalized_data.get("joined_at")
        or (
            existing_waitlist_entry.joined_at
            if existing_waitlist_entry is not None
            else None
        )
        or now
    )

    # Keep promoted_at as historical context after a promoted entry is accepted,
    # declined, or expires.
    if normalized_data["waitlist_status"] in PROMOTION_HISTORY_WAITLIST_STATUSES:
        normalized_data["promoted_at"] = (
            normalized_data.get("promoted_at")
            or (
                existing_waitlist_entry.promoted_at
                if existing_waitlist_entry is not None
                else None
            )
            or now
        )
    else:
        normalized_data["promoted_at"] = None

    if normalized_data["waitlist_status"] in {"cancelled", "payment_failed"}:
        normalized_data["cancelled_at"] = (
            normalized_data.get("cancelled_at")
            or (
                existing_waitlist_entry.cancelled_at
                if existing_waitlist_entry is not None
                else None
            )
            or now
        )
    else:
        normalized_data["cancelled_at"] = None

    if normalized_data["waitlist_status"] == "expired":
        normalized_data["expired_at"] = (
            normalized_data.get("expired_at")
            or (
                existing_waitlist_entry.expired_at
                if existing_waitlist_entry is not None
                else None
            )
            or now
        )
    else:
        normalized_data["expired_at"] = None

    if normalized_data["waitlist_status"] != "promoted":
        normalized_data["promotion_expires_at"] = None

    return normalized_data


# This route creates one waitlist entry after validating the linked game, user,
# and optional promoted booking references.
@router.post("", response_model=WaitlistEntryRead, status_code=status.HTTP_201_CREATED)
def create_waitlist_entry(
    waitlist_entry: WaitlistEntryCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_OFFICIAL_GAMES_ROSTER_MANAGE)
    ),
) -> WaitlistEntry:
    del current_admin
    db_game = get_active_game_or_404(db, waitlist_entry.game_id)
    get_active_user_or_404(db, waitlist_entry.user_id)

    if waitlist_entry.promoted_booking_id is not None:
        db_booking = get_booking_or_404(db, waitlist_entry.promoted_booking_id)

        if db_booking.game_id != waitlist_entry.game_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="promoted_booking_id must belong to the same game_id.",
            )

    normalized_waitlist_entry_data = normalize_waitlist_entry_lifecycle_fields(
        waitlist_entry.model_dump()
    )
    validate_game_accepts_waitlist_status(
        db_game, normalized_waitlist_entry_data["waitlist_status"]
    )
    validate_waitlist_entry_business_rules(normalized_waitlist_entry_data)

    new_waitlist_entry = WaitlistEntry(
        id=uuid.uuid4(),
        **normalized_waitlist_entry_data,
    )

    try:
        db.add(new_waitlist_entry)
        db.commit()
        db.refresh(new_waitlist_entry)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_waitlist_entry_conflict_detail(exc),
        ) from exc

    return new_waitlist_entry


@router.get(
    "/me",
    response_model=list[CurrentUserWaitlistEntryRead],
    status_code=status.HTTP_200_OK,
)
def list_my_waitlist_entries(
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> list[WaitlistEntry]:
    return list_current_user_waitlist_entries(db, current_user)


# This route fetches a single waitlist entry by its internal UUID.
@router.get(
    "/{waitlist_entry_id}",
    response_model=WaitlistEntryRead,
    status_code=status.HTTP_200_OK,
)
def get_waitlist_entry(
    waitlist_entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_app_user),
) -> WaitlistEntry:
    db_waitlist_entry = db.get(WaitlistEntry, waitlist_entry_id)

    if db_waitlist_entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Waitlist entry not found.",
        )

    if db_waitlist_entry.user_id != current_user.id:
        require_user_admin_permission(
            current_user,
            PERMISSION_OFFICIAL_GAMES_ROSTER_MANAGE,
        )

    return db_waitlist_entry


# This route returns waitlist entries currently stored in the app database.
@router.get("", response_model=list[WaitlistEntryRead], status_code=status.HTTP_200_OK)
def list_waitlist_entries(
    game_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    waitlist_status: str | None = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_OFFICIAL_GAMES_ROSTER_MANAGE)
    ),
) -> list[WaitlistEntry]:
    del current_admin
    statement = select(WaitlistEntry)

    if game_id is not None:
        statement = statement.where(WaitlistEntry.game_id == game_id)

    if user_id is not None:
        statement = statement.where(WaitlistEntry.user_id == user_id)

    if waitlist_status is not None:
        if waitlist_status not in VALID_WAITLIST_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "waitlist_status must be 'active', 'promoted', 'accepted', "
                    "'declined', 'expired', 'cancelled', or 'removed'."
                ),
            )
        statement = statement.where(WaitlistEntry.waitlist_status == waitlist_status)

    waitlist_entries = db.scalars(
        statement.order_by(
            WaitlistEntry.position.asc(),
            WaitlistEntry.joined_at.asc(),
        )
    ).all()
    return list(waitlist_entries)


# This route applies partial updates to an existing waitlist entry while keeping
# required relationships and lifecycle timestamps aligned with the status.
@router.patch(
    "/{waitlist_entry_id}",
    response_model=WaitlistEntryRead,
    status_code=status.HTTP_200_OK,
)
def update_waitlist_entry(
    waitlist_entry_id: uuid.UUID,
    waitlist_entry_update: WaitlistEntryUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_OFFICIAL_GAMES_ROSTER_MANAGE)
    ),
) -> WaitlistEntry:
    del current_admin
    db_waitlist_entry = db.get(WaitlistEntry, waitlist_entry_id)

    if db_waitlist_entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Waitlist entry not found.",
        )

    update_data = waitlist_entry_update.model_dump(exclude_unset=True)
    effective_waitlist_entry_data = {
        "game_id": update_data.get("game_id", db_waitlist_entry.game_id),
        "user_id": update_data.get("user_id", db_waitlist_entry.user_id),
        "party_size": update_data.get("party_size", db_waitlist_entry.party_size),
        "position": update_data.get("position", db_waitlist_entry.position),
        "waitlist_status": update_data.get(
            "waitlist_status", db_waitlist_entry.waitlist_status
        ),
        "promoted_booking_id": update_data.get(
            "promoted_booking_id", db_waitlist_entry.promoted_booking_id
        ),
        "promotion_expires_at": update_data.get(
            "promotion_expires_at", db_waitlist_entry.promotion_expires_at
        ),
        "joined_at": update_data.get("joined_at", db_waitlist_entry.joined_at),
        "promoted_at": update_data.get("promoted_at", db_waitlist_entry.promoted_at),
        "cancelled_at": update_data.get(
            "cancelled_at", db_waitlist_entry.cancelled_at
        ),
        "expired_at": update_data.get("expired_at", db_waitlist_entry.expired_at),
    }

    db_game = None
    if effective_waitlist_entry_data["game_id"] is not None:
        db_game = get_active_game_or_404(db, effective_waitlist_entry_data["game_id"])

    if effective_waitlist_entry_data["user_id"] is not None:
        get_active_user_or_404(db, effective_waitlist_entry_data["user_id"])

    if effective_waitlist_entry_data["promoted_booking_id"] is not None:
        db_booking = get_booking_or_404(
            db, effective_waitlist_entry_data["promoted_booking_id"]
        )

        if db_booking.game_id != effective_waitlist_entry_data["game_id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="promoted_booking_id must belong to the same game_id.",
            )

    effective_waitlist_entry_data = normalize_waitlist_entry_lifecycle_fields(
        effective_waitlist_entry_data,
        db_waitlist_entry,
    )
    if db_game is not None and (
        "game_id" in update_data or "waitlist_status" in update_data
    ):
        validate_game_accepts_waitlist_status(
            db_game, effective_waitlist_entry_data["waitlist_status"]
        )
    validate_waitlist_entry_business_rules(effective_waitlist_entry_data)

    # Lifecycle fields are managed from the fully merged waitlist state so
    # partial PATCH payloads cannot leave stale status timestamps behind.
    for lifecycle_field in (
        "joined_at",
        "promotion_expires_at",
        "promoted_at",
        "cancelled_at",
        "expired_at",
    ):
        update_data[lifecycle_field] = effective_waitlist_entry_data[lifecycle_field]

    for field_name, field_value in update_data.items():
        setattr(db_waitlist_entry, field_name, field_value)

    db_waitlist_entry.updated_at = datetime.now(timezone.utc)

    try:
        db.add(db_waitlist_entry)
        db.commit()
        db.refresh(db_waitlist_entry)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_waitlist_entry_conflict_detail(exc),
        ) from exc

    return db_waitlist_entry
