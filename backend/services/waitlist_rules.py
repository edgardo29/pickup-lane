"""Waitlist entry constants, validation, and lifecycle normalization."""

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from backend.models import Game, WaitlistEntry

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


def validate_waitlist_status(value: str) -> None:
    if value not in VALID_WAITLIST_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "waitlist_status must be 'active', 'promoted', 'accepted', "
                "'declined', 'expired', 'cancelled', 'removed', "
                "'payment_processing', or 'payment_failed'."
            ),
        )


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

    validate_waitlist_status(str(waitlist_entry_data["waitlist_status"]))

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
    # declined, expires, or moves through payment processing.
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
