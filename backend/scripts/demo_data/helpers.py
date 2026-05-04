from __future__ import annotations

import uuid
from datetime import UTC, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

DEMO_NAMESPACE = uuid.UUID("7a3fd1d5-c3e5-4a71-a5d7-2f65486bf48f")
CHICAGO_TZ = ZoneInfo("America/Chicago")


def demo_uuid(key: str) -> uuid.UUID:
    return uuid.uuid5(DEMO_NAMESPACE, key)


def now_utc() -> datetime:
    return datetime.now(UTC)


def upcoming_saturday() -> datetime:
    today = datetime.now(CHICAGO_TZ).date()
    days_until_saturday = (5 - today.weekday()) % 7
    if days_until_saturday == 0:
        days_until_saturday = 7

    return datetime.combine(today + timedelta(days=days_until_saturday), time.min, CHICAGO_TZ)


def starts_at(day_offset: int, hour: int, minute: int = 0) -> datetime:
    browse_start = upcoming_saturday() + timedelta(days=day_offset)
    return browse_start.replace(hour=hour, minute=minute)


def ends_at(start: datetime, minutes: int = 90) -> datetime:
    return start + timedelta(minutes=minutes)


def upsert_by_id(
    db: Session,
    model: type,
    record_id: uuid.UUID,
    values: dict[str, Any],
) -> Any:
    record = db.get(model, record_id)

    if record is None:
        record = model(id=record_id)
        db.add(record)

    for field_name, field_value in values.items():
        setattr(record, field_name, field_value)

    return record


def find_one_by_id(db: Session, model: type, record_id: uuid.UUID) -> Any | None:
    return db.scalars(select(model).where(model.id == record_id)).first()
