from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import Game, User, Venue

DEV_IDS = {
    "chat_user_id": UUID("14141414-1414-4141-8141-141414141414"),
    "chat_admin_id": UUID("15151515-1515-4151-8151-151515151515"),
    "chat_venue_id": UUID("16161616-1616-4161-8161-161616161616"),
    "game_chat_ready_game_id": UUID("17171717-1717-4171-8171-171717171717"),
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


def seed_game_chat_scenario() -> dict[str, UUID]:
    now = datetime.now(UTC)
    starts_at = now + timedelta(days=7)
    ends_at = starts_at + timedelta(hours=1)

    with SessionLocal() as db:
        user = upsert_by_id(
            db,
            User,
            DEV_IDS["chat_user_id"],
            {
                "auth_user_id": "dev-chat-user",
                "role": "player",
                "email": "dev-chat-user@pickuplane.local",
                "phone": "+15550000004",
                "first_name": "Dev",
                "last_name": "ChatUser",
                "date_of_birth": date(1995, 1, 1),
                "home_city": "Chicago",
                "home_state": "IL",
                "account_status": "active",
                "hosting_status": "not_eligible",
                "deleted_at": None,
                "updated_at": now,
            },
            lookup_filters={"auth_user_id": "dev-chat-user"},
        )
        admin = upsert_by_id(
            db,
            User,
            DEV_IDS["chat_admin_id"],
            {
                "auth_user_id": "dev-chat-admin",
                "role": "admin",
                "email": "dev-chat-admin@pickuplane.local",
                "phone": "+15550000005",
                "first_name": "Dev",
                "last_name": "ChatAdmin",
                "date_of_birth": date(1990, 3, 15),
                "home_city": "Chicago",
                "home_state": "IL",
                "account_status": "active",
                "hosting_status": "eligible",
                "deleted_at": None,
                "updated_at": now,
            },
            lookup_filters={"auth_user_id": "dev-chat-admin"},
        )
        db.flush()

        venue = upsert_by_id(
            db,
            Venue,
            DEV_IDS["chat_venue_id"],
            {
                "name": "Dev Chat Field",
                "address_line_1": "456 Chat Ave",
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
            DEV_IDS["game_chat_ready_game_id"],
            {
                "game_type": "official",
                "publish_status": "published",
                "game_status": "scheduled",
                "title": "Dev Game Ready For Chat",
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

        db.commit()

        return {
            "chat_user_id": user.id,
            "chat_admin_id": admin.id,
            "chat_venue_id": venue.id,
            "game_chat_ready_game_id": game.id,
        }


def main() -> None:
    ids = seed_game_chat_scenario()

    print("Game chat scenario data ready.")
    print("")
    print("Use these IDs in Postman:")
    for label, value in ids.items():
        print(f"{label}: {value}")
    print("")
    print("POST /game-chats body:")
    print("{")
    print(f'  "game_id": "{ids["game_chat_ready_game_id"]}",')
    print('  "chat_status": "active"')
    print("}")


if __name__ == "__main__":
    main()
