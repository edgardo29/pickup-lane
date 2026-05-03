from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import Game, User, Venue

DEV_IDS = {
    "status_history_admin_id": UUID("32323232-3232-4323-8323-323232323232"),
    "status_history_venue_id": UUID("33333333-3333-4333-8333-333333333333"),
    "status_history_game_id": UUID("34343434-3434-4343-8343-343434343434"),
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


def seed_game_status_history_scenario() -> dict[str, UUID]:
    now = datetime.now(UTC)
    starts_at = now + timedelta(days=7)
    ends_at = starts_at + timedelta(hours=1)

    with SessionLocal() as db:
        admin = upsert_by_id(
            db,
            User,
            DEV_IDS["status_history_admin_id"],
            {
                "auth_user_id": "dev-status-history-admin",
                "role": "admin",
                "email": "dev-status-history-admin@pickuplane.local",
                "phone": "+15550000010",
                "first_name": "Dev",
                "last_name": "StatusAdmin",
                "date_of_birth": date(1990, 3, 15),
                "home_city": "Chicago",
                "home_state": "IL",
                "account_status": "active",
                "hosting_status": "eligible",
                "deleted_at": None,
                "updated_at": now,
            },
            lookup_filters={"auth_user_id": "dev-status-history-admin"},
        )
        db.flush()

        venue = upsert_by_id(
            db,
            Venue,
            DEV_IDS["status_history_venue_id"],
            {
                "name": "Dev Status History Field",
                "address_line_1": "654 Status Ave",
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
            DEV_IDS["status_history_game_id"],
            {
                "game_type": "official",
                "publish_status": "published",
                "game_status": "scheduled",
                "title": "Dev Game Ready For Status History",
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
            "status_history_admin_id": admin.id,
            "status_history_venue_id": venue.id,
            "status_history_game_id": game.id,
        }


def main() -> None:
    ids = seed_game_status_history_scenario()

    print("Game status history scenario data ready.")
    print("")
    print("Use these IDs in Postman:")
    for label, value in ids.items():
        print(f"{label}: {value}")
    print("")
    print("POST /game-status-history body:")
    print("{")
    print(f'  "game_id": "{ids["status_history_game_id"]}",')
    print('  "old_publish_status": "draft",')
    print('  "new_publish_status": "published",')
    print('  "old_game_status": "scheduled",')
    print('  "new_game_status": "scheduled",')
    print(f'  "changed_by_user_id": "{ids["status_history_admin_id"]}",')
    print('  "change_source": "admin",')
    print('  "change_reason": "Published the game for players to book."')
    print("}")


if __name__ == "__main__":
    main()
