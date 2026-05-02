from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import Game, Payment, User, Venue

DEV_IDS = {
    "host_user_id": UUID("22222222-2222-4222-8222-222222222222"),
    "admin_user_id": UUID("33333333-3333-4333-8333-333333333333"),
    "venue_id": UUID("44444444-4444-4444-8444-444444444444"),
    "community_game_ready_id": UUID("66666666-6666-4666-8666-666666666666"),
    "host_deposit_payment_ready_id": UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc"),
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


def seed_host_deposit_dev_data() -> dict[str, UUID]:
    now = datetime.now(UTC)
    starts_at = now + timedelta(days=7)
    ends_at = starts_at + timedelta(hours=1)

    with SessionLocal() as db:
        host = upsert_by_id(
            db,
            User,
            DEV_IDS["host_user_id"],
            {
                "auth_user_id": "dev-host",
                "role": "player",
                "email": "dev-host@pickuplane.local",
                "phone": "+15550000002",
                "first_name": "Dev",
                "last_name": "Host",
                "date_of_birth": date(1993, 5, 10),
                "home_city": "Chicago",
                "home_state": "IL",
                "account_status": "active",
                "hosting_status": "eligible",
                "deleted_at": None,
                "updated_at": now,
            },
            lookup_filters={"auth_user_id": "dev-host"},
        )
        admin = upsert_by_id(
            db,
            User,
            DEV_IDS["admin_user_id"],
            {
                "auth_user_id": "dev-admin",
                "role": "admin",
                "email": "dev-admin@pickuplane.local",
                "phone": "+15550000003",
                "first_name": "Dev",
                "last_name": "Admin",
                "date_of_birth": date(1990, 3, 15),
                "home_city": "Chicago",
                "home_state": "IL",
                "account_status": "active",
                "hosting_status": "eligible",
                "deleted_at": None,
                "updated_at": now,
            },
            lookup_filters={"auth_user_id": "dev-admin"},
        )
        db.flush()

        venue = upsert_by_id(
            db,
            Venue,
            DEV_IDS["venue_id"],
            {
                "name": "Dev Pickup Field",
                "address_line_1": "123 Dev Ave",
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

        community_game = upsert_by_id(
            db,
            Game,
            DEV_IDS["community_game_ready_id"],
            {
                "game_type": "community",
                "publish_status": "published",
                "game_status": "scheduled",
                "title": "Dev Community Game Ready For Host Deposit",
                "venue_id": venue.id,
                "venue_name_snapshot": venue.name,
                "address_snapshot": venue.address_line_1,
                "city_snapshot": venue.city,
                "state_snapshot": venue.state,
                "host_user_id": host.id,
                "created_by_user_id": host.id,
                "starts_at": starts_at,
                "ends_at": ends_at,
                "timezone": "America/Chicago",
                "sport_type": "soccer",
                "format_label": "5v5",
                "environment_type": "outdoor",
                "total_spots": 10,
                "price_per_player_cents": 1000,
                "currency": "USD",
                "allow_guests": True,
                "max_guests_per_booking": 2,
                "waitlist_enabled": True,
                "is_chat_enabled": True,
                "policy_mode": "custom_hosted",
                "published_at": now,
                "cancelled_at": None,
                "completed_at": None,
                "deleted_at": None,
                "updated_at": now,
            },
        )
        db.flush()

        host_deposit_payment = upsert_by_id(
            db,
            Payment,
            DEV_IDS["host_deposit_payment_ready_id"],
            {
                "payer_user_id": host.id,
                "booking_id": None,
                "game_id": community_game.id,
                "payment_type": "host_deposit",
                "provider": "stripe",
                "provider_payment_intent_id": "pi_dev_host_deposit_ready",
                "provider_charge_id": "ch_dev_host_deposit_ready",
                "idempotency_key": "dev-host-deposit-payment-ready",
                "amount_cents": 2500,
                "currency": "USD",
                "payment_status": "succeeded",
                "paid_at": now,
                "failure_reason": None,
                "payment_metadata": {"seed": "host_deposit_dev"},
                "updated_at": now,
            },
            lookup_filters={"idempotency_key": "dev-host-deposit-payment-ready"},
        )

        db.commit()

        return {
            "host_user_id": host.id,
            "admin_user_id": admin.id,
            "venue_id": venue.id,
            "community_game_ready_id": community_game.id,
            "host_deposit_payment_ready_id": host_deposit_payment.id,
        }


def main() -> None:
    ids = seed_host_deposit_dev_data()

    print("Host deposit dev data ready.")
    print("")
    print("Use these IDs in Postman:")
    for label, value in ids.items():
        print(f"{label}: {value}")
    print("")
    print("POST /host-deposits body for a paid deposit:")
    print("{")
    print(f'  "game_id": "{ids["community_game_ready_id"]}",')
    print(f'  "host_user_id": "{ids["host_user_id"]}",')
    print('  "required_amount_cents": 2500,')
    print('  "currency": "USD",')
    print('  "deposit_status": "paid",')
    print(f'  "payment_id": "{ids["host_deposit_payment_ready_id"]}"')
    print("}")


if __name__ == "__main__":
    main()
