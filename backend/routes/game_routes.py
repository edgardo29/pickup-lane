import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.admin_permission_service import (
    PERMISSION_COMMUNITY_GAMES_WRITE,
    PERMISSION_OFFICIAL_GAMES_WRITE,
)
from backend.services.auth_service import require_active_user, require_any_admin_permission
from backend.models import (
    Game,
    GameParticipant,
    User,
    Venue,
)
from backend.services.game_service import (
    ACTIVE_PLAYER_STATUSES,
    GAME_UPDATED_GAME_STATUSES,
    GAME_UPDATED_PARTICIPANT_STATUSES,
    GAME_UPDATED_PARTICIPANT_TYPES,
    GAME_UPDATED_STRUCTURAL_FIELDS,
    HOST_EDITABLE_GAME_STATUSES,
    LOCATION_FIELDS,
    MAJOR_HOST_EDIT_FIELDS,
    NON_NULL_HOST_EDIT_FIELDS,
    OFFICIAL_FORCED_FIELDS,
    RESERVED_PLAYER_STATUSES,
    count_non_host_participants,
    build_game_conflict_detail,
    ensure_timezone,
    game_has_paid_booking_payment,
    get_active_user_or_404,
    get_active_venue_or_404,
    get_default_host_guest_max,
    get_existing_active_participant,
    list_public_game_participant_counts,
    list_public_game_participants,
    host_edit_field_changed,
    normalize_game_lifecycle_fields,
    normalize_official_game_invariants,
    reject_direct_official_host_change,
    reject_official_location_change,
    require_game_not_started,
    require_roster_window_open,
    validate_game_business_rules,
)
from backend.services.game_cancellation_service import (
    cancel_game_state_workflow,
    game_updated_aggregation_key,
)
from backend.services.game_roster_service import (
    add_booking_game_guests_workflow,
    add_host_game_guests_workflow,
    join_game_roster_workflow,
    leave_game_roster_workflow,
    remove_game_guests_workflow,
)
from backend.services.notification_event_service import (
    build_game_notification_fields,
    reopen_aggregated_notification,
    resolve_aggregated_notification,
)
from backend.services.venue_service import find_matching_active_venue
from backend.schemas import (
    GameCancelCreate,
    GameCreate,
    GameGuestAddCreate,
    GameGuestAddRead,
    GameGuestRemoveCreate,
    GameGuestRemoveRead,
    GameHostEdit,
    GameParticipantCountRead,
    GameJoinCreate,
    GameJoinRead,
    GameLeaveCreate,
    GameLeaveRead,
    PublicGameParticipantRead,
    GameRead,
    GameUpdate,
)

router = APIRouter(prefix="/games", tags=["games"])


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

    matching_venue = find_matching_active_venue(
        db,
        name=venue_name,
        address_line_1=address_line_1,
        city=city,
        state=state_value,
        postal_code=postal_code,
        country_code="US",
        neighborhood=neighborhood,
    )
    if matching_venue is not None:
        return matching_venue

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


def host_edit_changes_location(
    db: Session, db_game: Game, game_update: GameHostEdit
) -> bool:
    update_data = game_update.model_dump(exclude_unset=True)

    if not LOCATION_FIELDS.intersection(update_data):
        return False

    db_venue = db.get(Venue, db_game.venue_id)
    existing_values = {
        "venue_name": (
            db_venue.name if db_venue is not None else db_game.venue_name_snapshot
        ),
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


def capture_game_updated_structural_snapshot(db_game: Game) -> dict[str, object]:
    snapshot = {
        field_name: getattr(db_game, field_name)
        for field_name in GAME_UPDATED_STRUCTURAL_FIELDS
    }

    for field_name in ("starts_at", "ends_at"):
        value = snapshot[field_name]
        if isinstance(value, datetime):
            snapshot[field_name] = ensure_timezone(value)

    return snapshot


def game_updated_structural_snapshot_changed(
    before: dict[str, object],
    db_game: Game,
) -> bool:
    after = capture_game_updated_structural_snapshot(db_game)
    return any(before[field_name] != after[field_name] for field_name in before)


def list_game_updated_recipient_user_ids(
    db: Session,
    db_game: Game,
    actor_user_id: uuid.UUID | None,
) -> list[uuid.UUID]:
    user_ids: set[uuid.UUID] = set()

    if db_game.host_user_id is not None:
        user_ids.add(db_game.host_user_id)

    participant_user_ids = db.scalars(
        select(GameParticipant.user_id).where(
            GameParticipant.game_id == db_game.id,
            GameParticipant.user_id.is_not(None),
            GameParticipant.participant_type.in_(GAME_UPDATED_PARTICIPANT_TYPES),
            GameParticipant.participant_status.in_(GAME_UPDATED_PARTICIPANT_STATUSES),
        )
    ).all()
    user_ids.update(user_id for user_id in participant_user_ids if user_id is not None)

    if actor_user_id is not None:
        user_ids.discard(actor_user_id)

    return sorted(user_ids, key=str)


def notify_connected_users_game_updated(
    db: Session,
    *,
    db_game: Game,
    actor_user_id: uuid.UUID | None,
    event_at: datetime,
) -> None:
    if (
        db_game.publish_status != "published"
        or db_game.game_status not in GAME_UPDATED_GAME_STATUSES
        or db_game.deleted_at is not None
    ):
        return

    recipient_user_ids = list_game_updated_recipient_user_ids(
        db,
        db_game,
        actor_user_id,
    )
    if not recipient_user_ids:
        return

    for recipient_user_id in recipient_user_ids:
        aggregation_key = game_updated_aggregation_key(db_game.id, recipient_user_id)
        notification_fields = build_game_notification_fields(
            db_game,
            "game_updated",
            event_at=event_at,
            aggregation_key=aggregation_key,
        )
        notification_fields.update(
            {
                "actor_user_id": actor_user_id,
                "related_game_id": db_game.id,
            }
        )
        reopen_aggregated_notification(
            db,
            user_id=recipient_user_id,
            notification_type="game_updated",
            notification_category="game_activity",
            notification_domain="game",
            aggregation_key=aggregation_key,
            values=notification_fields,
            aggregate_count_mode="clear",
        )


# This route creates the core game listing record after validating the related
# venue and user references that the row depends on.
@router.post("", response_model=GameRead, status_code=status.HTTP_201_CREATED)
def create_game(
    game: GameCreate,
    db: Session = Depends(get_db),
    _current_admin: User = Depends(
        require_any_admin_permission(
            PERMISSION_OFFICIAL_GAMES_WRITE,
            PERMISSION_COMMUNITY_GAMES_WRITE,
        )
    ),
) -> Game:
    game_data = normalize_official_game_invariants(
        game.model_dump(), is_create=True
    )
    get_active_venue_or_404(db, game_data["venue_id"])
    get_active_user_or_404(
        db, game_data["created_by_user_id"], "Created-by user not found."
    )

    if game_data["host_user_id"] is not None:
        get_active_user_or_404(db, game_data["host_user_id"], "Host user not found.")

    if game_data["cancelled_by_user_id"] is not None:
        get_active_user_or_404(
            db, game_data["cancelled_by_user_id"], "Cancelled-by user not found."
        )

    if game_data["completed_by_user_id"] is not None:
        get_active_user_or_404(
            db, game_data["completed_by_user_id"], "Completed-by user not found."
        )

    normalized_game_data = normalize_official_game_invariants(
        normalize_game_lifecycle_fields(game_data), is_create=True
    )
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


@router.post(
    "/{game_id}/join", response_model=GameJoinRead, status_code=status.HTTP_201_CREATED
)
def join_game(
    game_id: uuid.UUID,
    join_request: GameJoinCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> GameJoinRead:
    return join_game_roster_workflow(db, game_id, join_request, current_user)


@router.post(
    "/{game_id}/leave", response_model=GameLeaveRead, status_code=status.HTTP_200_OK
)
def leave_game(
    game_id: uuid.UUID,
    leave_request: GameLeaveCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> GameLeaveRead:
    return leave_game_roster_workflow(db, game_id, current_user)


@router.post(
    "/{game_id}/booking-guests/add",
    response_model=GameGuestAddRead,
    status_code=status.HTTP_201_CREATED,
)
def add_booking_game_guests(
    game_id: uuid.UUID,
    guest_request: GameGuestAddCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> GameGuestAddRead:
    return add_booking_game_guests_workflow(db, game_id, guest_request, current_user)


@router.post(
    "/{game_id}/guests/add",
    response_model=GameGuestAddRead,
    status_code=status.HTTP_201_CREATED,
)
def add_host_game_guests(
    game_id: uuid.UUID,
    guest_request: GameGuestAddCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> GameGuestAddRead:
    return add_host_game_guests_workflow(db, game_id, guest_request, current_user)


@router.post(
    "/{game_id}/guests/remove",
    response_model=GameGuestRemoveRead,
    status_code=status.HTTP_200_OK,
)
def remove_game_guests(
    game_id: uuid.UUID,
    guest_request: GameGuestRemoveCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> GameGuestRemoveRead:
    return remove_game_guests_workflow(db, game_id, guest_request, current_user)


@router.post(
    "/{game_id}/cancel",
    response_model=GameRead,
    status_code=status.HTTP_200_OK,
)
def cancel_game(
    game_id: uuid.UUID,
    cancel_request: GameCancelCreate,
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> Game:
    return cancel_game_state_workflow(db, game_id, cancel_request, current_user)


@router.get(
    "/participant-counts",
    response_model=list[GameParticipantCountRead],
    status_code=status.HTTP_200_OK,
)
def list_game_participant_counts(
    db: Session = Depends(get_db),
) -> list[dict[str, object]]:
    return list_public_game_participant_counts(db)


@router.get(
    "/{game_id}/participants",
    response_model=list[PublicGameParticipantRead],
    status_code=status.HTTP_200_OK,
)
def list_game_roster_participants(
    game_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> list[GameParticipant]:
    return list_public_game_participants(db, game_id)


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
    game_id: uuid.UUID,
    game_update: GameUpdate,
    db: Session = Depends(get_db),
    _current_admin: User = Depends(
        require_any_admin_permission(
            PERMISSION_OFFICIAL_GAMES_WRITE,
            PERMISSION_COMMUNITY_GAMES_WRITE,
        )
    ),
) -> Game:
    db_game = db.get(Game, game_id)

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    update_data = game_update.model_dump(exclude_unset=True)
    if "game_type" in update_data and update_data["game_type"] != db_game.game_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="game_type cannot be changed after creation.",
        )

    reject_official_location_change(db_game, update_data)
    reject_direct_official_host_change(db_game, update_data)

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

    now = datetime.now(timezone.utc)
    require_game_not_started(db_game, now, "Games cannot be edited after start time.")
    structural_snapshot_before = capture_game_updated_structural_snapshot(db_game)

    if "format_label" in update_data and "host_guest_max" not in update_data:
        update_data["host_guest_max"] = get_default_host_guest_max(
            update_data["format_label"]
        )

    effective_game_data = {
        "game_type": update_data.get("game_type", db_game.game_type),
        "payment_collection_type": update_data.get(
            "payment_collection_type", db_game.payment_collection_type
        ),
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
        "game_player_group": update_data.get(
            "game_player_group", db_game.game_player_group
        ),
        "skill_level": update_data.get("skill_level", db_game.skill_level),
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
        "host_guest_max": update_data.get("host_guest_max", db_game.host_guest_max),
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
    effective_game_data = normalize_official_game_invariants(
        normalize_game_lifecycle_fields(effective_game_data, db_game)
    )
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

    if "host_guest_max" in update_data:
        update_data["host_guest_max"] = effective_game_data["host_guest_max"]
    if effective_game_data["game_type"] == "official":
        for field_name in OFFICIAL_FORCED_FIELDS:
            if (
                field_name in update_data
                or getattr(db_game, field_name) != effective_game_data[field_name]
            ):
                update_data[field_name] = effective_game_data[field_name]
    update_data["starts_on_local"] = effective_game_data["starts_on_local"]

    for field_name, field_value in update_data.items():
        setattr(db_game, field_name, field_value)

    # Keep updated_at aligned with the latest game change so downstream clients
    # can reliably track when the record was last modified.
    db_game.updated_at = now
    if game_updated_structural_snapshot_changed(structural_snapshot_before, db_game):
        notify_connected_users_game_updated(
            db,
            db_game=db_game,
            actor_user_id=None,
            event_at=now,
        )

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
    game_id: uuid.UUID,
    game_update: GameHostEdit,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_active_user),
) -> Game:
    db_game = db.get(Game, game_id)

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    if db_game.game_type != "community":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only community games can be edited by hosts.",
        )

    if db_game.host_user_id != current_user.id:
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

    now = datetime.now(timezone.utc)
    require_game_not_started(db_game, now, "Games cannot be edited after start time.")
    structural_snapshot_before = capture_game_updated_structural_snapshot(db_game)

    update_data = game_update.model_dump(exclude_unset=True)
    if "format_label" in update_data:
        update_data["host_guest_max"] = get_default_host_guest_max(
            update_data["format_label"]
        )

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

    if effective_starts_at <= now:
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
    elif (
        "format_label" in update_data
        and update_data["format_label"] != db_game.format_label
    ):
        update_data["title"] = f"{db_game.venue_name_snapshot} {update_data['format_label']}"

    effective_game_data = {
        "game_type": db_game.game_type,
        "payment_collection_type": db_game.payment_collection_type,
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
        "game_player_group": update_data.get(
            "game_player_group", db_game.game_player_group
        ),
        "skill_level": update_data.get("skill_level", db_game.skill_level),
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
        "host_guest_max": update_data.get("host_guest_max", db_game.host_guest_max),
        "waitlist_enabled": db_game.waitlist_enabled,
        "is_chat_enabled": db_game.is_chat_enabled,
        "policy_mode": db_game.policy_mode,
        "custom_rules_text": update_data.get(
            "custom_rules_text", db_game.custom_rules_text
        ),
        "custom_cancellation_text": db_game.custom_cancellation_text,
        "game_notes": update_data.get("game_notes", db_game.game_notes),
        "parking_notes": update_data.get("parking_notes", db_game.parking_notes),
        "published_at": db_game.published_at,
        "cancelled_at": db_game.cancelled_at,
        "cancelled_by_user_id": db_game.cancelled_by_user_id,
        "cancel_reason": db_game.cancel_reason,
        "completed_at": db_game.completed_at,
        "completed_by_user_id": db_game.completed_by_user_id,
    }
    effective_game_data = normalize_game_lifecycle_fields(effective_game_data, db_game)
    validate_game_business_rules(effective_game_data)
    if "host_guest_max" in update_data:
        update_data["host_guest_max"] = effective_game_data["host_guest_max"]
    update_data["starts_on_local"] = effective_game_data["starts_on_local"]

    for field_name, field_value in update_data.items():
        if field_name in LOCATION_FIELDS:
            continue

        setattr(db_game, field_name, field_value)

    db_game.updated_at = now
    if game_updated_structural_snapshot_changed(structural_snapshot_before, db_game):
        notify_connected_users_game_updated(
            db,
            db_game=db_game,
            actor_user_id=current_user.id,
            event_at=now,
        )

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
def delete_game(
    game_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_admin: User = Depends(
        require_any_admin_permission(
            PERMISSION_OFFICIAL_GAMES_WRITE,
            PERMISSION_COMMUNITY_GAMES_WRITE,
        )
    ),
) -> Game:
    db_game = db.get(Game, game_id)

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    if db_game.game_type == "official":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Official games must be cancelled instead of deleted.",
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
