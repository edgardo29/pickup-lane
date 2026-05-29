import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.routes.auth_routes import get_current_app_user, is_admin
from backend.models import (
    AdminAction,
    Booking,
    Game,
    GameChat,
    GameParticipant,
    GameStatusHistory,
    Notification,
    Payment,
    Refund,
    User,
    Venue,
    WaitlistEntry,
)
from backend.routes.venue_routes import find_matching_active_venue
from backend.services.stripe_service import (
    StripeConfigError,
    create_refund as create_stripe_refund,
)
from backend.services.game_credit_service import (
    release_reserved_game_credits,
    restore_redeemed_game_credits,
)
from backend.schemas import (
    GameCancelCreate,
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
CANCELLABLE_GAME_STATUSES = {"scheduled", "full"}
ACTIVE_PLAYER_STATUSES = {"pending_payment", "confirmed", "waitlisted"}
RESERVED_PLAYER_STATUSES = {"pending_payment", "confirmed"}
ROSTER_PLAYER_STATUSES = {"pending_payment", "confirmed"}
ACTIVE_JOIN_STATUSES = {"pending_payment", "confirmed", "waitlisted"}
ACTIVE_WAITLIST_STATUSES = {"active", "promoted"}
ACTIVE_BOOKING_STATUSES = {
    "pending_payment",
    "confirmed",
    "waitlisted",
    "partially_cancelled",
}
JOINABLE_GAME_STATUSES = {"scheduled", "full"}
OFFICIAL_FORCED_FIELDS = {
    "minimum_age",
    "host_guest_max",
    "custom_rules_text",
    "custom_cancellation_text",
}
OFFICIAL_LOCATION_FIELDS = {
    "venue_id",
    "venue_name_snapshot",
    "address_snapshot",
    "city_snapshot",
    "state_snapshot",
    "neighborhood_snapshot",
}
CANCELLATION_REFUND_FOLLOWUP_BOOKING_PAYMENT_STATUSES = {
    "paid",
    "partially_refunded",
    "refunded",
    "disputed",
}
CANCELLATION_REFUND_FOLLOWUP_PAYMENT_STATUSES = {
    "succeeded",
    "partially_refunded",
    "refunded",
    "disputed",
}
CANCELLATION_UNCHARGED_PENDING_PAYMENT_STATUSES = {
    "requires_payment_method",
    "requires_action",
}
CANCELLATION_AUTO_REFUND_PAYMENT_STATUSES = {"succeeded"}
MINIMUM_TOTAL_SPOTS = 6
MAXIMUM_TOTAL_SPOTS = 99
MAX_CANCEL_REASON_LENGTH = 500
REFUND_CUTOFF_HOURS = 24
JOIN_WINDOW_MINUTES = 5
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
    error_text = str(exc.orig)

    if "ux_games_one_active_community_game_per_host_date" in error_text:
        return "You already have a community game on this date."

    if "ck_games_official_minimum_age_null" in error_text:
        return "Official games require minimum_age to be null."

    if "ck_games_official_host_guest_max_zero" in error_text:
        return "Official games require host_guest_max to be 0."

    if "ck_games_official_no_custom_rules" in error_text:
        return "Official games cannot use custom_rules_text."

    if "ck_games_official_no_custom_cancellation" in error_text:
        return "Official games cannot use custom_cancellation_text."

    # The games table does not currently expose user-facing unique constraints,
    # so fall back to the database error text for now if an integrity issue
    # occurs.
    return error_text


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


def get_valid_timezone(timezone_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="timezone must be a valid IANA timezone.",
        ) from exc


def get_game_local_date(starts_at: datetime, timezone_name: str) -> date:
    return ensure_timezone(starts_at).astimezone(get_valid_timezone(timezone_name)).date()


def get_join_window_closes_at(db_game: Game) -> datetime:
    return ensure_timezone(db_game.starts_at) + timedelta(minutes=JOIN_WINDOW_MINUTES)


def is_roster_locked(db_game: Game, now: datetime) -> bool:
    return now >= get_join_window_closes_at(db_game)


def require_roster_window_open(db_game: Game, now: datetime, detail: str) -> None:
    if is_roster_locked(db_game, now):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def require_game_not_started(db_game: Game, now: datetime, detail: str) -> None:
    if now >= ensure_timezone(db_game.starts_at):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


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


def normalize_official_game_invariants(
    game_data: dict[str, object], *, is_create: bool = False
) -> dict[str, object]:
    normalized_data = dict(game_data)
    if normalized_data.get("game_type") != "official":
        return normalized_data

    normalized_data["minimum_age"] = None
    normalized_data["host_guest_max"] = 0
    normalized_data["custom_rules_text"] = None
    normalized_data["custom_cancellation_text"] = None

    if is_create:
        normalized_data["host_user_id"] = None

    return normalized_data


def reject_official_location_change(
    db_game: Game, update_data: dict[str, object]
) -> None:
    if db_game.game_type != "official":
        return

    for field_name in OFFICIAL_LOCATION_FIELDS:
        if field_name not in update_data:
            continue

        if update_data[field_name] == getattr(db_game, field_name):
            continue

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Official game venue/location cannot be changed. "
                "Cancel and recreate the official game instead."
            ),
        )


def reject_direct_official_host_change(
    db_game: Game, update_data: dict[str, object]
) -> None:
    if db_game.game_type != "official" or "host_user_id" not in update_data:
        return

    if update_data["host_user_id"] == db_game.host_user_id:
        return

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Use the official game host assignment route to change host_user_id.",
    )


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
    get_valid_timezone(game_data["timezone"])

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

    if game_data["game_type"] == "official":
        if game_data["minimum_age"] is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Official games require minimum_age to be null.",
            )

        if game_data["host_guest_max"] != 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Official games require host_guest_max to be 0.",
            )

        if game_data["custom_rules_text"] is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Official games cannot use custom_rules_text.",
            )

        if game_data["custom_cancellation_text"] is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Official games cannot use custom_cancellation_text.",
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
    normalized_data["starts_at"] = ensure_timezone(normalized_data["starts_at"])
    normalized_data["ends_at"] = ensure_timezone(normalized_data["ends_at"])
    normalized_data["starts_on_local"] = get_game_local_date(
        normalized_data["starts_at"],
        normalized_data["timezone"],
    )

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


def normalize_cancel_reason(cancel_reason: str | None) -> str | None:
    if cancel_reason is None:
        return None

    normalized_reason = " ".join(cancel_reason.strip().split())
    if not normalized_reason:
        return None

    if len(normalized_reason) > MAX_CANCEL_REASON_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"cancel_reason must be {MAX_CANCEL_REASON_LENGTH} characters or fewer.",
        )

    return normalized_reason


def require_cancel_permission(db_game: Game, current_user: User) -> str:
    if current_user.account_status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account cannot cancel games right now.",
        )

    if is_admin(current_user):
        return "admin_cancelled"

    if db_game.game_type == "community":
        if db_game.host_user_id == current_user.id:
            return "host_cancelled"

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the community game host or an admin can cancel this game.",
        )

    if db_game.game_type == "official":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an admin can cancel official games.",
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="This game type cannot be cancelled.",
    )


def cancel_game_participants(
    db: Session,
    db_game: Game,
    now: datetime,
    cancellation_type: str,
) -> list[uuid.UUID]:
    notified_user_ids: set[uuid.UUID] = set()
    participants = db.scalars(
        select(GameParticipant).where(
            GameParticipant.game_id == db_game.id,
            GameParticipant.participant_status.in_(ACTIVE_JOIN_STATUSES),
        )
    ).all()

    for participant in participants:
        should_notify = (
            participant.user_id is not None
            and participant.user_id != db_game.host_user_id
            and participant.participant_type in {"registered_user", "admin_added"}
            and participant.participant_status in {"confirmed", "waitlisted"}
        )
        if should_notify:
            notified_user_ids.add(participant.user_id)

        participant.participant_status = "cancelled"
        participant.cancellation_type = cancellation_type
        participant.cancelled_at = now
        participant.attendance_status = "not_applicable"
        participant.updated_at = now
        db.add(participant)

    return list(notified_user_ids)


def cancel_game_waitlist_entries(db: Session, db_game: Game, now: datetime) -> None:
    waitlist_entries = db.scalars(
        select(WaitlistEntry).where(
            WaitlistEntry.game_id == db_game.id,
            WaitlistEntry.waitlist_status.in_(ACTIVE_WAITLIST_STATUSES),
        )
    ).all()

    for waitlist_entry in waitlist_entries:
        waitlist_entry.waitlist_status = "cancelled"
        waitlist_entry.cancelled_at = now
        waitlist_entry.updated_at = now
        db.add(waitlist_entry)


def cancel_game_bookings(
    db: Session,
    db_game: Game,
    current_user: User,
    now: datetime,
    cancellation_type: str,
) -> dict[str, object]:
    bookings = db.scalars(
        select(Booking)
        .where(
            Booking.game_id == db_game.id,
            Booking.booking_status.in_(ACTIVE_BOOKING_STATUSES),
        )
        .order_by(Booking.created_at.asc(), Booking.id.asc())
    ).all()
    app_payment_required = game_requires_app_player_payment(db_game)
    payment_summary: dict[str, object] = {
        "cancelled_booking_count": 0,
        "paid_booking_count": 0,
        "processing_payment_booking_count": 0,
        "uncharged_pending_booking_count": 0,
        "refund_followup_required": False,
        "payment_followup_required": False,
        "payment_refund_created": False,
        "refund_created_count": 0,
        "refund_failed_count": 0,
        "refund_processing_count": 0,
        "refund_missing_charge_count": 0,
        "credit_restored_count": 0,
        "credit_restored_cents": 0,
        "credit_released_count": 0,
        "credit_released_cents": 0,
    }

    for booking in bookings:
        payments = db.scalars(
            select(Payment).where(
                Payment.booking_id == booking.id,
                Payment.payment_type == "booking",
            )
        ).all()

        if app_payment_required:
            payment_statuses = {payment.payment_status for payment in payments}
            has_paid_payment = bool(
                payment_statuses
                & CANCELLATION_REFUND_FOLLOWUP_PAYMENT_STATUSES
            ) or (
                booking.payment_status
                in CANCELLATION_REFUND_FOLLOWUP_BOOKING_PAYMENT_STATUSES
            )
            has_processing_payment = "processing" in payment_statuses

            if has_paid_payment:
                payment_summary["paid_booking_count"] = (
                    int(payment_summary["paid_booking_count"]) + 1
                )
                restored_credit_usages = restore_redeemed_game_credits(
                    db,
                    booking.id,
                    now=now,
                    restore_reason="game_cancelled",
                    user_id=booking.buyer_user_id,
                )
                restored_credit_cents = sum(
                    usage.amount_cents for usage in restored_credit_usages
                )
                payment_summary["credit_restored_count"] = (
                    int(payment_summary["credit_restored_count"])
                    + len(restored_credit_usages)
                )
                payment_summary["credit_restored_cents"] = (
                    int(payment_summary["credit_restored_cents"])
                    + restored_credit_cents
                )
                refund_summary = create_official_cancellation_refunds(
                    db,
                    db_game,
                    booking,
                    payments,
                    current_user,
                    now,
                )
                for key, value in refund_summary.items():
                    payment_summary[key] = int(payment_summary[key]) + value
                if refund_summary["refund_created_count"] > 0:
                    payment_summary["payment_refund_created"] = True
                booking_refund_followup_required = True
                if (
                    refund_summary["refund_failed_count"] == 0
                    and refund_summary["refund_processing_count"] == 0
                    and refund_summary["refund_missing_charge_count"] == 0
                    and all_booking_refundable_payments_refunded(payments)
                ):
                    booking.payment_status = "refunded"
                    booking_refund_followup_required = False
                elif (
                    restored_credit_cents > 0
                    and refund_summary["refund_failed_count"] == 0
                    and refund_summary["refund_processing_count"] == 0
                    and refund_summary["refund_missing_charge_count"] == 0
                    and not booking_has_refundable_payments(payments)
                ):
                    booking.payment_status = "credit_restored"
                    booking_refund_followup_required = False
                if booking_refund_followup_required:
                    payment_summary["refund_followup_required"] = True
            elif has_processing_payment:
                payment_summary["processing_payment_booking_count"] = (
                    int(payment_summary["processing_payment_booking_count"]) + 1
                )
                payment_summary["payment_followup_required"] = True
            elif booking.booking_status == "pending_payment":
                for payment in payments:
                    if (
                        payment.payment_status
                        in CANCELLATION_UNCHARGED_PENDING_PAYMENT_STATUSES
                    ):
                        payment.payment_status = "canceled"
                        payment.failure_code = "game_cancelled"
                        payment.failure_message = (
                            "Game was cancelled before payment completed."
                        )
                        payment.failure_reason = "game_cancelled"
                        payment.updated_at = now
                        db.add(payment)

                released_credit_usages = release_reserved_game_credits(
                    db,
                    booking.id,
                    now=now,
                    release_reason="game_cancelled",
                    user_id=booking.buyer_user_id,
                )
                payment_summary["credit_released_count"] = (
                    int(payment_summary["credit_released_count"])
                    + len(released_credit_usages)
                )
                payment_summary["credit_released_cents"] = (
                    int(payment_summary["credit_released_cents"])
                    + sum(usage.amount_cents for usage in released_credit_usages)
                )

                booking.payment_status = "failed"
                payment_summary["uncharged_pending_booking_count"] = (
                    int(payment_summary["uncharged_pending_booking_count"]) + 1
                )

        booking.booking_status = "cancelled"
        booking.cancelled_at = now
        booking.cancelled_by_user_id = current_user.id
        booking.cancel_reason = cancellation_type
        booking.updated_at = now
        db.add(booking)
        payment_summary["cancelled_booking_count"] = (
            int(payment_summary["cancelled_booking_count"]) + 1
        )

    return payment_summary


def map_stripe_refund_status(stripe_status: str) -> str:
    normalized_status = stripe_status.strip().lower()
    if normalized_status == "succeeded":
        return "succeeded"

    if normalized_status == "failed":
        return "failed"

    if normalized_status in {"canceled", "cancelled"}:
        return "cancelled"

    return "processing"


def all_booking_refundable_payments_refunded(payments: list[Payment]) -> bool:
    refundable_payments = [
        payment
        for payment in payments
        if payment.payment_status
        in CANCELLATION_REFUND_FOLLOWUP_PAYMENT_STATUSES
    ]
    return bool(refundable_payments) and all(
        payment.payment_status == "refunded" for payment in refundable_payments
    )


def booking_has_refundable_payments(payments: list[Payment]) -> bool:
    return any(
        payment.payment_status in CANCELLATION_REFUND_FOLLOWUP_PAYMENT_STATUSES
        for payment in payments
    )


def build_cancellation_refund_summary() -> dict[str, int]:
    return {
        "refund_created_count": 0,
        "refund_failed_count": 0,
        "refund_processing_count": 0,
        "refund_missing_charge_count": 0,
    }


def create_official_cancellation_refunds(
    db: Session,
    db_game: Game,
    booking: Booking,
    payments: list[Payment],
    current_user: User,
    now: datetime,
) -> dict[str, int]:
    summary = build_cancellation_refund_summary()

    for payment in payments:
        if payment.payment_status not in CANCELLATION_AUTO_REFUND_PAYMENT_STATUSES:
            continue

        existing_refund = db.scalars(
            select(Refund)
            .where(
                Refund.payment_id == payment.id,
                Refund.booking_id == booking.id,
                Refund.refund_reason == "game_cancelled",
                Refund.refund_status.in_(
                    {"pending", "approved", "processing", "succeeded"}
                ),
            )
            .limit(1)
        ).first()
        if existing_refund is not None:
            continue

        if not payment.provider_charge_id:
            create_cancellation_refund_record(
                db,
                payment,
                booking,
                current_user,
                now,
                provider_refund_id=None,
                refund_status="failed",
            )
            summary["refund_failed_count"] += 1
            summary["refund_missing_charge_count"] += 1
            continue

        refund_idempotency_key = (
            f"game_cancel:{db_game.id}:payment:{payment.id}:refund"
        )
        try:
            stripe_refund = create_stripe_refund(
                charge_id=payment.provider_charge_id,
                amount_cents=payment.amount_cents,
                currency=payment.currency,
                idempotency_key=refund_idempotency_key,
                metadata={
                    "source": "official_game_cancel",
                    "game_id": str(db_game.id),
                    "booking_id": str(booking.id),
                    "payment_id": str(payment.id),
                    "admin_user_id": str(current_user.id),
                },
            )
        except StripeConfigError:
            create_cancellation_refund_record(
                db,
                payment,
                booking,
                current_user,
                now,
                provider_refund_id=None,
                refund_status="failed",
            )
            summary["refund_failed_count"] += 1
            continue
        except Exception:
            create_cancellation_refund_record(
                db,
                payment,
                booking,
                current_user,
                now,
                provider_refund_id=None,
                refund_status="failed",
            )
            summary["refund_failed_count"] += 1
            continue

        refund_status = map_stripe_refund_status(stripe_refund.status)
        create_cancellation_refund_record(
            db,
            payment,
            booking,
            current_user,
            now,
            provider_refund_id=stripe_refund.id,
            refund_status=refund_status,
        )
        summary["refund_created_count"] += 1

        if refund_status == "succeeded":
            payment.payment_status = "refunded"
            payment.updated_at = now
            db.add(payment)
        elif refund_status == "failed":
            summary["refund_failed_count"] += 1
        else:
            summary["refund_processing_count"] += 1

    return summary


def create_cancellation_refund_record(
    db: Session,
    payment: Payment,
    booking: Booking,
    current_user: User,
    now: datetime,
    *,
    provider_refund_id: str | None,
    refund_status: str,
) -> Refund:
    refund = Refund(
        id=uuid.uuid4(),
        payment_id=payment.id,
        booking_id=booking.id,
        participant_id=None,
        provider_refund_id=provider_refund_id,
        amount_cents=payment.amount_cents,
        currency=payment.currency,
        refund_reason="game_cancelled",
        refund_status=refund_status,
        requested_by_user_id=current_user.id,
        approved_by_user_id=current_user.id,
        requested_at=now,
        approved_at=(
            now
            if refund_status in {"approved", "processing", "succeeded"}
            else None
        ),
        refunded_at=now if refund_status == "succeeded" else None,
        created_at=now,
        updated_at=now,
    )
    db.add(refund)
    return refund


def archive_game_chats(db: Session, db_game: Game, now: datetime) -> None:
    game_chats = db.scalars(
        select(GameChat).where(
            GameChat.game_id == db_game.id,
            GameChat.chat_status.in_({"active", "locked"}),
        )
    ).all()

    for game_chat in game_chats:
        game_chat.chat_status = "archived"
        game_chat.updated_at = now
        db.add(game_chat)


def create_game_cancelled_notifications(
    db: Session,
    db_game: Game,
    recipient_user_ids: list[uuid.UUID],
    now: datetime,
) -> None:
    if not recipient_user_ids:
        return

    game_title = db_game.title or db_game.venue_name_snapshot or "Your game"
    for recipient_user_id in sorted(set(recipient_user_ids)):
        db.add(
            Notification(
                id=uuid.uuid4(),
                user_id=recipient_user_id,
                notification_type="game_cancelled",
                title="Game cancelled",
                body=f"{game_title} was cancelled.",
                related_game_id=db_game.id,
                is_read=False,
                read_at=None,
                created_at=now,
                updated_at=now,
            )
        )


def create_game_cancellation_history(
    db: Session,
    db_game: Game,
    current_user: User,
    old_game_status: str,
    cancel_reason: str | None,
    change_source: str,
    now: datetime,
) -> None:
    db.add(
        GameStatusHistory(
            id=uuid.uuid4(),
            game_id=db_game.id,
            old_publish_status=db_game.publish_status,
            new_publish_status=db_game.publish_status,
            old_game_status=old_game_status,
            new_game_status="cancelled",
            changed_by_user_id=current_user.id,
            change_source=change_source,
            change_reason=cancel_reason,
            created_at=now,
        )
    )


def create_game_cancellation_admin_action(
    db: Session,
    db_game: Game,
    current_user: User,
    cancellation_type: str,
    old_game_status: str,
    cancel_reason: str | None,
    notified_user_ids: list[uuid.UUID],
    payment_summary: dict[str, object],
    now: datetime,
) -> None:
    if cancellation_type != "admin_cancelled":
        return

    db.add(
        AdminAction(
            id=uuid.uuid4(),
            admin_user_id=current_user.id,
            action_type="cancel_game",
            target_game_id=db_game.id,
            reason=cancel_reason,
            metadata_={
                "old_game_status": old_game_status,
                "new_game_status": "cancelled",
                "notified_user_count": len(set(notified_user_ids)),
                "cancelled_at": now.isoformat(),
                **payment_summary,
            },
            created_at=now,
        )
    )


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


def create_booking_guest_add_payment(
    db_game: Game,
    booking: Booking,
    payer_user_id: uuid.UUID,
    added_count: int,
    now: datetime,
) -> Payment:
    payment_id = uuid.uuid4()
    return Payment(
        id=payment_id,
        payer_user_id=payer_user_id,
        booking_id=booking.id,
        game_id=None,
        payment_type="booking",
        provider="stripe",
        provider_payment_intent_id=f"pi_demo_booking_add_guests_{payment_id}",
        provider_charge_id=f"ch_demo_booking_add_guests_{payment_id}",
        idempotency_key=f"booking:{booking.id}:add_guests:{payment_id}:succeeded",
        amount_cents=db_game.price_per_player_cents * added_count,
        currency=booking.currency,
        payment_status="succeeded",
        paid_at=now,
        payment_metadata={
            "source": "booking_guest_add_demo",
            "game_id": str(db_game.id),
            "added_guest_count": added_count,
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


def build_added_booking_guest_participants(
    db_game: Game,
    booking: Booking,
    joining_user: User,
    display_name: str,
    guest_count: int,
    current_guest_count: int,
    now: datetime,
    first_roster_order: int,
) -> list[GameParticipant]:
    guests = []
    for index in range(guest_count):
        guest_number = current_guest_count + index + 1
        guests.append(
            GameParticipant(
                id=uuid.uuid4(),
                game_id=db_game.id,
                booking_id=booking.id,
                participant_type="guest",
                user_id=None,
                guest_of_user_id=joining_user.id,
                guest_name=f"Guest {guest_number}",
                display_name_snapshot=f"{display_name} guest {guest_number}",
                participant_status="confirmed",
                attendance_status="unknown",
                cancellation_type="none",
                price_cents=db_game.price_per_player_cents,
                currency=db_game.currency,
                roster_order=first_roster_order + index,
                joined_at=now,
                confirmed_at=now,
            )
        )

    return guests


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

    if is_roster_locked(db_game, now):
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

    now = datetime.now(timezone.utc)
    require_roster_window_open(db_game, now, "Joining is closed for this game.")

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
    require_roster_window_open(db_game, now, "Attendance changes are closed for this game.")
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
    "/{game_id}/booking-guests/add",
    response_model=GameGuestAddRead,
    status_code=status.HTTP_201_CREATED,
)
def add_booking_game_guests(
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

    if db_game.publish_status != "published" or db_game.game_status not in JOINABLE_GAME_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only published scheduled or full games can add guests.",
        )

    now = datetime.now(timezone.utc)
    require_roster_window_open(db_game, now, "Attendance changes are closed for this game.")

    if guest_request.guest_count <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="guest_count must be greater than 0.",
        )

    participant = get_existing_active_participant(db, db_game.id, acting_user.id)
    if participant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not currently joined to this game.",
        )

    if (
        participant.participant_status != "confirmed"
        or participant.participant_type != "registered_user"
        or participant.booking_id is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only confirmed players can add guests.",
        )

    booking = db.get(Booking, participant.booking_id)
    if booking is None or booking.booking_status not in {"confirmed", "partially_cancelled"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your booking is not eligible for guest changes.",
        )

    booking_participants = get_booking_participants(
        db, db_game.id, booking.id, ACTIVE_JOIN_STATUSES
    )
    current_guest_count = sum(
        booking_participant.participant_type == "guest"
        for booking_participant in booking_participants
    )
    max_guests = db_game.max_guests_per_booking if db_game.allow_guests else 0
    if current_guest_count + guest_request.guest_count > max_guests:
        detail = (
            "This game does not allow guests."
            if max_guests == 0
            else f"This game allows up to {max_guests} guests."
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    roster_count = count_roster_players(db, db_game.id)
    if guest_request.guest_count > max(db_game.total_spots - roster_count, 0):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not enough spots are available for guests.",
        )

    added_guests = build_added_booking_guest_participants(
        db_game,
        booking,
        acting_user,
        get_display_name(acting_user),
        guest_request.guest_count,
        current_guest_count,
        now,
        get_next_roster_order(db, db_game.id),
    )
    booking.participant_count += len(added_guests)
    booking.subtotal_cents = db_game.price_per_player_cents * booking.participant_count
    booking.total_cents = booking.subtotal_cents + booking.platform_fee_cents - booking.discount_cents
    booking.booking_status = "confirmed"
    booking.payment_status = (
        "paid" if game_requires_app_player_payment(db_game) else "not_required"
    )
    booking.updated_at = now
    db_game.updated_at = now

    db.add_all(added_guests)
    db.add(booking)
    if game_requires_app_player_payment(db_game):
        db.add(
            create_booking_guest_add_payment(
                db_game,
                booking,
                acting_user.id,
                len(added_guests),
                now,
            )
        )
    db.flush()
    sync_game_capacity_status(db, db_game)

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
        message="Guests added to your booking.",
        added_count=len(added_guests),
        booking_id=booking.id,
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

    now = datetime.now(timezone.utc)
    require_roster_window_open(db_game, now, "Attendance changes are closed for this game.")

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
    require_roster_window_open(db_game, now, "Attendance changes are closed for this game.")
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


@router.post(
    "/{game_id}/cancel",
    response_model=GameRead,
    status_code=status.HTTP_200_OK,
)
def cancel_game(
    game_id: uuid.UUID,
    cancel_request: GameCancelCreate,
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> Game:
    db_game = db.get(Game, game_id)

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    cancellation_type = require_cancel_permission(db_game, current_user)

    if db_game.publish_status != "published":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only published games can be cancelled.",
        )

    if db_game.game_status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This game is already cancelled.",
        )

    if db_game.game_status not in CANCELLABLE_GAME_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only scheduled or full games can be cancelled.",
        )

    now = datetime.now(timezone.utc)
    require_game_not_started(db_game, now, "Games cannot be cancelled after start time.")
    old_game_status = db_game.game_status
    cancel_reason = normalize_cancel_reason(cancel_request.cancel_reason)
    change_source = "admin" if cancellation_type == "admin_cancelled" else "host"
    notified_user_ids = cancel_game_participants(
        db,
        db_game,
        now,
        cancellation_type,
    )
    if (
        cancellation_type == "admin_cancelled"
        and db_game.game_type == "community"
        and db_game.host_user_id is not None
        and db_game.host_user_id != current_user.id
    ):
        notified_user_ids.append(db_game.host_user_id)
    cancel_game_waitlist_entries(db, db_game, now)
    payment_summary = cancel_game_bookings(
        db, db_game, current_user, now, cancellation_type
    )
    archive_game_chats(db, db_game, now)
    create_game_cancelled_notifications(db, db_game, notified_user_ids, now)
    create_game_cancellation_history(
        db,
        db_game,
        current_user,
        old_game_status,
        cancel_reason,
        change_source,
        now,
    )
    create_game_cancellation_admin_action(
        db,
        db_game,
        current_user,
        cancellation_type,
        old_game_status,
        cancel_reason,
        notified_user_ids,
        payment_summary,
        now,
    )

    db_game.game_status = "cancelled"
    db_game.cancelled_at = now
    db_game.cancelled_by_user_id = current_user.id
    db_game.cancel_reason = cancel_reason
    db_game.completed_at = None
    db_game.completed_by_user_id = None
    db_game.updated_at = now

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

    now = datetime.now(timezone.utc)
    require_game_not_started(db_game, now, "Games cannot be edited after start time.")

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
