from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import User, Venue

DEV_IDS = {
    "venue_approval_request_user_id": UUID(
        "91919191-9191-4991-8991-919191919191"
    ),
    "venue_approval_request_admin_id": UUID(
        "92929292-9292-4992-8992-929292929292"
    ),
    "venue_approval_request_venue_id": UUID(
        "93939393-9393-4993-8993-939393939393"
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


def seed_venue_approval_request_scenario() -> dict[str, UUID]:
    now = datetime.now(UTC)

    with SessionLocal() as db:
        user = upsert_by_id(
            db,
            User,
            DEV_IDS["venue_approval_request_user_id"],
            {
                "auth_user_id": "dev-venue-approval-request-user",
                "role": "player",
                "email": "dev-venue-approval-request-user@pickuplane.local",
                "phone": "+15550000081",
                "first_name": "Dev",
                "last_name": "VenueApprovalRequestUser",
                "date_of_birth": date(1995, 1, 1),
                "home_city": "Chicago",
                "home_state": "IL",
                "account_status": "active",
                "hosting_status": "not_eligible",
                "deleted_at": None,
                "updated_at": now,
            },
            lookup_filters={"phone": "+15550000081"},
        )

        admin = upsert_by_id(
            db,
            User,
            DEV_IDS["venue_approval_request_admin_id"],
            {
                "auth_user_id": "dev-venue-approval-request-admin",
                "role": "admin",
                "email": "dev-venue-approval-request-admin@pickuplane.local",
                "phone": "+15550000082",
                "first_name": "Dev",
                "last_name": "VenueApprovalRequestAdmin",
                "date_of_birth": date(1990, 1, 1),
                "home_city": "Chicago",
                "home_state": "IL",
                "account_status": "active",
                "hosting_status": "eligible",
                "deleted_at": None,
                "updated_at": now,
            },
            lookup_filters={"phone": "+15550000082"},
        )
        db.flush()

        venue = upsert_by_id(
            db,
            Venue,
            DEV_IDS["venue_approval_request_venue_id"],
            {
                "name": "Dev Approved Venue Request Field",
                "address_line_1": "888 Venue Request Ave",
                "city": "Chicago",
                "state": "IL",
                "postal_code": "60601",
                "country_code": "US",
                "venue_status": "approved",
                "created_by_user_id": user.id,
                "approved_by_user_id": admin.id,
                "approved_at": now,
                "is_active": True,
                "deleted_at": None,
                "updated_at": now,
            },
        )

        db.commit()

        return {
            "venue_approval_request_user_id": user.id,
            "venue_approval_request_admin_id": admin.id,
            "venue_approval_request_venue_id": venue.id,
        }


def main() -> None:
    ids = seed_venue_approval_request_scenario()

    print("Venue approval request scenario data ready.")
    print("")
    print("Use these IDs in Postman:")
    for label, value in ids.items():
        print(f"{label}: {value}")
    print("")
    print("POST /venue-approval-requests body:")
    print("{")
    print(
        '  "submitted_by_user_id": '
        f'"{ids["venue_approval_request_user_id"]}",'
    )
    print('  "requested_name": "Dev Requested Soccer Field",')
    print('  "requested_address_line_1": "999 Requested Field Ave",')
    print('  "requested_city": "Chicago",')
    print('  "requested_state": "IL",')
    print('  "requested_postal_code": "60601",')
    print('  "requested_country_code": "US"')
    print("}")
    print("")
    print("PATCH approval body:")
    print("{")
    print('  "request_status": "approved",')
    print(f'  "venue_id": "{ids["venue_approval_request_venue_id"]}",')
    print(f'  "reviewed_by_user_id": "{ids["venue_approval_request_admin_id"]}",')
    print(f'  "reviewed_at": "{datetime.now(UTC).isoformat()}",')
    print('  "review_notes": "Approved from local Postman test."')
    print("}")


if __name__ == "__main__":
    main()