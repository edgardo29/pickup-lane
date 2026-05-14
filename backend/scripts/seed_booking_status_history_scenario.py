from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import Booking, Game, User, Venue

DEV_IDS = {
    "booking_history_user_id": UUID("35353535-3535-4353-8353-353535353535"),
    "booking_history_admin_id": UUID("36363636-3636-4363-8363-363636363636"),
    "booking_history_venue_id": UUID("37373737-3737-4373-8373-373737373737"),
    "booking_history_game_id": UUID("38383838-3838-4383-8383-383838383838"),
    "booking_history_booking_id": UUID("39393939-3939-4393-8393-393939393939"),
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


def seed_booking_status_history_scenario() -> dict[str, UUID]:
    now = datetime.now(UTC)
    starts_at = now + timedelta(days=7)
    ends_at = starts_at + timedelta(hours=1)

    with SessionLocal() as db:
        user = upsert_by_id(
            db,
            User,
            DEV_IDS["booking_history_user_id"],
            {
                "auth_user_id": "dev-booking-history-user",
                "role": "player",
                "email": "dev-booking-history-user@pickuplane.local",
                "phone": "+15550000011",
                "first_name": "Dev",
                "last_name": "BookingHistoryUser",
                "date_of_birth": date(1995, 1, 1),
                "home_city": "Chicago",
                "home_state": "IL",
                "account_status": "active",
                "hosting_status": "not_eligible",
                "deleted_at": None,
                "updated_at": now,
            },
            lookup_filters={"auth_user_id": "dev-booking-history-user"},
        )
        admin = upsert_by_id(
            db,
            User,
            DEV_IDS["booking_history_admin_id"],
            {
                "auth_user_id": "dev-booking-history-admin",
                "role": "admin",
                "email": "dev-booking-history-admin@pickuplane.local",
                "phone": "+15550000012",
                "first_name": "Dev",
                "last_name": "BookingHistoryAdmin",
                "date_of_birth": date(1990, 3, 15),
                "home_city": "Chicago",
                "home_state": "IL",
                "account_status": "active",
                "hosting_status": "eligible",
                "deleted_at": None,
                "updated_at": now,
            },
            lookup_filters={"auth_user_id": "dev-booking-history-admin"},
        )
        db.flush()

        venue = upsert_by_id(
            db,
            Venue,
            DEV_IDS["booking_history_venue_id"],
            {
                "name": "Dev Booking History Field",
                "address_line_1": "987 Booking History Ave",
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
            DEV_IDS["booking_history_game_id"],
            {
                "game_type": "official",
                "payment_collection_type": "in_app",
                "publish_status": "published",
                "game_status": "scheduled",
                "title": "Dev Game Ready For Booking History",
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
            DEV_IDS["booking_history_booking_id"],
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

        db.commit()

        return {
            "booking_history_user_id": user.id,
            "booking_history_admin_id": admin.id,
            "booking_history_venue_id": venue.id,
            "booking_history_game_id": game.id,
            "booking_history_booking_id": booking.id,
        }


def main() -> None:
    ids = seed_booking_status_history_scenario()

    print("Booking status history scenario data ready.")
    print("")
    print("Use these IDs in Postman:")
    for label, value in ids.items():
        print(f"{label}: {value}")
    print("")
    print("POST /booking-status-history body:")
    print("{")
    print(f'  "booking_id": "{ids["booking_history_booking_id"]}",')
    print('  "old_booking_status": "pending_payment",')
    print('  "new_booking_status": "confirmed",')
    print('  "old_payment_status": "processing",')
    print('  "new_payment_status": "paid",')
    print(f'  "changed_by_user_id": "{ids["booking_history_admin_id"]}",')
    print('  "change_source": "payment_webhook",')
    print('  "change_reason": "Payment succeeded and booking was confirmed."')
    print("}")


if __name__ == "__main__":
    main()
