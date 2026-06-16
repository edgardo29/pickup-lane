"""Shared helpers for recording booking and participant status changes."""

import uuid

from sqlalchemy.orm import Session

from backend.models import (
    Booking,
    BookingStatusHistory,
    GameParticipant,
    ParticipantStatusHistory,
)


def add_booking_status_history_if_changed(
    db: Session,
    booking: Booking,
    *,
    old_booking_status: str,
    old_payment_status: str,
    reason: str,
    changed_by_user_id: uuid.UUID | None = None,
    change_source: str = "system",
) -> None:
    if (
        old_booking_status == booking.booking_status
        and old_payment_status == booking.payment_status
    ):
        return

    db.add(
        BookingStatusHistory(
            id=uuid.uuid4(),
            booking_id=booking.id,
            old_booking_status=old_booking_status,
            new_booking_status=booking.booking_status,
            old_payment_status=old_payment_status,
            new_payment_status=booking.payment_status,
            changed_by_user_id=changed_by_user_id,
            change_source=change_source,
            change_reason=reason,
        )
    )


def add_participant_status_history_if_changed(
    db: Session,
    participant: GameParticipant,
    *,
    old_participant_status: str,
    old_attendance_status: str,
    reason: str,
    changed_by_user_id: uuid.UUID | None = None,
    change_source: str = "system",
) -> None:
    if (
        old_participant_status == participant.participant_status
        and old_attendance_status == participant.attendance_status
    ):
        return

    db.add(
        ParticipantStatusHistory(
            id=uuid.uuid4(),
            participant_id=participant.id,
            old_participant_status=old_participant_status,
            new_participant_status=participant.participant_status,
            old_attendance_status=old_attendance_status,
            new_attendance_status=participant.attendance_status,
            changed_by_user_id=changed_by_user_id,
            change_source=change_source,
            change_reason=reason,
        )
    )
