from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import Game, HostDeposit, Payment, User, Venue

DEV_IDS = {
    "host_deposit_event_host_user_id": UUID("81818181-8181-4818-8818-818181818181"),
    "host_deposit_event_admin_id": UUID("82828282-8282-4828-8828-828282828282"),
    "host_deposit_event_venue_id": UUID("83838383-8383-4838-8838-838383838383"),
    "host_deposit_event_game_id": UUID("84848484-8484-4848-8848-848484848484"),
    "host_deposit_event_payment_id": UUID("85858585-8585-4858-8858-858585858585"),
    "host_deposit_event_host_deposit_id": UUID("86868686-8686-4868-8868-868686868686"),
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


def seed_host_deposit_event_scenario() -> dict[str, UUID]:
    now = datetime.now(UTC)
    starts_at = now + timedelta(days=7)
    ends_at = starts_at + timedelta(hours=1)

    with SessionLocal() as db:
        host = upsert_by_id(
            db,
            User,
            DEV_IDS["host_deposit_event_host_user_id"],
            {
                "auth_user_id": "dev-host-deposit-event-host",
                "role": "player",
                "email": "dev-host-deposit-event-host@pickuplane.local",
                "phone": "+15550000061",
                "first_name": "Dev",
                "last_name": "HostDepositEventHost",
                "date_of_birth": date(1993, 5, 10),
                "home_city": "Chicago",
                "home_state": "IL",
                "account_status": "active",
                "hosting_status": "eligible",
                "deleted_at": None,
                "updated_at": now,
            },
            lookup_filters={"auth_user_id": "dev-host-deposit-event-host"},
        )
        admin = upsert_by_id(
            db,
            User,
            DEV_IDS["host_deposit_event_admin_id"],
            {
                "auth_user_id": "dev-host-deposit-event-admin",
                "role": "admin",
                "email": "dev-host-deposit-event-admin@pickuplane.local",
                "phone": "+15550000062",
                "first_name": "Dev",
                "last_name": "HostDepositEventAdmin",
                "date_of_birth": date(1990, 3, 15),
                "home_city": "Chicago",
                "home_state": "IL",
                "account_status": "active",
                "hosting_status": "eligible",
                "deleted_at": None,
                "updated_at": now,
            },
            lookup_filters={"auth_user_id": "dev-host-deposit-event-admin"},
        )
        db.flush()

        venue = upsert_by_id(
            db,
            Venue,
            DEV_IDS["host_deposit_event_venue_id"],
            {
                "name": "Dev Host Deposit Event Field",
                "address_line_1": "616 Event Ave",
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
            DEV_IDS["host_deposit_event_game_id"],
            {
                "game_type": "community",
                "publish_status": "published",
                "game_status": "scheduled",
                "title": "Dev Game Ready For Host Deposit Events",
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

        payment = upsert_by_id(
            db,
            Payment,
            DEV_IDS["host_deposit_event_payment_id"],
            {
                "payer_user_id": host.id,
                "booking_id": None,
                "game_id": game.id,
                "payment_type": "host_deposit",
                "provider": "stripe",
                "provider_payment_intent_id": "pi_dev_host_deposit_event",
                "provider_charge_id": "ch_dev_host_deposit_event",
                "idempotency_key": "dev-host-deposit-event-payment",
                "amount_cents": 2500,
                "currency": "USD",
                "payment_status": "succeeded",
                "paid_at": now,
                "failure_reason": None,
                "payment_metadata": {"source": "host_deposit_event_seed"},
                "updated_at": now,
            },
            lookup_filters={"idempotency_key": "dev-host-deposit-event-payment"},
        )
        db.flush()

        host_deposit = upsert_by_id(
            db,
            HostDeposit,
            DEV_IDS["host_deposit_event_host_deposit_id"],
            {
                "game_id": game.id,
                "host_user_id": host.id,
                "required_amount_cents": 2500,
                "currency": "USD",
                "deposit_status": "paid",
                "payment_id": payment.id,
                "refund_id": None,
                "paid_at": now,
                "released_at": None,
                "forfeited_at": None,
                "refunded_at": None,
                "decision_by_user_id": None,
                "decision_reason": None,
                "updated_at": now,
            },
            lookup_filters={"game_id": game.id},
        )

        db.commit()

        return {
            "host_deposit_event_host_user_id": host.id,
            "host_deposit_event_admin_id": admin.id,
            "host_deposit_event_venue_id": venue.id,
            "host_deposit_event_game_id": game.id,
            "host_deposit_event_payment_id": payment.id,
            "host_deposit_event_host_deposit_id": host_deposit.id,
        }


def main() -> None:
    ids = seed_host_deposit_event_scenario()

    print("Host deposit event scenario data ready.")
    print("")
    print("Use these IDs in Postman:")
    for label, value in ids.items():
        print(f"{label}: {value}")
    print("")
    print("POST /host-deposit-events body:")
    print("{")
    print(f'  "host_deposit_id": "{ids["host_deposit_event_host_deposit_id"]}",')
    print('  "old_status": "payment_pending",')
    print('  "new_status": "paid",')
    print(f'  "changed_by_user_id": "{ids["host_deposit_event_admin_id"]}",')
    print('  "change_source": "admin",')
    print('  "reason": "Confirmed host deposit payment for testing."')
    print("}")


if __name__ == "__main__":
    main()
