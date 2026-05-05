import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Game, GameParticipant, Payment, User, Venue
from backend.schemas import GameCreate, GameHostEdit, GameRead, GameUpdate

router = APIRouter(prefix="/games", tags=["games"])

VALID_GAME_TYPES = {"official", "community"}
VALID_PUBLISH_STATUSES = {"draft", "published", "archived"}
VALID_GAME_STATUSES = {"scheduled", "full", "cancelled", "completed", "abandoned"}
VALID_ENVIRONMENT_TYPES = {"indoor", "outdoor"}
VALID_POLICY_MODES = {"official_standard", "custom_hosted"}
VALID_CURRENCY = "USD"
HOST_EDITABLE_GAME_STATUSES = {"scheduled", "full"}
ACTIVE_PLAYER_STATUSES = {"pending_payment", "confirmed", "waitlisted"}
RESERVED_PLAYER_STATUSES = {"pending_payment", "confirmed"}
LOCATION_FIELDS = {
    "venue_name",
    "address_line_1",
    "city",
    "state",
    "postal_code",
    "neighborhood",
}
MAJOR_HOST_EDIT_FIELDS = {
    "starts_at",
    "ends_at",
    "format_label",
    "environment_type",
    "price_per_player_cents",
}
NON_NULL_HOST_EDIT_FIELDS = MAJOR_HOST_EDIT_FIELDS | {
    "total_spots",
    "venue_name",
    "address_line_1",
    "city",
    "state",
    "postal_code",
}


def build_game_conflict_detail(exc: IntegrityError) -> str:
    # The games table does not currently expose user-facing unique constraints,
    # so fall back to the database error text for now if an integrity issue
    # occurs.
    return str(exc.orig)


def get_active_venue_or_404(db: Session, venue_id: uuid.UUID) -> Venue:
    db_venue = db.get(Venue, venue_id)

    if db_venue is None or db_venue.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venue not found.",
        )

    return db_venue


def get_active_user_or_404(db: Session, user_id: uuid.UUID, detail: str) -> User:
    db_user = db.get(User, user_id)

    if db_user is None or db_user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )

    return db_user


def count_non_host_participants(
    db: Session, game_id: uuid.UUID, participant_statuses: set[str]
) -> int:
    return db.scalar(
        select(func.count())
        .select_from(GameParticipant)
        .where(
            GameParticipant.game_id == game_id,
            GameParticipant.participant_type != "host",
            GameParticipant.participant_status.in_(participant_statuses),
        )
    ) or 0


def game_has_paid_booking_payment(db: Session, game_id: uuid.UUID) -> bool:
    return (
        db.scalar(
            select(Payment.id)
            .where(
                Payment.game_id == game_id,
                Payment.payment_type == "booking",
                Payment.payment_status.in_(
                    {"succeeded", "partially_refunded", "disputed"}
                ),
            )
            .limit(1)
        )
        is not None
    )


def create_host_edit_venue(
    db: Session, db_game: Game, game_update: GameHostEdit
) -> Venue:
    venue_name = (game_update.venue_name or "").strip()
    address_line_1 = (game_update.address_line_1 or "").strip()
    city = (game_update.city or "").strip()
    state_value = (game_update.state or "").strip()
    postal_code = (game_update.postal_code or "").strip()
    neighborhood = (game_update.neighborhood or "").strip() or None

    if not all([venue_name, address_line_1, city, state_value, postal_code]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Location edits require venue name, street, city, state, and postal code.",
        )

    new_venue = Venue(
        id=uuid.uuid4(),
        name=venue_name,
        address_line_1=address_line_1,
        city=city,
        state=state_value,
        postal_code=postal_code,
        country_code="US",
        neighborhood=neighborhood,
        venue_status="approved",
        created_by_user_id=db_game.host_user_id,
        approved_by_user_id=db_game.host_user_id,
        approved_at=datetime.now(timezone.utc),
        is_active=True,
    )
    db.add(new_venue)
    db.flush()
    return new_venue


def build_host_edit_address_snapshot(game_update: GameHostEdit) -> str:
    state_line = " ".join(
        value
        for value in [
            (game_update.state or "").strip(),
            (game_update.postal_code or "").strip(),
        ]
        if value
    )
    city_line = ", ".join(
        value
        for value in [(game_update.city or "").strip(), state_line]
        if value
    )
    return ", ".join(
        value
        for value in [(game_update.address_line_1 or "").strip(), city_line]
        if value
    )


def host_edit_changes_location(db: Session, db_game: Game, game_update: GameHostEdit) -> bool:
    update_data = game_update.model_dump(exclude_unset=True)

    if not LOCATION_FIELDS.intersection(update_data):
        return False

    db_venue = db.get(Venue, db_game.venue_id)
    existing_values = {
        "venue_name": db_venue.name if db_venue is not None else db_game.venue_name_snapshot,
        "address_line_1": (
            db_venue.address_line_1
            if db_venue is not None
            else db_game.address_snapshot.split(",")[0].strip()
        ),
        "city": db_venue.city if db_venue is not None else db_game.city_snapshot,
        "state": db_venue.state if db_venue is not None else db_game.state_snapshot,
        "postal_code": db_venue.postal_code if db_venue is not None else "",
        "neighborhood": (
            db_venue.neighborhood
            if db_venue is not None
            else db_game.neighborhood_snapshot
        )
        or "",
    }

    for field_name in LOCATION_FIELDS:
        if field_name not in update_data:
            continue

        if (update_data[field_name] or "").strip() != existing_values[field_name]:
            return True

    return False


def ensure_timezone(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value


def host_edit_field_changed(db_game: Game, field_name: str, new_value: object) -> bool:
    current_value = getattr(db_game, field_name)

    if field_name in {"starts_at", "ends_at"}:
        return ensure_timezone(current_value) != ensure_timezone(new_value)

    return current_value != new_value


def validate_game_business_rules(game_data: dict[str, object]) -> None:
    if game_data["game_type"] not in VALID_GAME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="game_type must be 'official' or 'community'.",
        )

    if game_data["publish_status"] not in VALID_PUBLISH_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="publish_status must be 'draft', 'published', or 'archived'.",
        )

    if game_data["game_status"] not in VALID_GAME_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "game_status must be 'scheduled', 'full', 'cancelled', "
                "'completed', or 'abandoned'."
            ),
        )

    if game_data["environment_type"] not in VALID_ENVIRONMENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="environment_type must be 'indoor' or 'outdoor'.",
        )

    if game_data["policy_mode"] not in VALID_POLICY_MODES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="policy_mode must be 'official_standard' or 'custom_hosted'.",
        )

    if game_data["currency"] != VALID_CURRENCY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="currency must be 'USD'.",
        )

    if game_data["ends_at"] <= game_data["starts_at"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ends_at must be greater than starts_at.",
        )

    if game_data["total_spots"] <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="total_spots must be greater than 0.",
        )

    if game_data["price_per_player_cents"] < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="price_per_player_cents must be greater than or equal to 0.",
        )

    if game_data["max_guests_per_booking"] < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="max_guests_per_booking must be greater than or equal to 0.",
        )

    if game_data["minimum_age"] is not None and game_data["minimum_age"] < 13:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="minimum_age must be null or greater than or equal to 13.",
        )

    if game_data["game_type"] == "community" and game_data["host_user_id"] is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Community games require host_user_id.",
        )

    if (
        game_data["game_type"] == "official"
        and game_data["policy_mode"] != "official_standard"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Official games require policy_mode 'official_standard'.",
        )

    if (
        game_data["game_type"] == "community"
        and game_data["policy_mode"] != "custom_hosted"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Community games require policy_mode 'custom_hosted'.",
        )


def normalize_game_lifecycle_fields(
    game_data: dict[str, object], existing_game: Game | None = None
) -> dict[str, object]:
    normalized_data = dict(game_data)
    now = datetime.now(timezone.utc)

    if normalized_data["publish_status"] == "published":
        normalized_data["published_at"] = (
            normalized_data.get("published_at")
            or (existing_game.published_at if existing_game is not None else None)
            or now
        )
    else:
        normalized_data["published_at"] = None

    if normalized_data["game_status"] == "cancelled":
        normalized_data["cancelled_at"] = (
            normalized_data.get("cancelled_at")
            or (existing_game.cancelled_at if existing_game is not None else None)
            or now
        )
        normalized_data["completed_at"] = None
        normalized_data["completed_by_user_id"] = None
    elif normalized_data["game_status"] == "completed":
        normalized_data["completed_at"] = (
            normalized_data.get("completed_at")
            or (existing_game.completed_at if existing_game is not None else None)
            or now
        )
        normalized_data["cancelled_at"] = None
        normalized_data["cancelled_by_user_id"] = None
        normalized_data["cancel_reason"] = None
    else:
        normalized_data["cancelled_at"] = None
        normalized_data["cancelled_by_user_id"] = None
        normalized_data["cancel_reason"] = None
        normalized_data["completed_at"] = None
        normalized_data["completed_by_user_id"] = None

    return normalized_data


# This route creates the core game listing record after validating the related
# venue and user references that the row depends on.
@router.post("", response_model=GameRead, status_code=status.HTTP_201_CREATED)
def create_game(game: GameCreate, db: Session = Depends(get_db)) -> Game:
    get_active_venue_or_404(db, game.venue_id)
    get_active_user_or_404(db, game.created_by_user_id, "Created-by user not found.")

    if game.host_user_id is not None:
        get_active_user_or_404(db, game.host_user_id, "Host user not found.")

    if game.cancelled_by_user_id is not None:
        get_active_user_or_404(
            db, game.cancelled_by_user_id, "Cancelled-by user not found."
        )

    if game.completed_by_user_id is not None:
        get_active_user_or_404(
            db, game.completed_by_user_id, "Completed-by user not found."
        )

    normalized_game_data = normalize_game_lifecycle_fields(game.model_dump())
    validate_game_business_rules(normalized_game_data)

    new_game = Game(
        id=uuid.uuid4(),
        **normalized_game_data,
    )

    try:
        db.add(new_game)
        db.commit()
        db.refresh(new_game)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_conflict_detail(exc),
        ) from exc

    return new_game


# This route fetches a single game record by its internal UUID.
@router.get("/{game_id}", response_model=GameRead, status_code=status.HTTP_200_OK)
def get_game(game_id: uuid.UUID, db: Session = Depends(get_db)) -> Game:
    db_game = db.get(Game, game_id)

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    return db_game


# This route returns game records currently stored in the app database.
@router.get("", response_model=list[GameRead], status_code=status.HTTP_200_OK)
def list_games(db: Session = Depends(get_db)) -> list[Game]:
    games = db.scalars(
        select(Game)
        .where(Game.deleted_at.is_(None))
        .order_by(Game.starts_at.asc(), Game.created_at.asc())
    ).all()
    return list(games)


# This route applies partial updates to an existing game record.
@router.patch("/{game_id}", response_model=GameRead, status_code=status.HTTP_200_OK)
def update_game(
    game_id: uuid.UUID, game_update: GameUpdate, db: Session = Depends(get_db)
) -> Game:
    db_game = db.get(Game, game_id)

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    if game_update.venue_id is not None:
        get_active_venue_or_404(db, game_update.venue_id)

    if game_update.created_by_user_id is not None:
        get_active_user_or_404(
            db, game_update.created_by_user_id, "Created-by user not found."
        )

    if game_update.host_user_id is not None:
        get_active_user_or_404(db, game_update.host_user_id, "Host user not found.")

    if game_update.cancelled_by_user_id is not None:
        get_active_user_or_404(
            db, game_update.cancelled_by_user_id, "Cancelled-by user not found."
        )

    if game_update.completed_by_user_id is not None:
        get_active_user_or_404(
            db, game_update.completed_by_user_id, "Completed-by user not found."
        )

    update_data = game_update.model_dump(exclude_unset=True)
    effective_game_data = {
        "game_type": update_data.get("game_type", db_game.game_type),
        "publish_status": update_data.get("publish_status", db_game.publish_status),
        "game_status": update_data.get("game_status", db_game.game_status),
        "title": update_data.get("title", db_game.title),
        "description": update_data.get("description", db_game.description),
        "venue_id": update_data.get("venue_id", db_game.venue_id),
        "venue_name_snapshot": update_data.get(
            "venue_name_snapshot", db_game.venue_name_snapshot
        ),
        "address_snapshot": update_data.get(
            "address_snapshot", db_game.address_snapshot
        ),
        "city_snapshot": update_data.get("city_snapshot", db_game.city_snapshot),
        "state_snapshot": update_data.get("state_snapshot", db_game.state_snapshot),
        "neighborhood_snapshot": update_data.get(
            "neighborhood_snapshot", db_game.neighborhood_snapshot
        ),
        "host_user_id": update_data.get("host_user_id", db_game.host_user_id),
        "created_by_user_id": update_data.get(
            "created_by_user_id", db_game.created_by_user_id
        ),
        "starts_at": update_data.get("starts_at", db_game.starts_at),
        "ends_at": update_data.get("ends_at", db_game.ends_at),
        "timezone": update_data.get("timezone", db_game.timezone),
        "sport_type": update_data.get("sport_type", db_game.sport_type),
        "format_label": update_data.get("format_label", db_game.format_label),
        "environment_type": update_data.get(
            "environment_type", db_game.environment_type
        ),
        "total_spots": update_data.get("total_spots", db_game.total_spots),
        "price_per_player_cents": update_data.get(
            "price_per_player_cents", db_game.price_per_player_cents
        ),
        "currency": update_data.get("currency", db_game.currency),
        "minimum_age": update_data.get("minimum_age", db_game.minimum_age),
        "allow_guests": update_data.get("allow_guests", db_game.allow_guests),
        "max_guests_per_booking": update_data.get(
            "max_guests_per_booking", db_game.max_guests_per_booking
        ),
        "waitlist_enabled": update_data.get(
            "waitlist_enabled", db_game.waitlist_enabled
        ),
        "is_chat_enabled": update_data.get(
            "is_chat_enabled", db_game.is_chat_enabled
        ),
        "policy_mode": update_data.get("policy_mode", db_game.policy_mode),
        "custom_rules_text": update_data.get(
            "custom_rules_text", db_game.custom_rules_text
        ),
        "custom_cancellation_text": update_data.get(
            "custom_cancellation_text", db_game.custom_cancellation_text
        ),
        "game_notes": update_data.get("game_notes", db_game.game_notes),
        "arrival_notes": update_data.get("arrival_notes", db_game.arrival_notes),
        "parking_notes": update_data.get("parking_notes", db_game.parking_notes),
        "published_at": update_data.get("published_at", db_game.published_at),
        "cancelled_at": update_data.get("cancelled_at", db_game.cancelled_at),
        "cancelled_by_user_id": update_data.get(
            "cancelled_by_user_id", db_game.cancelled_by_user_id
        ),
        "cancel_reason": update_data.get("cancel_reason", db_game.cancel_reason),
        "completed_at": update_data.get("completed_at", db_game.completed_at),
        "completed_by_user_id": update_data.get(
            "completed_by_user_id", db_game.completed_by_user_id
        ),
    }
    effective_game_data = normalize_game_lifecycle_fields(effective_game_data, db_game)
    validate_game_business_rules(effective_game_data)

    # Lifecycle fields are managed from the fully merged game state so partial
    # PATCH payloads cannot accidentally keep stale timestamps or status notes.
    for lifecycle_field in (
        "published_at",
        "cancelled_at",
        "cancelled_by_user_id",
        "cancel_reason",
        "completed_at",
        "completed_by_user_id",
    ):
        update_data[lifecycle_field] = effective_game_data[lifecycle_field]

    for field_name, field_value in update_data.items():
        setattr(db_game, field_name, field_value)

    # Keep updated_at aligned with the latest game change so downstream clients
    # can reliably track when the record was last modified.
    db_game.updated_at = datetime.now(timezone.utc)

    try:
        db.add(db_game)
        db.commit()
        db.refresh(db_game)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_conflict_detail(exc),
        ) from exc

    return db_game


@router.patch(
    "/{game_id}/host-edit", response_model=GameRead, status_code=status.HTTP_200_OK
)
def host_edit_game(
    game_id: uuid.UUID, game_update: GameHostEdit, db: Session = Depends(get_db)
) -> Game:
    db_game = db.get(Game, game_id)

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    get_active_user_or_404(db, game_update.acting_user_id, "Acting user not found.")

    if db_game.game_type != "community":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only community games can be edited by hosts.",
        )

    if db_game.host_user_id != game_update.acting_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the game host can edit this game.",
        )

    if (
        db_game.publish_status != "published"
        or db_game.game_status not in HOST_EDITABLE_GAME_STATUSES
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only published scheduled or full games can be edited.",
        )

    update_data = game_update.model_dump(exclude_unset=True)
    update_data.pop("acting_user_id", None)

    if any(
        field in update_data and update_data[field] is None
        for field in NON_NULL_HOST_EDIT_FIELDS
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Host edit fields cannot be null.",
        )

    location_changed = host_edit_changes_location(db, db_game, game_update)
    active_player_count = count_non_host_participants(
        db, game_id, ACTIVE_PLAYER_STATUSES
    )
    reserved_player_count = count_non_host_participants(
        db, game_id, RESERVED_PLAYER_STATUSES
    )
    paid_booking_exists = game_has_paid_booking_payment(db, game_id)

    if active_player_count > 0:
        changed_major_fields = [
            field_name
            for field_name in MAJOR_HOST_EDIT_FIELDS
            if field_name in update_data
            and host_edit_field_changed(db_game, field_name, update_data[field_name])
        ]

        if location_changed or changed_major_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Date, time, location, format, indoor/outdoor, and price "
                    "cannot be changed after players have joined."
                ),
            )

        if (
            "total_spots" in update_data
            and update_data["total_spots"] < db_game.total_spots
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Capacity can only be increased after players have joined.",
            )

    if (
        paid_booking_exists
        and "price_per_player_cents" in update_data
        and update_data["price_per_player_cents"] != db_game.price_per_player_cents
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Price cannot be changed after a booking payment exists.",
        )

    effective_starts_at = ensure_timezone(
        update_data.get("starts_at", db_game.starts_at)
    )
    effective_ends_at = ensure_timezone(update_data.get("ends_at", db_game.ends_at))

    if effective_starts_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game start time must be in the future.",
        )

    if effective_ends_at <= effective_starts_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ends_at must be greater than starts_at.",
        )

    if (
        "total_spots" in update_data
        and update_data["total_spots"] < reserved_player_count
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="total_spots cannot be less than confirmed players.",
        )

    if location_changed:
        new_venue = create_host_edit_venue(db, db_game, game_update)
        update_data["venue_id"] = new_venue.id
        update_data["venue_name_snapshot"] = new_venue.name
        update_data["address_snapshot"] = build_host_edit_address_snapshot(game_update)
        update_data["city_snapshot"] = new_venue.city
        update_data["state_snapshot"] = new_venue.state
        update_data["neighborhood_snapshot"] = new_venue.neighborhood
        update_data["title"] = f"{new_venue.name} {update_data.get('format_label', db_game.format_label)}"
    elif "format_label" in update_data and update_data["format_label"] != db_game.format_label:
        update_data["title"] = f"{db_game.venue_name_snapshot} {update_data['format_label']}"

    effective_game_data = {
        "game_type": db_game.game_type,
        "publish_status": db_game.publish_status,
        "game_status": db_game.game_status,
        "title": update_data.get("title", db_game.title),
        "description": update_data.get("description", db_game.description),
        "venue_id": update_data.get("venue_id", db_game.venue_id),
        "venue_name_snapshot": update_data.get(
            "venue_name_snapshot", db_game.venue_name_snapshot
        ),
        "address_snapshot": update_data.get(
            "address_snapshot", db_game.address_snapshot
        ),
        "city_snapshot": update_data.get("city_snapshot", db_game.city_snapshot),
        "state_snapshot": update_data.get("state_snapshot", db_game.state_snapshot),
        "neighborhood_snapshot": update_data.get(
            "neighborhood_snapshot", db_game.neighborhood_snapshot
        ),
        "host_user_id": db_game.host_user_id,
        "created_by_user_id": db_game.created_by_user_id,
        "starts_at": effective_starts_at,
        "ends_at": effective_ends_at,
        "timezone": db_game.timezone,
        "sport_type": db_game.sport_type,
        "format_label": update_data.get("format_label", db_game.format_label),
        "environment_type": update_data.get(
            "environment_type", db_game.environment_type
        ),
        "total_spots": update_data.get("total_spots", db_game.total_spots),
        "price_per_player_cents": update_data.get(
            "price_per_player_cents", db_game.price_per_player_cents
        ),
        "currency": db_game.currency,
        "minimum_age": db_game.minimum_age,
        "allow_guests": db_game.allow_guests,
        "max_guests_per_booking": db_game.max_guests_per_booking,
        "waitlist_enabled": db_game.waitlist_enabled,
        "is_chat_enabled": db_game.is_chat_enabled,
        "policy_mode": db_game.policy_mode,
        "custom_rules_text": db_game.custom_rules_text,
        "custom_cancellation_text": db_game.custom_cancellation_text,
        "game_notes": update_data.get("game_notes", db_game.game_notes),
        "arrival_notes": update_data.get("arrival_notes", db_game.arrival_notes),
        "parking_notes": update_data.get("parking_notes", db_game.parking_notes),
        "published_at": db_game.published_at,
        "cancelled_at": db_game.cancelled_at,
        "cancelled_by_user_id": db_game.cancelled_by_user_id,
        "cancel_reason": db_game.cancel_reason,
        "completed_at": db_game.completed_at,
        "completed_by_user_id": db_game.completed_by_user_id,
    }
    validate_game_business_rules(effective_game_data)

    for field_name, field_value in update_data.items():
        if field_name in LOCATION_FIELDS:
            continue

        setattr(db_game, field_name, field_value)

    db_game.updated_at = datetime.now(timezone.utc)

    try:
        db.add(db_game)
        db.commit()
        db.refresh(db_game)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_conflict_detail(exc),
        ) from exc

    return db_game


# This route performs a soft delete so the game record remains available for
# history and operational review without appearing in normal game listings.
@router.delete("/{game_id}", response_model=GameRead, status_code=status.HTTP_200_OK)
def delete_game(game_id: uuid.UUID, db: Session = Depends(get_db)) -> Game:
    db_game = db.get(Game, game_id)

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    db_game.updated_at = datetime.now(timezone.utc)
    db_game.deleted_at = datetime.now(timezone.utc)

    try:
        db.add(db_game)
        db.commit()
        db.refresh(db_game)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_conflict_detail(exc),
        ) from exc

    return db_game
