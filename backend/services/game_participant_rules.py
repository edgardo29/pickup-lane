"""Game participant constants, validation, and lifecycle normalization."""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from backend.models import GameParticipant

VALID_PARTICIPANT_TYPES = {"registered_user", "guest", "host", "admin_added"}
ROSTER_USER_PARTICIPANT_TYPES = {"registered_user", "host", "admin_added"}
OFFICIAL_ROSTER_PARTICIPANT_TYPES = {"registered_user", "admin_added"}
ACTIVE_ROSTER_PARTICIPANT_STATUSES = {"pending_payment", "confirmed"}
VALID_PARTICIPANT_STATUSES = {
    "pending_payment",
    "confirmed",
    "waitlisted",
    "cancelled",
    "late_cancelled",
    "removed",
    "refunded",
}
VALID_ATTENDANCE_STATUSES = {
    "unknown",
    "attended",
    "no_show",
    "excused_absence",
    "not_applicable",
}
VALID_CANCELLATION_TYPES = {
    "none",
    "on_time",
    "late",
    "host_cancelled",
    "admin_cancelled",
    "payment_failed",
}
VALID_CURRENCY = "USD"
CANCELLED_PARTICIPANT_STATUSES = {"cancelled", "late_cancelled", "removed", "refunded"}
DECIDED_ATTENDANCE_STATUSES = {"attended", "no_show", "excused_absence"}
CONFIRMED_HISTORY_PARTICIPANT_STATUSES = {"confirmed"} | CANCELLED_PARTICIPANT_STATUSES


def build_game_participant_conflict_detail(exc: IntegrityError) -> str:
    error_text = str(exc.orig)

    if "ux_game_participants_active_registered_user_per_game" in error_text:
        return "This user already has an active participant row for this game."

    return error_text


def validate_game_participant_status(value: str) -> None:
    if value not in VALID_PARTICIPANT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "participant_status must be 'pending_payment', 'confirmed', "
                "'waitlisted', 'cancelled', 'late_cancelled', 'removed', "
                "or 'refunded'."
            ),
        )


def validate_game_participant_attendance_status(value: str) -> None:
    if value not in VALID_ATTENDANCE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "attendance_status must be 'unknown', 'attended', "
                "'no_show', 'excused_absence', or 'not_applicable'."
            ),
        )


def validate_game_participant_business_rules(
    participant_data: dict[str, object],
) -> None:
    if participant_data["participant_type"] not in VALID_PARTICIPANT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "participant_type must be 'registered_user', 'guest', "
                "'host', or 'admin_added'."
            ),
        )

    validate_game_participant_status(str(participant_data["participant_status"]))
    validate_game_participant_attendance_status(str(participant_data["attendance_status"]))

    if participant_data["cancellation_type"] not in VALID_CANCELLATION_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "cancellation_type must be 'none', 'on_time', 'late', "
                "'host_cancelled', 'admin_cancelled', or 'payment_failed'."
            ),
        )

    if participant_data["currency"] != VALID_CURRENCY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="currency must be 'USD'.",
        )

    if participant_data["price_cents"] < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="price_cents must be greater than or equal to 0.",
        )

    if (
        participant_data["roster_order"] is not None
        and participant_data["roster_order"] <= 0
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="roster_order must be null or greater than 0.",
        )

    if (
        participant_data["participant_type"] == "guest"
        and participant_data["guest_name"] is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Guest participants require guest_name.",
        )

    if (
        participant_data["participant_type"] == "guest"
        and participant_data["user_id"] is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Guest participants cannot include user_id.",
        )

    if (
        participant_data["participant_type"] in {"registered_user", "host", "admin_added"}
        and participant_data["user_id"] is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registered_user, host, and admin_added participants require user_id.",
        )

    if (
        participant_data["participant_type"] != "guest"
        and any(
            participant_data[field_name] is not None
            for field_name in ("guest_name", "guest_email", "guest_phone")
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Only guest participants may include guest_name, guest_email, "
                "or guest_phone."
            ),
        )

    if (
        participant_data["participant_status"] in CANCELLED_PARTICIPANT_STATUSES
        and participant_data["cancellation_type"] == "none"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Cancelled, late_cancelled, removed, and refunded participants "
                "require a non-'none' cancellation_type."
            ),
        )

    if (
        participant_data["participant_status"] not in CANCELLED_PARTICIPANT_STATUSES
        and participant_data["cancellation_type"] != "none"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Only cancelled, late_cancelled, removed, and refunded "
                "participants may use a non-'none' cancellation_type."
            ),
        )

    if (
        participant_data["attendance_status"] in DECIDED_ATTENDANCE_STATUSES
        and participant_data["marked_attendance_by_user_id"] is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Attended, no_show, and excused_absence participants require "
                "marked_attendance_by_user_id."
            ),
        )

    if (
        participant_data["checked_in_at"] is not None
        and participant_data["attendance_status"] != "attended"
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="checked_in_at can only be set when attendance_status is 'attended'.",
        )


def normalize_game_participant_lifecycle_fields(
    participant_data: dict[str, object],
    existing_participant: GameParticipant | None = None,
) -> dict[str, object]:
    normalized_data = dict(participant_data)
    now = datetime.now(timezone.utc)

    normalized_data["joined_at"] = (
        normalized_data.get("joined_at")
        or (existing_participant.joined_at if existing_participant is not None else None)
        or now
    )

    # Preserve the original confirmed_at timestamp for participants who were
    # once confirmed, even if they later cancel or get refunded.
    if normalized_data["participant_status"] in CONFIRMED_HISTORY_PARTICIPANT_STATUSES:
        normalized_data["confirmed_at"] = (
            normalized_data.get("confirmed_at")
            or (
                existing_participant.confirmed_at
                if existing_participant is not None
                else None
            )
            or now
        )
    else:
        normalized_data["confirmed_at"] = None

    if normalized_data["participant_status"] in CANCELLED_PARTICIPANT_STATUSES:
        normalized_data["cancelled_at"] = (
            normalized_data.get("cancelled_at")
            or (
                existing_participant.cancelled_at
                if existing_participant is not None
                else None
            )
            or now
        )
    else:
        normalized_data["cancelled_at"] = None

    if normalized_data["attendance_status"] in DECIDED_ATTENDANCE_STATUSES:
        normalized_data["attendance_decided_at"] = (
            normalized_data.get("attendance_decided_at")
            or (
                existing_participant.attendance_decided_at
                if existing_participant is not None
                else None
            )
            or now
        )
    else:
        normalized_data["attendance_decided_at"] = None
        normalized_data["marked_attendance_by_user_id"] = None
        normalized_data["attendance_notes"] = None

    return normalized_data
