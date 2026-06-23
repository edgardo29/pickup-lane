"""Shared game rules and helpers used by routes and services."""

import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    Booking,
    Game,
    GameParticipant,
    Notification,
    Payment,
    Refund,
    User,
    Venue,
    WaitlistEntry,
)
from backend.services.notification_service import (
    build_game_notification_fields,
    reopen_aggregated_notification,
)

VALID_GAME_TYPES = {"official", "community"}
VALID_PAYMENT_COLLECTION_TYPES = {"in_app", "external_host", "none"}
VALID_PUBLISH_STATUSES = {"draft", "published", "archived"}
VALID_GAME_STATUSES = {"scheduled", "full", "cancelled", "completed", "abandoned"}
VALID_ENVIRONMENT_TYPES = {"indoor", "outdoor"}
VALID_GAME_PLAYER_GROUPS = {"men", "women", "coed"}
VALID_SKILL_LEVELS = {
    "any",
    "beginner",
    "recreational",
    "intermediate",
    "advanced",
    "competitive",
}
VALID_POLICY_MODES = {"official_standard", "custom_hosted"}
VALID_CURRENCY = "USD"
HOST_EDITABLE_GAME_STATUSES = {"scheduled", "full"}
CANCELLABLE_GAME_STATUSES = {"scheduled", "full"}
GAME_STATUSES_WITH_DISABLED_INBOX_ACTIONS = {"cancelled", "abandoned"}
ACTIVE_PLAYER_STATUSES = {"pending_payment", "confirmed", "waitlisted"}
RESERVED_PLAYER_STATUSES = {"pending_payment", "confirmed"}
ROSTER_PLAYER_STATUSES = {"pending_payment", "confirmed"}
ACTIVE_JOIN_STATUSES = {"pending_payment", "confirmed", "waitlisted"}
ACTIVE_WAITLIST_STATUSES = {"active", "promoted", "payment_processing"}
WAITLIST_PROMOTION_CANDIDATE_STATUSES = {"active"}
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
AUTO_CHARGE_CONSENT_VERSION_MAX_LENGTH = 50
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
    "game_player_group",
    "skill_level",
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
GAME_UPDATED_GAME_STATUSES = {"scheduled", "full"}
GAME_UPDATED_PARTICIPANT_STATUSES = {"confirmed", "waitlisted"}
GAME_UPDATED_PARTICIPANT_TYPES = {"registered_user", "admin_added"}
GAME_UPDATED_STRUCTURAL_FIELDS = (
    "starts_at",
    "ends_at",
    "venue_id",
    "venue_name_snapshot",
    "address_snapshot",
    "city_snapshot",
    "state_snapshot",
    "neighborhood_snapshot",
    "environment_type",
    "format_label",
    "game_player_group",
    "skill_level",
)


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


def game_requires_app_player_payment(db_game: Game) -> bool:
    return (
        db_game.game_type == "official"
        and db_game.payment_collection_type == "in_app"
    )


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

    if game_data["game_player_group"] not in VALID_GAME_PLAYER_GROUPS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="game_player_group must be 'men', 'women', or 'coed'.",
        )

    if game_data["skill_level"] not in VALID_SKILL_LEVELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "skill_level must be 'any', 'beginner', 'recreational', "
                "'intermediate', 'advanced', or 'competitive'."
            ),
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


def booking_refunded_aggregation_key(game_id: uuid.UUID, booking_id: uuid.UUID) -> str:
    return f"game:{game_id}:booking:{booking_id}:booking_refunded"


def booking_refunded_copy(
    *,
    stripe_refund_processed: bool,
    credit_restored: bool,
    game_cancelled: bool = True,
) -> dict[str, str]:
    if stripe_refund_processed and credit_restored:
        return {
            "title": "Refund and credit processed",
            "summary": "Your refund was processed and your game credit was restored.",
            "body": (
                "Your Stripe refund was processed and your Pickup Lane game credit "
                "was restored "
                + (
                    "for this canceled official game."
                    if game_cancelled
                    else "after your booking was removed from this official game."
                )
            ),
        }

    if credit_restored:
        return {
            "title": "Credit restored",
            "summary": "Your Pickup Lane game credit was restored.",
            "body": (
                "Your Pickup Lane game credit was restored "
                + (
                    "for this canceled official game."
                    if game_cancelled
                    else "after your booking was removed from this official game."
                )
            ),
        }

    return {
        "title": "Refund processed",
        "summary": "Your refund was processed.",
        "body": "Your refund for this official game was processed.",
    }


def game_allows_inbox_action(db_game: Game) -> bool:
    return (
        db_game.deleted_at is None
        and db_game.publish_status == "published"
        and db_game.game_status not in GAME_STATUSES_WITH_DISABLED_INBOX_ACTIONS
    )


def create_or_reopen_booking_refunded_notification(
    db: Session,
    *,
    db_game: Game,
    booking: Booking,
    now: datetime,
    payment: Payment | None = None,
    refund: Refund | None = None,
    stripe_refund_processed: bool,
    credit_restored: bool,
    game_cancelled: bool = True,
    force_action_null: bool = True,
) -> None:
    aggregation_key = booking_refunded_aggregation_key(db_game.id, booking.id)
    copy = booking_refunded_copy(
        stripe_refund_processed=stripe_refund_processed,
        credit_restored=credit_restored,
        game_cancelled=game_cancelled,
    )
    reopen_aggregated_notification(
        db,
        user_id=booking.buyer_user_id,
        notification_type="booking_refunded",
        notification_category="game_activity",
        notification_domain="game",
        aggregation_key=aggregation_key,
        values={
            **build_game_notification_fields(
                db_game,
                "booking_refunded",
                event_at=now,
                force_action_null=force_action_null,
                aggregation_key=aggregation_key,
                **copy,
            ),
            "actor_user_id": None,
            "related_game_id": db_game.id,
            "related_booking_id": booking.id,
            "related_payment_id": payment.id if payment is not None else None,
            "related_refund_id": refund.id if refund is not None else None,
            "related_participant_id": None,
        },
        aggregate_count_mode="clear",
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


def list_public_game_participants(db: Session, game_id: uuid.UUID) -> list[GameParticipant]:
    db_game = db.get(Game, game_id)

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    return list(
        db.scalars(
            select(GameParticipant)
            .where(GameParticipant.game_id == game_id)
            .order_by(
                GameParticipant.roster_order.asc().nulls_last(),
                GameParticipant.created_at.asc(),
            )
        ).all()
    )


def list_public_game_participant_counts(db: Session) -> list[dict[str, object]]:
    rows = db.execute(
        select(
            GameParticipant.game_id,
            func.count(GameParticipant.id).label("participant_count"),
        )
        .where(GameParticipant.participant_status.in_(ROSTER_PLAYER_STATUSES))
        .group_by(GameParticipant.game_id)
    ).all()

    return [
        {"game_id": row.game_id, "participant_count": row.participant_count}
        for row in rows
    ]


def list_current_user_game_participants(
    db: Session,
    current_user: User,
) -> list[GameParticipant]:
    return list(
        db.scalars(
            select(GameParticipant)
            .where(GameParticipant.user_id == current_user.id)
            .order_by(
                GameParticipant.joined_at.desc(),
                GameParticipant.created_at.desc(),
            )
        ).all()
    )


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
    now: datetime,
    payment: Payment | None = None,
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
            notification_category="game_activity",
            notification_domain="game",
            **build_game_notification_fields(
                db_game,
                "waitlist_promoted",
                event_at=now,
                body=body,
            ),
            related_game_id=db_game.id,
            related_booking_id=participant.booking_id,
            related_participant_id=participant.id,
            related_payment_id=payment.id if payment is not None else None,
            is_read=False,
        )
    )


WAITLIST_PAYMENT_FAILED_BODY = (
    "A spot opened, but your payment did not go through, so you were removed "
    "from the waitlist. Update your payment method and try joining again if a "
    "spot is still available."
)


def create_waitlist_payment_failed_notification(
    db: Session,
    db_game: Game,
    booking: Booking,
    payment: Payment | None,
    now: datetime,
) -> None:
    db.add(
        Notification(
            id=uuid.uuid4(),
            user_id=booking.buyer_user_id,
            notification_type="payment_failed",
            notification_category="game_activity",
            notification_domain="game",
            **build_game_notification_fields(
                db_game,
                "payment_failed",
                event_at=now,
                summary="Your waitlist payment did not go through.",
                body=WAITLIST_PAYMENT_FAILED_BODY,
            ),
            related_game_id=db_game.id,
            related_booking_id=booking.id,
            related_payment_id=payment.id if payment is not None else None,
            is_read=False,
            read_at=None,
            created_at=now,
            updated_at=now,
        )
    )
