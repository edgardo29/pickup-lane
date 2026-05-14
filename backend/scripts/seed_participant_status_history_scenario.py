from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import Booking, Game, GameParticipant, User, Venue

DEV_IDS = {
    "participant_history_user_id": UUID("41414141-4141-4441-8441-414141414141"),
    "participant_history_admin_id": UUID("42424242-4242-4442-8442-424242424242"),
    "participant_history_venue_id": UUID("43434343-4343-4443-8443-434343434343"),
    "participant_history_game_id": UUID("44444444-4444-4444-8444-444444444444"),
    "participant_history_booking_id": UUID("45454545-4545-4445-8445-454545454545"),
    "participant_history_participant_id": UUID(
        "46464646-4646-4446-8446-464646464646"
    ),
}


def upsert_by_id(
    db: Session,
    model: type,
    record_id: UUID,
    values: dict[str, Any],
    lookup_filters: dict[str, Any] | None = None,
) -> Any:
    record = db.get(model, record_id)

    if record is None and lookup_filters:
        statement = select(model)
        for field_name, field_value in lookup_filters.items():
            statement = statement.where(getattr(model, field_name) == field_value)
        record = db.scalars(statement).first()

    if record is None:
        record = model(id=record_id)
        db.add(record)

    for field_name, field_value in values.items():
        setattr(record, field_name, field_value)

    return record


def seed_participant_status_history_scenario() -> dict[str, UUID]:
    now = datetime.now(UTC)
    starts_at = now + timedelta(days=7)
    ends_at = starts_at + timedelta(hours=1)

    with SessionLocal() as db:
        user = upsert_by_id(
            db,
            User,
            DEV_IDS["participant_history_user_id"],
            {
                "auth_user_id": "dev-participant-history-user",
                "role": "player",
                "email": "dev-participant-history-user@pickuplane.local",
                "phone": "+15550000021",
                "first_name": "Dev",
                "last_name": "ParticipantHistoryUser",
                "date_of_birth": date(1995, 1, 1),
                "home_city": "Chicago",
                "home_state": "IL",
                "account_status": "active",
                "hosting_status": "not_eligible",
                "deleted_at": None,
                "updated_at": now,
            },
            lookup_filters={"auth_user_id": "dev-participant-history-user"},
        )
        admin = upsert_by_id(
            db,
            User,
            DEV_IDS["participant_history_admin_id"],
            {
                "auth_user_id": "dev-participant-history-admin",
                "role": "admin",
                "email": "dev-participant-history-admin@pickuplane.local",
                "phone": "+15550000022",
                "first_name": "Dev",
                "last_name": "ParticipantHistoryAdmin",
                "date_of_birth": date(1990, 3, 15),
                "home_city": "Chicago",
                "home_state": "IL",
                "account_status": "active",
                "hosting_status": "eligible",
                "deleted_at": None,
                "updated_at": now,
            },
            lookup_filters={"auth_user_id": "dev-participant-history-admin"},
        )
        db.flush()

        venue = upsert_by_id(
            db,
            Venue,
            DEV_IDS["participant_history_venue_id"],
            {
                "name": "Dev Participant History Field",
                "address_line_1": "321 Participant History Ave",
                "city": "Chicago",
                "state": "IL",
                "postal_code": "60601",
                "country_code": "US",
                "venue_status": "approved",
                "created_by_user_id": admin.id,
                "approved_by_user_id": admin.id,
                "approved_at": now,
                "is_active": True,
                "deleted_at": None,
                "updated_at": now,
            },
        )
        db.flush()

        game = upsert_by_id(
            db,
            Game,
            DEV_IDS["participant_history_game_id"],
            {
                "game_type": "official",
                "payment_collection_type": "in_app",
                "publish_status": "published",
                "game_status": "scheduled",
                "title": "Dev Game Ready For Participant History",
                "venue_id": venue.id,
                "venue_name_snapshot": venue.name,
                "address_snapshot": venue.address_line_1,
                "city_snapshot": venue.city,
                "state_snapshot": venue.state,
                "host_user_id": None,
                "created_by_user_id": admin.id,
                "starts_at": starts_at,
                "ends_at": ends_at,
                "timezone": "America/Chicago",
                "sport_type": "soccer",
                "format_label": "5v5",
                "environment_type": "indoor",
                "total_spots": 10,
                "price_per_player_cents": 1200,
                "currency": "USD",
                "allow_guests": True,
                "max_guests_per_booking": 2,
                "waitlist_enabled": True,
                "is_chat_enabled": True,
                "policy_mode": "official_standard",
                "published_at": now,
                "cancelled_at": None,
                "completed_at": None,
                "deleted_at": None,
                "updated_at": now,
            },
        )
        db.flush()

        booking = upsert_by_id(
            db,
            Booking,
            DEV_IDS["participant_history_booking_id"],
            {
                "game_id": game.id,
                "buyer_user_id": user.id,
                "booking_status": "confirmed",
                "payment_status": "paid",
                "participant_count": 1,
                "subtotal_cents": 1200,
                "platform_fee_cents": 100,
                "discount_cents": 0,
                "total_cents": 1300,
                "currency": "USD",
                "price_per_player_snapshot_cents": 1200,
                "platform_fee_snapshot_cents": 100,
                "booked_at": now,
                "cancelled_at": None,
                "cancelled_by_user_id": None,
                "cancel_reason": None,
                "expires_at": None,
                "updated_at": now,
            },
        )
        db.flush()

        participant = upsert_by_id(
            db,
            GameParticipant,
            DEV_IDS["participant_history_participant_id"],
            {
                "game_id": game.id,
                "booking_id": booking.id,
                "participant_type": "registered_user",
                "user_id": user.id,
                "guest_name": None,
                "guest_email": None,
                "guest_phone": None,
                "display_name_snapshot": "Dev Participant History User",
                "participant_status": "confirmed",
                "attendance_status": "unknown",
                "cancellation_type": "none",
                "price_cents": 1200,
                "currency": "USD",
                "roster_order": 1,
                "joined_at": now,
                "confirmed_at": now,
                "cancelled_at": None,
                "checked_in_at": None,
                "marked_attendance_by_user_id": None,
                "attendance_decided_at": None,
                "attendance_notes": None,
                "updated_at": now,
            },
        )

        db.commit()

        return {
            "participant_history_user_id": user.id,
            "participant_history_admin_id": admin.id,
            "participant_history_venue_id": venue.id,
            "participant_history_game_id": game.id,
            "participant_history_booking_id": booking.id,
            "participant_history_participant_id": participant.id,
        }


def main() -> None:
    ids = seed_participant_status_history_scenario()

    print("Participant status history scenario data ready.")
    print("")
    print("Use these IDs in Postman:")
    for label, value in ids.items():
        print(f"{label}: {value}")
    print("")
    print("POST /participant-status-history body:")
    print("{")
    print(f'  "participant_id": "{ids["participant_history_participant_id"]}",')
    print('  "old_participant_status": "pending_payment",')
    print('  "new_participant_status": "confirmed",')
    print('  "old_attendance_status": "unknown",')
    print('  "new_attendance_status": "attended",')
    print(f'  "changed_by_user_id": "{ids["participant_history_admin_id"]}",')
    print('  "change_source": "admin",')
    print('  "change_reason": "Participant confirmed and marked attended."')
    print("}")


if __name__ == "__main__":
    main()