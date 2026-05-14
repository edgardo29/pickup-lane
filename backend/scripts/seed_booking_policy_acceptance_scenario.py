from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import Booking, Game, PolicyDocument, User, Venue

DEV_IDS = {
    "booking_policy_acceptance_user_id": UUID(
        "84848484-8484-4884-8884-848484848484"
    ),
    "booking_policy_acceptance_admin_id": UUID(
        "85858585-8585-4885-8885-858585858585"
    ),
    "booking_policy_acceptance_venue_id": UUID(
        "86868686-8686-4886-8886-868686868686"
    ),
    "booking_policy_acceptance_game_id": UUID(
        "87878787-8787-4887-8887-878787878787"
    ),
    "booking_policy_acceptance_booking_id": UUID(
        "88888888-8888-4888-8888-888888888888"
    ),
    "booking_policy_acceptance_document_id": UUID(
        "89898989-8989-4889-8889-898989898989"
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


def seed_booking_policy_acceptance_scenario() -> dict[str, UUID]:
    now = datetime.now(UTC)
    starts_at = now + timedelta(days=7)
    ends_at = starts_at + timedelta(hours=1)

    with SessionLocal() as db:
        user = upsert_by_id(
            db,
            User,
            DEV_IDS["booking_policy_acceptance_user_id"],
            {
                "auth_user_id": "dev-booking-policy-acceptance-user",
                "role": "player",
                "email": "dev-booking-policy-acceptance-user@pickuplane.local",
                "phone": "+15550000071",
                "first_name": "Dev",
                "last_name": "BookingPolicyAcceptanceUser",
                "date_of_birth": date(1995, 1, 1),
                "home_city": "Chicago",
                "home_state": "IL",
                "account_status": "active",
                "hosting_status": "not_eligible",
                "deleted_at": None,
                "updated_at": now,
            },
            lookup_filters={"phone": "+15550000071"},
        )

        admin = upsert_by_id(
            db,
            User,
            DEV_IDS["booking_policy_acceptance_admin_id"],
            {
                "auth_user_id": "dev-booking-policy-acceptance-admin",
                "role": "admin",
                "email": "dev-booking-policy-acceptance-admin@pickuplane.local",
                "phone": "+15550000072",
                "first_name": "Dev",
                "last_name": "BookingPolicyAcceptanceAdmin",
                "date_of_birth": date(1990, 1, 1),
                "home_city": "Chicago",
                "home_state": "IL",
                "account_status": "active",
                "hosting_status": "eligible",
                "deleted_at": None,
                "updated_at": now,
            },
            lookup_filters={"phone": "+15550000072"},
        )
        db.flush()

        venue = upsert_by_id(
            db,
            Venue,
            DEV_IDS["booking_policy_acceptance_venue_id"],
            {
                "name": "Dev Booking Policy Acceptance Field",
                "address_line_1": "777 Booking Policy Ave",
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
            DEV_IDS["booking_policy_acceptance_game_id"],
            {
                "game_type": "official",
                "payment_collection_type": "in_app",
                "publish_status": "published",
                "game_status": "scheduled",
                "title": "Dev Game Ready For Booking Policy Acceptance",
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
            DEV_IDS["booking_policy_acceptance_booking_id"],
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

        policy_document = upsert_by_id(
            db,
            PolicyDocument,
            DEV_IDS["booking_policy_acceptance_document_id"],
            {
                "policy_type": "refund_policy",
                "version": "v1.1",
                "title": "Pickup Lane Refund Policy for Booking Acceptance Test",
                "content_url": None,
                "content_text": "These are test refund policy terms for booking acceptance.",
                "effective_at": now,
                "retired_at": None,
                "is_active": True,
                "updated_at": now,
            },
            lookup_filters={
                "policy_type": "refund_policy",
                "version": "v1.1",
            },
        )

        db.commit()

        return {
            "booking_policy_acceptance_user_id": user.id,
            "booking_policy_acceptance_admin_id": admin.id,
            "booking_policy_acceptance_venue_id": venue.id,
            "booking_policy_acceptance_game_id": game.id,
            "booking_policy_acceptance_booking_id": booking.id,
            "booking_policy_acceptance_document_id": policy_document.id,
        }


def main() -> None:
    ids = seed_booking_policy_acceptance_scenario()

    print("Booking policy acceptance scenario data ready.")
    print("")
    print("Use these IDs in Postman:")
    for label, value in ids.items():
        print(f"{label}: {value}")
    print("")
    print("POST /booking-policy-acceptances body:")
    print("{")
    print(
        '  "booking_id": '
        f'"{ids["booking_policy_acceptance_booking_id"]}",'
    )
    print(
        '  "policy_document_id": '
        f'"{ids["booking_policy_acceptance_document_id"]}"'
    )
    print("}")


if __name__ == "__main__":
    main()