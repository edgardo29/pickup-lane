from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import Game, GameChat, User, Venue

DEV_IDS = {
    "message_sender_user_id": UUID("18181818-1818-4181-8181-181818181818"),
    "message_admin_user_id": UUID("19191919-1919-4191-8191-191919191919"),
    "message_venue_id": UUID("20202020-2020-4202-8202-202020202020"),
    "chat_message_ready_game_id": UUID("21212121-2121-4212-8212-212121212121"),
    "chat_message_ready_chat_id": UUID("23232323-2323-4232-8232-232323232323"),
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


def seed_chat_message_scenario() -> dict[str, UUID]:
    now = datetime.now(UTC)
    starts_at = now + timedelta(days=7)
    ends_at = starts_at + timedelta(hours=1)

    with SessionLocal() as db:
        sender = upsert_by_id(
            db,
            User,
            DEV_IDS["message_sender_user_id"],
            {
                "auth_user_id": "dev-message-sender",
                "role": "player",
                "email": "dev-message-sender@pickuplane.local",
                "phone": "+15550000006",
                "first_name": "Dev",
                "last_name": "MessageSender",
                "date_of_birth": date(1995, 1, 1),
                "home_city": "Chicago",
                "home_state": "IL",
                "account_status": "active",
                "hosting_status": "not_eligible",
                "deleted_at": None,
                "updated_at": now,
            },
            lookup_filters={"auth_user_id": "dev-message-sender"},
        )
        admin = upsert_by_id(
            db,
            User,
            DEV_IDS["message_admin_user_id"],
            {
                "auth_user_id": "dev-message-admin",
                "role": "admin",
                "email": "dev-message-admin@pickuplane.local",
                "phone": "+15550000007",
                "first_name": "Dev",
                "last_name": "MessageAdmin",
                "date_of_birth": date(1990, 3, 15),
                "home_city": "Chicago",
                "home_state": "IL",
                "account_status": "active",
                "hosting_status": "eligible",
                "deleted_at": None,
                "updated_at": now,
            },
            lookup_filters={"auth_user_id": "dev-message-admin"},
        )
        db.flush()

        venue = upsert_by_id(
            db,
            Venue,
            DEV_IDS["message_venue_id"],
            {
                "name": "Dev Message Field",
                "address_line_1": "789 Message Ave",
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
            DEV_IDS["chat_message_ready_game_id"],
            {
                "game_type": "official",
                "payment_collection_type": "in_app",
                "publish_status": "published",
                "game_status": "scheduled",
                "title": "Dev Game Ready For Chat Messages",
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

        game_chat = upsert_by_id(
            db,
            GameChat,
            DEV_IDS["chat_message_ready_chat_id"],
            {
                "game_id": game.id,
                "chat_status": "active",
                "locked_at": None,
                "updated_at": now,
            },
        )

        db.commit()

        return {
            "message_sender_user_id": sender.id,
            "message_admin_user_id": admin.id,
            "message_venue_id": venue.id,
            "chat_message_ready_game_id": game.id,
            "chat_message_ready_chat_id": game_chat.id,
        }


def main() -> None:
    ids = seed_chat_message_scenario()

    print("Chat message scenario data ready.")
    print("")
    print("Use these IDs in Postman:")
    for label, value in ids.items():
        print(f"{label}: {value}")
    print("")
    print("POST /chat-messages body:")
    print("{")
    print(f'  "chat_id": "{ids["chat_message_ready_chat_id"]}",')
    print(f'  "sender_user_id": "{ids["message_sender_user_id"]}",')
    print('  "message_type": "text",')
    print('  "message_body": "See you all at the field.",')
    print('  "is_pinned": false,')
    print('  "moderation_status": "visible"')
    print("}")


if __name__ == "__main__":
    main()
