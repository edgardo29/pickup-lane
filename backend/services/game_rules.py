"""Pure game constants, validation rules, and lifecycle normalization."""

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from backend.models import Game, User
from backend.services.game_participant_rules import (
    ACTIVE_ROSTER_PARTICIPANT_STATUSES,
    OFFICIAL_ROSTER_PARTICIPANT_TYPES,
)
from backend.services.payment_rules import (
    COLLECTED_PAYMENT_STATUSES,
    SUCCEEDED_PAYMENT_STATUSES,
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
OPEN_GAME_STATUSES = {"scheduled", "full"}
HOST_EDITABLE_GAME_STATUSES = OPEN_GAME_STATUSES
CANCELLABLE_GAME_STATUSES = OPEN_GAME_STATUSES
GAME_STATUSES_WITH_DISABLED_INBOX_ACTIONS = {"cancelled", "abandoned"}
ACTIVE_JOIN_STATUSES = {"pending_payment", "confirmed", "waitlisted"}
ACTIVE_PLAYER_STATUSES = ACTIVE_JOIN_STATUSES
RESERVED_PLAYER_STATUSES = ACTIVE_ROSTER_PARTICIPANT_STATUSES
ROSTER_PLAYER_STATUSES = ACTIVE_ROSTER_PARTICIPANT_STATUSES
ACTIVE_WAITLIST_STATUSES = {"active", "promoted", "payment_processing"}
WAITLIST_PROMOTION_CANDIDATE_STATUSES = {"active"}
ACTIVE_BOOKING_STATUSES = {
    "pending_payment",
    "confirmed",
    "waitlisted",
    "partially_cancelled",
}
JOINABLE_GAME_STATUSES = OPEN_GAME_STATUSES
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
CANCELLATION_REFUND_FOLLOWUP_PAYMENT_STATUSES = COLLECTED_PAYMENT_STATUSES
CANCELLATION_UNCHARGED_PENDING_PAYMENT_STATUSES = {
    "requires_payment_method",
    "requires_action",
}
CANCELLATION_AUTO_REFUND_PAYMENT_STATUSES = SUCCEEDED_PAYMENT_STATUSES
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
GAME_UPDATED_GAME_STATUSES = OPEN_GAME_STATUSES
GAME_UPDATED_PARTICIPANT_STATUSES = {"confirmed", "waitlisted"}
GAME_UPDATED_PARTICIPANT_TYPES = OFFICIAL_ROSTER_PARTICIPANT_TYPES
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
