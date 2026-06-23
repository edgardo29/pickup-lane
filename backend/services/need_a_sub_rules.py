"""Rules and constants for Need a Sub workflows."""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status

from backend.models import SubPost

POST_STATUSES = {"active", "filled", "expired", "canceled", "removed"}
REQUEST_STATUSES = {
    "pending",
    "confirmed",
    "declined",
    "sub_waitlist",
    "canceled_by_player",
    "canceled_by_owner",
    "no_show_reported",
    "expired",
}
ACTIVE_VISIBLE_POST_STATUSES = {"active", "filled"}
ACTIVE_REQUEST_STATUSES = {"pending", "confirmed", "sub_waitlist"}
QUEUE_HOLD_REQUEST_STATUSES = {"pending", "confirmed"}
EXPIRABLE_REQUEST_STATUSES = {"pending", "sub_waitlist"}
MAX_WAITLIST_REQUESTS_PER_POST = 25
MAX_SUB_POST_SCHEDULE_DAYS_AHEAD = 14
VALID_FORMAT_LABELS = {
    "3v3",
    "4v4",
    "5v5",
    "6v6",
    "7v7",
    "8v8",
    "9v9",
    "10v10",
    "11v11",
}
VALID_SKILL_LEVELS = {
    "any",
    "beginner",
    "recreational",
    "intermediate",
    "advanced",
    "competitive",
}
VALID_ENVIRONMENT_TYPES = {"indoor", "outdoor"}
VALID_POSITION_LABELS = {"field_player", "goalkeeper"}
TERMINAL_REQUEST_STATUSES = {
    "declined",
    "canceled_by_player",
    "canceled_by_owner",
    "no_show_reported",
    "expired",
}
SUB_POST_UPDATED_RECIPIENT_STATUSES = {"pending", "confirmed", "sub_waitlist"}
SUB_POST_UPDATED_STRUCTURAL_FIELDS = (
    "starts_at",
    "ends_at",
    "location_name",
    "address_line_1",
    "city",
    "state",
    "postal_code",
    "neighborhood",
    "format_label",
    "environment_type",
    "skill_level",
    "game_player_group",
    "price_due_at_venue_cents",
)
POST_STATUS_CHANGE_SOURCES = {"owner", "admin", "system", "scheduled_job"}
VALID_POSITION_GROUPS_BY_POST_GROUP = {
    "men": {"men"},
    "women": {"women"},
    "coed": {"open", "men", "women"},
}
PLAYER_GROUP_DISPLAY_LABELS = {
    "open": "Any",
    "men": "Men's",
    "women": "Women's",
}
POSITION_DISPLAY_LABELS = {
    "field_player": "Field Player",
    "goalkeeper": "Goalkeeper",
}


def ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def now_utc() -> datetime:
    return datetime.now(UTC)


def get_local_date(value: datetime, timezone: str | None) -> date:
    try:
        local_timezone = ZoneInfo(timezone or "UTC")
    except ZoneInfoNotFoundError:
        local_timezone = UTC

    return ensure_aware(value).astimezone(local_timezone).date()


def normalize_post_status_change_source(change_source: str) -> str:
    if change_source in POST_STATUS_CHANGE_SOURCES:
        return change_source

    return "system"


def require_before_post_start(sub_post: SubPost, detail: str) -> None:
    if now_utc() >= ensure_aware(sub_post.starts_at):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )


def require_live_sub_post(sub_post: SubPost, detail: str) -> None:
    if sub_post.post_status not in ACTIVE_VISIBLE_POST_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )
