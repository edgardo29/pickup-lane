from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import User

DEV_IDS = {
    "admin_action_admin_user_id": UUID("61616161-6161-4661-8661-616161616161"),
    "admin_action_target_user_id": UUID("62626262-6262-4662-8662-626262626262"),
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


def seed_admin_action_scenario() -> dict[str, UUID]:
    now = datetime.now(UTC)

    with SessionLocal() as db:
        admin_user = upsert_by_id(
            db,
            User,
            DEV_IDS["admin_action_admin_user_id"],
            {
                "auth_user_id": "dev-admin-action-admin",
                "role": "admin",
                "email": "dev-admin-action-admin@pickuplane.local",
                "phone": "+15550000041",
                "first_name": "Dev",
                "last_name": "AdminActionAdmin",
                "date_of_birth": date(1990, 1, 1),
                "home_city": "Chicago",
                "home_state": "IL",
                "account_status": "active",
                "hosting_status": "eligible",
                "deleted_at": None,
                "updated_at": now,
            },
            lookup_filters={"auth_user_id": "dev-admin-action-admin"},
        )

        target_user = upsert_by_id(
            db,
            User,
            DEV_IDS["admin_action_target_user_id"],
            {
                "auth_user_id": "dev-admin-action-target-user",
                "role": "player",
                "email": "dev-admin-action-target-user@pickuplane.local",
                "phone": "+15550000042",
                "first_name": "Dev",
                "last_name": "AdminActionTarget",
                "date_of_birth": date(1995, 1, 1),
                "home_city": "Chicago",
                "home_state": "IL",
                "account_status": "active",
                "hosting_status": "not_eligible",
                "deleted_at": None,
                "updated_at": now,
            },
            lookup_filters={"auth_user_id": "dev-admin-action-target-user"},
        )

        db.commit()

        return {
            "admin_action_admin_user_id": admin_user.id,
            "admin_action_target_user_id": target_user.id,
        }


def main() -> None:
    ids = seed_admin_action_scenario()

    print("Admin action scenario data ready.")
    print("")
    print("Use these IDs in Postman:")
    for label, value in ids.items():
        print(f"{label}: {value}")
    print("")
    print("POST /admin-actions body:")
    print("{")
    print(f'  "admin_user_id": "{ids["admin_action_admin_user_id"]}",')
    print('  "action_type": "suspend_user",')
    print(f'  "target_user_id": "{ids["admin_action_target_user_id"]}",')
    print('  "reason": "Test admin action from Postman.",')
    print('  "metadata": {')
    print('    "source": "postman"')
    print("  }")
    print("}")


if __name__ == "__main__":
    main()