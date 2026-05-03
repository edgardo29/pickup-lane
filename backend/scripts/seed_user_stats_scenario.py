from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import User

DEV_IDS = {
    "user_stats_user_id": UUID("51515151-5151-4551-8551-515151515151"),
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


def seed_user_stats_scenario() -> dict[str, UUID]:
    now = datetime.now(UTC)

    with SessionLocal() as db:
        user = upsert_by_id(
            db,
            User,
            DEV_IDS["user_stats_user_id"],
            {
                "auth_user_id": "dev-user-stats-user",
                "role": "player",
                "email": "dev-user-stats-user@pickuplane.local",
                "phone": "+15550000031",
                "first_name": "Dev",
                "last_name": "UserStatsUser",
                "date_of_birth": date(1995, 1, 1),
                "home_city": "Chicago",
                "home_state": "IL",
                "account_status": "active",
                "hosting_status": "not_eligible",
                "deleted_at": None,
                "updated_at": now,
            },
            lookup_filters={"auth_user_id": "dev-user-stats-user"},
        )

        db.commit()

        return {
            "user_stats_user_id": user.id,
        }


def main() -> None:
    ids = seed_user_stats_scenario()

    print("User stats scenario data ready.")
    print("")
    print("Use this ID in Postman:")
    for label, value in ids.items():
        print(f"{label}: {value}")
    print("")
    print("POST /user-stats body:")
    print("{")
    print(f'  "user_id": "{ids["user_stats_user_id"]}",')
    print('  "games_played_count": 3,')
    print('  "games_hosted_completed_count": 1,')
    print('  "no_show_count": 0,')
    print('  "late_cancel_count": 1,')
    print('  "host_cancel_count": 0')
    print("}")


if __name__ == "__main__":
    main()