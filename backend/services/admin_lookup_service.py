"""Admin lookup queries for users and venues."""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.models import User, Venue


def normalized_like_query(query: str | None) -> str | None:
    normalized_query = " ".join((query or "").strip().lower().split())
    if not normalized_query:
        return None

    return f"%{normalized_query}%"


def list_admin_lookup_users(
    db: Session,
    *,
    query: str | None = None,
    limit: int = 100,
) -> list[User]:
    statement = select(User).where(User.deleted_at.is_(None))
    like_query = normalized_like_query(query)

    if like_query is not None:
        full_name = func.lower(
            func.concat(
                func.coalesce(User.first_name, ""),
                " ",
                func.coalesce(User.last_name, ""),
            )
        )
        statement = statement.where(
            or_(
                func.lower(func.coalesce(User.email, "")).like(like_query),
                func.lower(func.coalesce(User.phone, "")).like(like_query),
                full_name.like(like_query),
            )
        )

    users = db.scalars(
        statement.order_by(User.created_at.desc()).limit(limit)
    ).all()
    return list(users)


def list_admin_lookup_venues(
    db: Session,
    *,
    query: str | None = None,
    include_inactive: bool = False,
    limit: int = 100,
) -> list[Venue]:
    statement = select(Venue).where(Venue.deleted_at.is_(None))

    if not include_inactive:
        statement = statement.where(Venue.is_active.is_(True))

    like_query = normalized_like_query(query)
    if like_query is not None:
        statement = statement.where(
            or_(
                func.lower(func.coalesce(Venue.name, "")).like(like_query),
                func.lower(func.coalesce(Venue.address_line_1, "")).like(like_query),
                func.lower(func.coalesce(Venue.city, "")).like(like_query),
                func.lower(func.coalesce(Venue.state, "")).like(like_query),
                func.lower(func.coalesce(Venue.neighborhood, "")).like(like_query),
            )
        )

    venues = db.scalars(
        statement.order_by(Venue.is_active.desc(), Venue.created_at.desc()).limit(limit)
    ).all()
    return list(venues)
