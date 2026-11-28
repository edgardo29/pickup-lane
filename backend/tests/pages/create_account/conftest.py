"""Account snapshots for F05's read-only and rejected operations."""

from sqlalchemy import select

from backend.models import User, UserSettings, UserStats


def accounts(db):
    return {
        model.__name__: db.execute(
            select(model.__table__).order_by(*model.__table__.primary_key)
        ).all()
        for model in (User, UserSettings, UserStats)
    }
