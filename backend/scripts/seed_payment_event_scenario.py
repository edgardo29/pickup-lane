from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import Booking, Game, Payment, User, Venue

DEV_IDS = {
    "payment_event_user_id": UUID("71717171-7171-4771-8771-717171717171"),
    "payment_event_admin_id": UUID("72727272-7272-4772-8772-727272727272"),
    "payment_event_venue_id": UUID("73737373-7373-4773-8773-737373737373"),
    "payment_event_game_id": UUID("74747474-7474-4774-8774-747474747474"),
    "payment_event_booking_id": UUID("75757575-7575-4775-8775-757575757575"),
    "payment_event_payment_id": UUID("76767676-7676-4776-8776-767676767676"),
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


def seed_payment_event_scenario() -> dict[str, UUID]:
    now = datetime.now(UTC)
    starts_at = now + timedelta(days=7)
    ends_at = starts_at + timedelta(hours=1)

    with SessionLocal() as db:
        user = upsert_by_id(
            db,
            User,
            DEV_IDS["payment_event_user_id"],
            {
                "auth_user_id": "dev-payment-event-user",
                "role": "player",
                "email": "dev-payment-event-user@pickuplane.local",
                "phone": "+15550000051",
                "first_name": "Dev",
                "last_name": "PaymentEventUser",
                "date_of_birth": date(1995, 1, 1),
                "home_city": "Chicago",
                "home_state": "IL",
                "account_status": "active",
                "hosting_status": "not_eligible",
                "deleted_at": None,
                "updated_at": now,
            },
            lookup_filters={"auth_user_id": "dev-payment-event-user"},
        )
        admin = upsert_by_id(
            db,
            User,
            DEV_IDS["payment_event_admin_id"],
            {
                "auth_user_id": "dev-payment-event-admin",
                "role": "admin",
                "email": "dev-payment-event-admin@pickuplane.local",
                "phone": "+15550000052",
                "first_name": "Dev",
                "last_name": "PaymentEventAdmin",
                "date_of_birth": date(1990, 1, 1),
                "home_city": "Chicago",
                "home_state": "IL",
                "account_status": "active",
                "hosting_status": "eligible",
                "deleted_at": None,
                "updated_at": now,
            },
            lookup_filters={"auth_user_id": "dev-payment-event-admin"},
        )
        db.flush()

        venue = upsert_by_id(
            db,
            Venue,
            DEV_IDS["payment_event_venue_id"],
            {
                "name": "Dev Payment Event Field",
                "address_line_1": "555 Payment Event Ave",
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
            DEV_IDS["payment_event_game_id"],
            {
                "game_type": "official",
                "publish_status": "published",
                "game_status": "scheduled",
                "title": "Dev Game Ready For Payment Events",
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
            DEV_IDS["payment_event_booking_id"],
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

        payment = upsert_by_id(
            db,
            Payment,
            DEV_IDS["payment_event_payment_id"],
            {
                "payer_user_id": user.id,
                "booking_id": booking.id,
                "game_id": game.id,
                "payment_type": "booking",
                "provider": "stripe",
                "provider_payment_intent_id": "pi_dev_payment_event",
                "provider_charge_id": None,
                "idempotency_key": "dev-payment-event-idempotency-key",
                "amount_cents": 1300,
                "currency": "USD",
                "payment_status": "processing",
                "paid_at": None,
                "failure_reason": None,
                "metadata": {"source": "payment_event_seed"},
                "updated_at": now,
            },
            lookup_filters={"idempotency_key": "dev-payment-event-idempotency-key"},
        )

        db.commit()

        return {
            "payment_event_user_id": user.id,
            "payment_event_admin_id": admin.id,
            "payment_event_venue_id": venue.id,
            "payment_event_game_id": game.id,
            "payment_event_booking_id": booking.id,
            "payment_event_payment_id": payment.id,
        }


def main() -> None:
    ids = seed_payment_event_scenario()

    print("Payment event scenario data ready.")
    print("")
    print("Use these IDs in Postman:")
    for label, value in ids.items():
        print(f"{label}: {value}")
    print("")
    print("POST /payment-events body:")
    print("{")
    print(f'  "payment_id": "{ids["payment_event_payment_id"]}",')
    print('  "provider": "stripe",')
    print('  "provider_event_id": "evt_dev_payment_event_001",')
    print('  "event_type": "payment_intent.succeeded",')
    print('  "raw_payload": {')
    print('    "id": "evt_dev_payment_event_001",')
    print('    "type": "payment_intent.succeeded",')
    print('    "data": {')
    print('      "object": {')
    print('        "id": "pi_dev_payment_event"')
    print("      }")
    print("    }")
    print("  },")
    print('  "processing_status": "pending"')
    print("}")


if __name__ == "__main__":
    main()