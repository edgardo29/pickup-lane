from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import PolicyDocument

DEV_IDS = {
    "policy_document_id": UUID("81818181-8181-4881-8881-818181818181"),
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


def seed_policy_document_scenario() -> dict[str, UUID]:
    now = datetime.now(UTC)

    with SessionLocal() as db:
        policy_document = upsert_by_id(
            db,
            PolicyDocument,
            DEV_IDS["policy_document_id"],
            {
                "policy_type": "terms_of_service",
                "version": "v1.0",
                "title": "Pickup Lane Terms of Service",
                "content_url": None,
                "content_text": "These are test terms of service for local development.",
                "effective_at": now,
                "retired_at": None,
                "is_active": True,
                "updated_at": now,
            },
            lookup_filters={
                "policy_type": "terms_of_service",
                "version": "v1.0",
            },
        )

        db.commit()

        return {
            "policy_document_id": policy_document.id,
        }


def main() -> None:
    ids = seed_policy_document_scenario()

    print("Policy document scenario data ready.")
    print("")
    print("Use this ID in Postman:")
    for label, value in ids.items():
        print(f"{label}: {value}")
    print("")
    print("POST /policy-documents body:")
    print("{")
    print('  "policy_type": "privacy_policy",')
    print('  "version": "v1.0",')
    print('  "title": "Pickup Lane Privacy Policy",')
    print('  "content_url": null,')
    print('  "content_text": "This is a test privacy policy for local development.",')
    print(f'  "effective_at": "{datetime.now(UTC).isoformat()}",')
    print('  "is_active": true')
    print("}")


if __name__ == "__main__":
    main()