from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import PolicyDocument, User

DEV_IDS = {
    "policy_acceptance_user_id": UUID("82828282-8282-4882-8882-828282828282"),
    "policy_acceptance_document_id": UUID("83838383-8383-4883-8883-838383838383"),
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


def seed_policy_acceptance_scenario() -> dict[str, UUID]:
    now = datetime.now(UTC)

    with SessionLocal() as db:
        user = upsert_by_id(
            db,
            User,
            DEV_IDS["policy_acceptance_user_id"],
            {
                "auth_user_id": "dev-policy-acceptance-user",
                "role": "player",
                "email": "dev-policy-acceptance-user@pickuplane.local",
                "phone": "+15550000071",
                "first_name": "Dev",
                "last_name": "PolicyAcceptanceUser",
                "date_of_birth": date(1995, 1, 1),
                "home_city": "Chicago",
                "home_state": "IL",
                "account_status": "active",
                "hosting_status": "not_eligible",
                "deleted_at": None,
                "updated_at": now,
            },
            lookup_filters={"auth_user_id": "dev-policy-acceptance-user"},
        )

        policy_document = upsert_by_id(
            db,
            PolicyDocument,
            DEV_IDS["policy_acceptance_document_id"],
            {
                "policy_type": "terms_of_service",
                "version": "v1.1",
                "title": "Pickup Lane Terms of Service for Acceptance Test",
                "content_url": None,
                "content_text": "These are test terms for policy acceptance testing.",
                "effective_at": now,
                "retired_at": None,
                "is_active": True,
                "updated_at": now,
            },
            lookup_filters={
                "policy_type": "terms_of_service",
                "version": "v1.1",
            },
        )

        db.commit()

        return {
            "policy_acceptance_user_id": user.id,
            "policy_acceptance_document_id": policy_document.id,
        }


def main() -> None:
    ids = seed_policy_acceptance_scenario()

    print("Policy acceptance scenario data ready.")
    print("")
    print("Use these IDs in Postman:")
    for label, value in ids.items():
        print(f"{label}: {value}")
    print("")
    print("POST /policy-acceptances body:")
    print("{")
    print(f'  "user_id": "{ids["policy_acceptance_user_id"]}",')
    print(f'  "policy_document_id": "{ids["policy_acceptance_document_id"]}",')
    print('  "ip_address": "127.0.0.1",')
    print('  "user_agent": "Postman local test"')
    print("}")


if __name__ == "__main__":
    main()
