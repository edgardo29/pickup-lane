import uuid
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import (
    Booking,
    Game,
    GameParticipant,
    Notification,
    Payment,
    User,
    Venue,
    WaitlistEntry,
)
from backend.routes.venue_routes import find_matching_active_venue
from backend.schemas import (
    GameCreate,
    GameGuestAddCreate,
    GameGuestAddRead,
    GameGuestRemoveCreate,
    GameGuestRemoveRead,
    GameHostEdit,
    GameJoinCreate,
    GameJoinRead,
    GameLeaveCreate,
    GameLeaveRead,
    GameRead,
    GameUpdate,
)

router = APIRouter(prefix="/games", tags=["games"])

VALID_GAME_TYPES = {"official", "community"}
VALID_PAYMENT_COLLECTION_TYPES = {"in_app", "external_host", "none"}
VALID_PUBLISH_STATUSES = {"draft", "published", "archived"}
VALID_GAME_STATUSES = {"scheduled", "full", "cancelled", "completed", "abandoned"}
VALID_ENVIRONMENT_TYPES = {"indoor", "outdoor"}
VALID_POLICY_MODES = {"official_standard", "custom_hosted"}
VALID_CURRENCY = "USD"
HOST_EDITABLE_GAME_STATUSES = {"scheduled", "full"}
ACTIVE_PLAYER_STATUSES = {"pending_payment", "confirmed", "waitlisted"}
RESERVED_PLAYER_STATUSES = {"pending_payment", "confirmed"}
ROSTER_PLAYER_STATUSES = {"pending_payment", "confirmed"}
ACTIVE_JOIN_STATUSES = {"pending_payment", "confirmed", "waitlisted"}
ACTIVE_WAITLIST_STATUSES = {"active", "promoted"}
JOINABLE_GAME_STATUSES = {"scheduled", "full"}
MINIMUM_TOTAL_SPOTS = 6
MAXIMUM_TOTAL_SPOTS = 99
REFUND_CUTOFF_HOURS = 24
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
            .join(Booking, Payment.booking_id == Booking.id)
            .where(
                Booking.game_id == game_id,
                Payment.payment_type == "booking",
                Payment.payment_status.in_(
                    {"succeeded", "partially_refunded", "disputed"}
                ),
            )
            .limit(1)
        )
        is not None
    )


def game_requires_app_player_payment(db_game: Game) -> bool:
    return (
        db_game.game_type == "official"
        and db_game.payment_collection_type == "in_app"
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


def ensure_timezone(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value


def get_side_size_for_format(format_label: str) -> int:
    label = (format_label or "").strip().lower()
    home_side, separator, away_side = label.partition("v")

    if (
        separator != "v"
        or not home_side.isdigit()
        or not away_side.isdigit()
        or home_side != away_side
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="format_label must be a player format like '7v7'.",
        )

    return int(home_side)


def get_minimum_spots_for_format(format_label: str) -> int:
    return max(get_side_size_for_format(format_label) * 2, MINIMUM_TOTAL_SPOTS)


def get_default_host_guest_max(format_label: str) -> int:
    return max(get_side_size_for_format(format_label) - 1, 0)


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

    if game_data["payment_collection_type"] not in VALID_PAYMENT_COLLECTION_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "payment_collection_type must be 'in_app', "
                "'external_host', or 'none'."
            ),
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

    starts_at = ensure_timezone(game_data["starts_at"])
    ends_at = ensure_timezone(game_data["ends_at"])

    if ends_at <= starts_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ends_at must be greater than starts_at.",
        )

    if game_data["game_status"] in {"scheduled", "full"} and starts_at <= datetime.now(
        timezone.utc
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game start time must be in the future.",
        )

    if game_data["total_spots"] < MINIMUM_TOTAL_SPOTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"total_spots must be at least {MINIMUM_TOTAL_SPOTS}.",
        )

    if game_data["total_spots"] > MAXIMUM_TOTAL_SPOTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"total_spots must be at most {MAXIMUM_TOTAL_SPOTS}.",
        )

    format_minimum_spots = get_minimum_spots_for_format(game_data["format_label"])
    default_host_guest_max = get_default_host_guest_max(game_data["format_label"])
    if game_data["total_spots"] < format_minimum_spots:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"total_spots must be at least {format_minimum_spots} "
                f"for {game_data['format_label']}."
            ),
        )

    if game_data["price_per_player_cents"] < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="price_per_player_cents must be greater than or equal to 0.",
        )

    if (
        game_data["payment_collection_type"] == "none"
        and game_data["price_per_player_cents"] != 0
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Free games must have price_per_player_cents set to 0.",
        )

    if game_data["max_guests_per_booking"] < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="max_guests_per_booking must be greater than or equal to 0.",
        )

    if game_data.get("host_guest_max") is None:
        game_data["host_guest_max"] = default_host_guest_max

    if game_data["host_guest_max"] < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="host_guest_max must be greater than or equal to 0.",
        )

    if game_data["host_guest_max"] > default_host_guest_max:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"host_guest_max must be at most {default_host_guest_max} "
                f"for {game_data['format_label']}."
            ),
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
        game_data["game_type"] == "official"
        and game_data["payment_collection_type"] != "in_app"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Official games require payment_collection_type 'in_app'.",
        )

    if (
        game_data["game_type"] == "community"
        and game_data["policy_mode"] != "custom_hosted"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Community games require policy_mode 'custom_hosted'.",
        )

    if (
        game_data["game_type"] == "community"
        and game_data["payment_collection_type"] not in {"external_host", "none"}
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Community games require payment_collection_type "
                "'external_host' or 'none'."
            ),
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


def get_display_name(user: User) -> str:
    full_name = " ".join(
        value for value in [user.first_name, user.last_name] if value
    ).strip()
    return full_name or user.email or "Pickup Lane Player"


def require_join_ready_user(user: User) -> None:
    if not user.first_name or not user.last_name or user.date_of_birth is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Finish your profile before joining a game.",
        )


def require_minimum_age(user: User, minimum_age: int | None) -> None:
    if minimum_age is None or user.date_of_birth is None:
        return

    today = date.today()
    user_age = (
        today.year
        - user.date_of_birth.year
        - ((today.month, today.day) < (user.date_of_birth.month, user.date_of_birth.day))
    )

    if user_age < minimum_age:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You must be at least {minimum_age} years old to join this game.",
        )


def get_existing_active_participant(
    db: Session, game_id: uuid.UUID, user_id: uuid.UUID
) -> GameParticipant | None:
    return db.scalars(
        select(GameParticipant)
        .where(
            GameParticipant.game_id == game_id,
            GameParticipant.user_id == user_id,
            GameParticipant.participant_status.in_(ACTIVE_JOIN_STATUSES),
        )
        .limit(1)
    ).first()


def count_roster_players(db: Session, game_id: uuid.UUID) -> int:
    return db.scalar(
        select(func.count())
        .select_from(GameParticipant)
        .where(
            GameParticipant.game_id == game_id,
            GameParticipant.participant_status.in_(ROSTER_PLAYER_STATUSES),
        )
    ) or 0


def get_next_roster_order(db: Session, game_id: uuid.UUID) -> int:
    return (
        db.scalar(
            select(func.max(GameParticipant.roster_order)).where(
                GameParticipant.game_id == game_id,
                GameParticipant.participant_status.in_(ROSTER_PLAYER_STATUSES),
            )
        )
        or 0
    ) + 1


def validate_guest_count(db_game: Game, guest_count: int) -> int:
    if guest_count < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="guest_count must be greater than or equal to 0.",
        )

    max_guests = db_game.max_guests_per_booking if db_game.allow_guests else 0

    if guest_count > max_guests:
        if max_guests == 0:
            detail = "This game does not allow guests."
        else:
            detail = f"This game allows up to {max_guests} guests."
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    return guest_count


def get_next_waitlist_position(db: Session, game_id: uuid.UUID) -> int:
    return (
        db.scalar(
            select(func.max(WaitlistEntry.position)).where(
                WaitlistEntry.game_id == game_id,
                WaitlistEntry.waitlist_status == "active",
            )
        )
        or 0
    ) + 1


def get_existing_active_waitlist_entry(
    db: Session, game_id: uuid.UUID, user_id: uuid.UUID
) -> WaitlistEntry | None:
    return db.scalars(
        select(WaitlistEntry)
        .where(
            WaitlistEntry.game_id == game_id,
            WaitlistEntry.user_id == user_id,
            WaitlistEntry.waitlist_status.in_(ACTIVE_WAITLIST_STATUSES),
        )
        .limit(1)
    ).first()


def get_booking_participants(
    db: Session,
    game_id: uuid.UUID,
    booking_id: uuid.UUID,
    participant_statuses: set[str],
) -> list[GameParticipant]:
    return list(
        db.scalars(
            select(GameParticipant)
            .where(
                GameParticipant.game_id == game_id,
                GameParticipant.booking_id == booking_id,
                GameParticipant.participant_status.in_(participant_statuses),
            )
            .order_by(
                GameParticipant.participant_type.desc(),
                GameParticipant.roster_order.asc().nulls_last(),
                GameParticipant.joined_at.asc(),
            )
        ).all()
    )


def build_booking(
    db_game: Game,
    joining_user: User,
    party_size: int,
    now: datetime,
    *,
    is_confirmed: bool,
) -> Booking:
    subtotal_cents = db_game.price_per_player_cents * party_size
    requires_app_payment = game_requires_app_player_payment(db_game)

    if is_confirmed:
        booking_status = "confirmed"
        payment_status = "paid" if requires_app_payment else "not_required"
    else:
        booking_status = "waitlisted"
        payment_status = "unpaid" if requires_app_payment else "not_required"

    return Booking(
        id=uuid.uuid4(),
        game_id=db_game.id,
        buyer_user_id=joining_user.id,
        booking_status=booking_status,
        payment_status=payment_status,
        participant_count=party_size,
        subtotal_cents=subtotal_cents,
        platform_fee_cents=0,
        discount_cents=0,
        total_cents=subtotal_cents,
        currency=db_game.currency,
        price_per_player_snapshot_cents=db_game.price_per_player_cents,
        platform_fee_snapshot_cents=0,
        booked_at=now if is_confirmed else None,
    )


def create_booking_payment(
    db_game: Game,
    booking: Booking,
    payer_user_id: uuid.UUID,
    now: datetime,
    *,
    source: str,
) -> Payment:
    return Payment(
        id=uuid.uuid4(),
        payer_user_id=payer_user_id,
        booking_id=booking.id,
        game_id=None,
        payment_type="booking",
        provider="stripe",
        provider_payment_intent_id=f"pi_demo_booking_{booking.id}",
        provider_charge_id=f"ch_demo_booking_{booking.id}",
        idempotency_key=f"booking:{booking.id}:succeeded",
        amount_cents=booking.total_cents,
        currency=booking.currency,
        payment_status="succeeded",
        paid_at=now,
        payment_metadata={
            "source": source,
            "game_id": str(db_game.id),
            "demo": True,
        },
    )


def update_booking_payment_status(
    db: Session, booking_id: uuid.UUID, payment_status: str, now: datetime
) -> None:
    payment = db.scalars(
        select(Payment)
        .where(
            Payment.booking_id == booking_id,
            Payment.payment_type == "booking",
            Payment.payment_status.in_({"succeeded", "partially_refunded"}),
        )
        .limit(1)
    ).first()

    if payment is None:
        return

    payment.payment_status = payment_status
    payment.updated_at = now
    db.add(payment)


def build_booking_participants(
    db_game: Game,
    booking: Booking,
    joining_user: User,
    display_name: str,
    guest_count: int,
    now: datetime,
    *,
    participant_status: str,
    first_roster_order: int | None,
) -> list[GameParticipant]:
    is_confirmed = participant_status == "confirmed"
    participants = [
        GameParticipant(
            id=uuid.uuid4(),
            game_id=db_game.id,
            booking_id=booking.id,
            participant_type="registered_user",
            user_id=joining_user.id,
            display_name_snapshot=display_name,
            participant_status=participant_status,
            attendance_status="unknown" if is_confirmed else "not_applicable",
            cancellation_type="none",
            price_cents=db_game.price_per_player_cents,
            currency=db_game.currency,
            roster_order=first_roster_order,
            joined_at=now,
            confirmed_at=now if is_confirmed else None,
        )
    ]

    for index in range(guest_count):
        roster_order = first_roster_order + index + 1 if first_roster_order else None
        guest_name = f"Guest {index + 1}"
        participants.append(
            GameParticipant(
                id=uuid.uuid4(),
                game_id=db_game.id,
                booking_id=booking.id,
                participant_type="guest",
                user_id=None,
                guest_of_user_id=joining_user.id,
                guest_name=guest_name,
                display_name_snapshot=f"{display_name} guest {index + 1}",
                participant_status=participant_status,
                attendance_status="unknown" if is_confirmed else "not_applicable",
                cancellation_type="none",
                price_cents=db_game.price_per_player_cents,
                currency=db_game.currency,
                roster_order=roster_order,
                joined_at=now,
                confirmed_at=now if is_confirmed else None,
            )
        )

    return participants


def build_host_guest_participants(
    db_game: Game,
    host_user: User,
    display_name: str,
    guest_count: int,
    now: datetime,
    first_roster_order: int,
) -> list[GameParticipant]:
    return [
        GameParticipant(
            id=uuid.uuid4(),
            game_id=db_game.id,
            booking_id=None,
            participant_type="guest",
            user_id=None,
            guest_of_user_id=host_user.id,
            guest_name=f"Guest {index + 1}",
            display_name_snapshot=f"{display_name} guest {index + 1}",
            participant_status="confirmed",
            attendance_status="unknown",
            cancellation_type="none",
            price_cents=0,
            currency=db_game.currency,
            roster_order=first_roster_order + index,
            joined_at=now,
            confirmed_at=now,
        )
        for index in range(guest_count)
    ]


def is_refund_eligible(starts_at: datetime, now: datetime) -> bool:
    seconds_until_start = (ensure_timezone(starts_at) - now).total_seconds()
    return seconds_until_start >= REFUND_CUTOFF_HOURS * 60 * 60


def sync_game_capacity_status(db: Session, db_game: Game) -> None:
    roster_count = count_roster_players(db, db_game.id)
    if roster_count >= db_game.total_spots:
        db_game.game_status = "full"
    elif db_game.game_status == "full":
        db_game.game_status = "scheduled"


def create_waitlist_promotion_notification(
    db: Session,
    db_game: Game,
    waitlist_entry: WaitlistEntry,
    participant: GameParticipant,
) -> None:
    if game_requires_app_player_payment(db_game):
        body = "Enough spots opened. You were charged and moved to the player list."
    else:
        body = "Enough spots opened. You were moved to the player list."

    db.add(
        Notification(
            id=uuid.uuid4(),
            user_id=waitlist_entry.user_id,
            notification_type="waitlist_promoted",
            title="Moved into the game",
            body=body,
            related_game_id=db_game.id,
            related_booking_id=participant.booking_id,
            related_participant_id=participant.id,
            is_read=False,
        )
    )


def promote_waitlist_entries(db: Session, db_game: Game, now: datetime) -> None:
    if not db_game.waitlist_enabled:
        sync_game_capacity_status(db, db_game)
        return

    available_spots = max(db_game.total_spots - count_roster_players(db, db_game.id), 0)
    if available_spots <= 0:
        sync_game_capacity_status(db, db_game)
        return

    waitlist_entries = list(
        db.scalars(
            select(WaitlistEntry)
            .where(
                WaitlistEntry.game_id == db_game.id,
                WaitlistEntry.waitlist_status == "active",
            )
            .order_by(WaitlistEntry.position.asc(), WaitlistEntry.joined_at.asc())
        ).all()
    )

    for waitlist_entry in waitlist_entries:
        if waitlist_entry.party_size > available_spots:
            continue

        participant = get_existing_active_participant(
            db, db_game.id, waitlist_entry.user_id
        )
        if participant is None or participant.participant_status != "waitlisted":
            waitlist_entry.waitlist_status = "removed"
            waitlist_entry.updated_at = now
            db.add(waitlist_entry)
            continue

        booking = db.get(Booking, participant.booking_id) if participant.booking_id else None
        if booking is None:
            waitlist_entry.waitlist_status = "removed"
            waitlist_entry.updated_at = now
            db.add(waitlist_entry)
            continue

        booking_participants = get_booking_participants(
            db, db_game.id, booking.id, {"waitlisted"}
        )
        if len(booking_participants) != waitlist_entry.party_size:
            waitlist_entry.party_size = len(booking_participants)

        if not booking_participants or len(booking_participants) > available_spots:
            db.add(waitlist_entry)
            continue

        next_roster_order = get_next_roster_order(db, db_game.id)
        for index, booking_participant in enumerate(booking_participants):
            booking_participant.participant_status = "confirmed"
            booking_participant.attendance_status = "unknown"
            booking_participant.confirmed_at = now
            booking_participant.roster_order = next_roster_order + index
            booking_participant.updated_at = now
            db.add(booking_participant)

        booking.booking_status = "confirmed"
        booking.payment_status = (
            "paid" if game_requires_app_player_payment(db_game) else "not_required"
        )
        booking.booked_at = now
        booking.updated_at = now
        db.add(booking)
        if game_requires_app_player_payment(db_game):
            db.add(
                create_booking_payment(
                    db_game,
                    booking,
                    booking.buyer_user_id,
                    now,
                    source="waitlist_auto_promote",
                )
            )

        waitlist_entry.waitlist_status = "accepted"
        waitlist_entry.promoted_booking_id = booking.id
        waitlist_entry.promoted_at = now
        waitlist_entry.updated_at = now
        db.add(waitlist_entry)
        create_waitlist_promotion_notification(db, db_game, waitlist_entry, participant)

        available_spots -= len(booking_participants)
        if available_spots <= 0:
            break

    sync_game_capacity_status(db, db_game)


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


@router.post(
    "/{game_id}/join", response_model=GameJoinRead, status_code=status.HTTP_201_CREATED
)
def join_game(
    game_id: uuid.UUID, join_request: GameJoinCreate, db: Session = Depends(get_db)
) -> GameJoinRead:
    db_game = db.get(Game, game_id)

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    joining_user = get_active_user_or_404(
        db, join_request.acting_user_id, "Joining user not found."
    )
    require_join_ready_user(joining_user)
    require_minimum_age(joining_user, db_game.minimum_age)

    if db_game.host_user_id == joining_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hosts are already part of their own game.",
        )

    if db_game.publish_status != "published" or db_game.game_status not in JOINABLE_GAME_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This game is not open for joining.",
        )

    if ensure_timezone(db_game.starts_at) <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This game has already started.",
        )

    existing_participant = get_existing_active_participant(
        db, db_game.id, joining_user.id
    )
    if existing_participant is not None:
        if existing_participant.participant_status == "waitlisted":
            detail = "You are already on the waitlist for this game."
        else:
            detail = "You already joined this game."
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

    if get_existing_active_waitlist_entry(db, db_game.id, joining_user.id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already on the waitlist for this game.",
        )

    now = datetime.now(timezone.utc)
    roster_count = count_roster_players(db, db_game.id)
    display_name = get_display_name(joining_user)
    guest_count = validate_guest_count(db_game, join_request.guest_count)
    party_size = guest_count + 1
    spots_left = max(db_game.total_spots - roster_count, 0)

    if party_size <= spots_left:
        booking = build_booking(
            db_game,
            joining_user,
            party_size,
            now,
            is_confirmed=True,
        )
        participants = build_booking_participants(
            db_game,
            booking,
            joining_user,
            display_name,
            guest_count,
            now,
            participant_status="confirmed",
            first_roster_order=get_next_roster_order(db, db_game.id),
        )

        if roster_count + party_size >= db_game.total_spots:
            db_game.game_status = "full"

        try:
            db.add(booking)
            if game_requires_app_player_payment(db_game):
                db.add(
                    create_booking_payment(
                        db_game, booking, joining_user.id, now, source="checkout_demo"
                    )
                )
            db.add_all(participants)
            db.add(db_game)
            db.commit()
            db.refresh(participants[0])
            db.refresh(booking)
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=build_game_conflict_detail(exc),
            ) from exc

        return GameJoinRead(
            status="joined",
            message="You joined this game.",
            participant_id=participants[0].id,
            booking_id=booking.id,
        )

    if not db_game.waitlist_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not enough spots are available for this join.",
        )

    booking = build_booking(
        db_game,
        joining_user,
        party_size,
        now,
        is_confirmed=False,
    )
    waitlist_entry = WaitlistEntry(
        id=uuid.uuid4(),
        game_id=db_game.id,
        user_id=joining_user.id,
        party_size=party_size,
        position=get_next_waitlist_position(db, db_game.id),
        waitlist_status="active",
        joined_at=now,
    )
    participants = build_booking_participants(
        db_game,
        booking,
        joining_user,
        display_name,
        guest_count,
        now,
        participant_status="waitlisted",
        first_roster_order=None,
    )
    if spots_left <= 0:
        db_game.game_status = "full"

    try:
        db.add(booking)
        db.add(waitlist_entry)
        db.add_all(participants)
        db.add(db_game)
        db.commit()
        db.refresh(participants[0])
        db.refresh(booking)
        db.refresh(waitlist_entry)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_conflict_detail(exc),
        ) from exc

    return GameJoinRead(
        status="waitlisted",
        message="You joined the waitlist.",
        participant_id=participants[0].id,
        booking_id=booking.id,
        waitlist_entry_id=waitlist_entry.id,
    )


@router.post(
    "/{game_id}/leave", response_model=GameLeaveRead, status_code=status.HTTP_200_OK
)
def leave_game(
    game_id: uuid.UUID, leave_request: GameLeaveCreate, db: Session = Depends(get_db)
) -> GameLeaveRead:
    db_game = db.get(Game, game_id)

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    leaving_user = get_active_user_or_404(
        db, leave_request.acting_user_id, "Leaving user not found."
    )

    if db_game.host_user_id == leaving_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hosts cannot leave their own game from the player flow.",
        )

    participant = get_existing_active_participant(db, db_game.id, leaving_user.id)
    if participant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not currently joined to this game.",
        )

    now = datetime.now(timezone.utc)
    refundable = is_refund_eligible(db_game.starts_at, now)
    app_payment_required = game_requires_app_player_payment(db_game)
    app_refund_eligible = refundable and app_payment_required
    was_waitlisted = participant.participant_status == "waitlisted"

    waitlist_entry = get_existing_active_waitlist_entry(db, db_game.id, leaving_user.id)
    if waitlist_entry is not None:
        waitlist_entry.waitlist_status = "cancelled"
        waitlist_entry.cancelled_at = now
        waitlist_entry.updated_at = now
        db.add(waitlist_entry)

    booking = db.get(Booking, participant.booking_id) if participant.booking_id else None
    participants_to_cancel = [participant]
    if booking is not None:
        participants_to_cancel = list(
            db.scalars(
                select(GameParticipant).where(
                    GameParticipant.game_id == db_game.id,
                    GameParticipant.booking_id == booking.id,
                    GameParticipant.participant_status.in_(ACTIVE_JOIN_STATUSES),
                )
            ).all()
        )

    for booking_participant in participants_to_cancel:
        booking_participant.cancelled_at = now
        booking_participant.updated_at = now
        booking_participant.cancellation_type = (
            "on_time" if refundable or was_waitlisted else "late"
        )
        booking_participant.participant_status = (
            "cancelled" if refundable or was_waitlisted else "late_cancelled"
        )
        booking_participant.attendance_status = "not_applicable"
        db.add(booking_participant)

    if booking is not None:
        booking.booking_status = "cancelled"
        booking.payment_status = (
            "refunded"
            if app_refund_eligible and not was_waitlisted
            else booking.payment_status
        )
        booking.cancelled_at = now
        booking.cancelled_by_user_id = leaving_user.id
        if was_waitlisted:
            booking.cancel_reason = "waitlist_cancelled"
        else:
            booking.cancel_reason = (
                "player_cancelled_on_time" if refundable else "player_cancelled_late"
            )
        booking.updated_at = now
        db.add(booking)
        if app_refund_eligible and not was_waitlisted:
            update_booking_payment_status(db, booking.id, "refunded", now)

    if db_game.game_status == "full" and not was_waitlisted:
        db_game.game_status = "scheduled"

    db_game.updated_at = now
    if not was_waitlisted:
        db.flush()
        promote_waitlist_entries(db, db_game, now)

    try:
        db.add(db_game)
        db.commit()
        db.refresh(participant)
        if booking is not None:
            db.refresh(booking)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_conflict_detail(exc),
        ) from exc

    if was_waitlisted:
        message = "You left the waitlist."
    elif app_refund_eligible:
        message = "You left the game. Your payment is marked for refund."
    elif app_payment_required:
        message = "You left the game. This is within 24 hours, so no refund is due."
    else:
        message = "You left the game."

    return GameLeaveRead(
        status="left_waitlist" if was_waitlisted else "left_game",
        message=message,
        refund_eligible=app_refund_eligible and not was_waitlisted,
        participant_id=participant.id,
        booking_id=booking.id if booking is not None else None,
    )


@router.post(
    "/{game_id}/guests/add",
    response_model=GameGuestAddRead,
    status_code=status.HTTP_201_CREATED,
)
def add_host_game_guests(
    game_id: uuid.UUID,
    guest_request: GameGuestAddCreate,
    db: Session = Depends(get_db),
) -> GameGuestAddRead:
    db_game = db.get(Game, game_id)

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    acting_user = get_active_user_or_404(
        db, guest_request.acting_user_id, "Acting user not found."
    )

    if db_game.host_user_id != acting_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the game host can add host guests.",
        )

    if db_game.publish_status != "published" or db_game.game_status not in HOST_EDITABLE_GAME_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only published scheduled or full games can be updated.",
        )

    if guest_request.guest_count < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="guest_count must be greater than or equal to 0.",
        )

    guest_count = guest_request.guest_count
    if guest_count <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="guest_count must be greater than 0.",
        )

    current_host_guest_count = db.scalar(
        select(func.count())
        .select_from(GameParticipant)
        .where(
            GameParticipant.game_id == db_game.id,
            GameParticipant.guest_of_user_id == acting_user.id,
            GameParticipant.participant_type == "guest",
            GameParticipant.participant_status.in_(ACTIVE_JOIN_STATUSES),
        )
    ) or 0
    max_guests = db_game.host_guest_max if db_game.allow_guests else 0
    if current_host_guest_count + guest_count > max_guests:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This game allows up to {max_guests} host guests.",
        )

    roster_count = count_roster_players(db, db_game.id)
    if guest_count > max(db_game.total_spots - roster_count, 0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not enough spots are available for host guests.",
        )

    now = datetime.now(timezone.utc)
    guests = build_host_guest_participants(
        db_game,
        acting_user,
        get_display_name(acting_user),
        guest_count,
        now,
        get_next_roster_order(db, db_game.id),
    )
    db.add_all(guests)
    db.flush()
    sync_game_capacity_status(db, db_game)
    db_game.updated_at = now

    try:
        db.add(db_game)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_conflict_detail(exc),
        ) from exc

    return GameGuestAddRead(
        status="guests_added",
        message="Host guests added.",
        added_count=len(guests),
    )


@router.post(
    "/{game_id}/guests/remove",
    response_model=GameGuestRemoveRead,
    status_code=status.HTTP_200_OK,
)
def remove_game_guests(
    game_id: uuid.UUID,
    guest_request: GameGuestRemoveCreate,
    db: Session = Depends(get_db),
) -> GameGuestRemoveRead:
    db_game = db.get(Game, game_id)

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    acting_user = get_active_user_or_404(
        db, guest_request.acting_user_id, "Acting user not found."
    )

    if guest_request.remove_count <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="remove_count must be greater than 0.",
        )

    participant = get_existing_active_participant(db, db_game.id, acting_user.id)
    if participant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not currently joined to this game.",
        )

    now = datetime.now(timezone.utc)
    refundable = is_refund_eligible(db_game.starts_at, now)
    app_payment_required = game_requires_app_player_payment(db_game)
    was_waitlisted = participant.participant_status == "waitlisted"
    booking = db.get(Booking, participant.booking_id) if participant.booking_id else None

    if booking is not None:
        booking_participants = get_booking_participants(
            db, db_game.id, booking.id, ACTIVE_JOIN_STATUSES
        )
        guests = [
            booking_participant
            for booking_participant in booking_participants
            if booking_participant.participant_type == "guest"
        ]
    else:
        guests = list(
            db.scalars(
                select(GameParticipant)
                .where(
                    GameParticipant.game_id == db_game.id,
                    GameParticipant.guest_of_user_id == acting_user.id,
                    GameParticipant.participant_type == "guest",
                    GameParticipant.participant_status.in_(ACTIVE_JOIN_STATUSES),
                )
                .order_by(
                    GameParticipant.roster_order.desc().nulls_last(),
                    GameParticipant.joined_at.desc(),
                )
            ).all()
        )
        booking_participants = [participant, *guests]

    if len(guests) < guest_request.remove_count:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You do not have that many guests to remove.",
        )

    guests_to_remove = guests[: guest_request.remove_count]
    removed_guest_ids = {guest.id for guest in guests_to_remove}

    for guest in guests_to_remove:
        guest.cancelled_at = now
        guest.updated_at = now
        guest.cancellation_type = "on_time" if refundable or was_waitlisted else "late"
        guest.participant_status = "cancelled" if refundable or was_waitlisted else "late_cancelled"
        guest.attendance_status = "not_applicable"
        db.add(guest)

    if booking is not None:
        remaining_participants = [
            booking_participant
            for booking_participant in booking_participants
            if booking_participant.id not in removed_guest_ids
        ]
        booking.participant_count = len(remaining_participants)
        booking.subtotal_cents = db_game.price_per_player_cents * len(remaining_participants)
        booking.total_cents = booking.subtotal_cents + booking.platform_fee_cents - booking.discount_cents
        if was_waitlisted:
            booking.booking_status = "waitlisted"
            booking.payment_status = (
                "unpaid" if app_payment_required else "not_required"
            )
        else:
            booking.booking_status = "partially_cancelled"
            if refundable and app_payment_required:
                booking.payment_status = "partially_refunded"
                update_booking_payment_status(db, booking.id, "partially_refunded", now)
        booking.updated_at = now
        db.add(booking)

        waitlist_entry = get_existing_active_waitlist_entry(db, db_game.id, acting_user.id)
        if waitlist_entry is not None:
            waitlist_entry.party_size = booking.participant_count
            waitlist_entry.updated_at = now
            db.add(waitlist_entry)

    db_game.updated_at = now
    db.flush()
    promote_waitlist_entries(db, db_game, now)

    try:
        db.add(db_game)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_conflict_detail(exc),
        ) from exc

    return GameGuestRemoveRead(
        status="guests_removed",
        message="Guest attendance updated.",
        removed_count=len(guests_to_remove),
        booking_id=booking.id if booking is not None else None,
    )


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

    if "host_guest_max" in update_data:
        update_data["host_guest_max"] = effective_game_data["host_guest_max"]

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
        "custom_rules_text": db_game.custom_rules_text,
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
    validate_game_business_rules(effective_game_data)
    if "host_guest_max" in update_data:
        update_data["host_guest_max"] = effective_game_data["host_guest_max"]

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
