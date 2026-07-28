"""Admin lookup queries for users and venues."""

import uuid
from typing import Any

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from backend.models import User, Venue

USER_LOOKUP_MIN_TERM_LENGTH = 3
USER_LOOKUP_MAX_TERMS = 3
USER_LOOKUP_MAX_LIMIT = 10
USER_LOOKUP_ALLOWED_ROLES = {"admin", "player"}


def normalized_like_query(query: str | None) -> str | None:
    normalized_query = " ".join((query or "").strip().lower().split())
    if not normalized_query:
        return None

    return f"%{normalized_query}%"


def escape_like_search_term(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def normalize_user_lookup_terms(query: str | None) -> list[str]:
    return [
        term
        for term in " ".join((query or "").strip().lower().split())
        .split()[:USER_LOOKUP_MAX_TERMS]
        if len(term) >= USER_LOOKUP_MIN_TERM_LENGTH
    ]


def user_lookup_condition(term: str):
    pattern = f"%{escape_like_search_term(term)}%"
    return or_(
        User.email.ilike(pattern, escape="\\"),
        User.first_name.ilike(pattern, escape="\\"),
        User.last_name.ilike(pattern, escape="\\"),
    )


def user_lookup_display_name(user: User) -> str:
    name = " ".join(
        part for part in (user.first_name, user.last_name) if part
    ).strip()
    return name or user.email or str(user.id)


def serialize_admin_lookup_user(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "display_name": user_lookup_display_name(user),
        "email": user.email,
        "eligible": user.deleted_at is None and user.account_status == "active",
    }


def list_admin_lookup_users(
    db: Session,
    *,
    account_status: str | None = None,
    query: str | None = None,
    role: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    effective_limit = max(1, min(limit, USER_LOOKUP_MAX_LIMIT))
    statement = select(User).where(User.deleted_at.is_(None))
    if account_status:
        statement = statement.where(User.account_status == account_status)
    if role:
        normalized_role = role.strip().lower()
        if normalized_role not in USER_LOOKUP_ALLOWED_ROLES:
            return []
        statement = statement.where(User.role == normalized_role)

    normalized_query = " ".join((query or "").strip().lower().split())
    if not normalized_query:
        return []

    exact_user_id = None
    try:
        exact_user_id = uuid.UUID(normalized_query)
    except ValueError:
        exact_user_id = None

    terms = normalize_user_lookup_terms(normalized_query)
    lookup_conditions = []
    if terms:
        lookup_conditions.append(
            and_(*(user_lookup_condition(term) for term in terms))
        )
    if exact_user_id is not None:
        lookup_conditions.append(User.id == exact_user_id)
    if not lookup_conditions:
        return []

    escaped_query = escape_like_search_term(normalized_query)
    prefix_pattern = f"{escaped_query}%"
    rank_conditions = []
    if exact_user_id is not None:
        rank_conditions.append((User.id == exact_user_id, 0))
    rank_conditions.extend(
        [
            (func.lower(User.email) == normalized_query, 1),
            (User.email.ilike(prefix_pattern, escape="\\"), 2),
            (User.first_name.ilike(prefix_pattern, escape="\\"), 3),
            (User.last_name.ilike(prefix_pattern, escape="\\"), 3),
        ]
    )

    if len(terms) >= 2:
        first_term = escape_like_search_term(terms[0])
        last_term = escape_like_search_term(terms[-1])
        rank_conditions.append(
            (
                and_(
                    User.first_name.ilike(f"{first_term}%", escape="\\"),
                    User.last_name.ilike(f"{last_term}%", escape="\\"),
                ),
                2,
            )
        )

    rank_expression = case(*rank_conditions, else_=10)
    statement = statement.where(or_(*lookup_conditions))

    users = db.scalars(
        statement.order_by(
            rank_expression.asc(),
            User.last_name.asc().nulls_last(),
            User.first_name.asc().nulls_last(),
            User.email.asc().nulls_last(),
            User.id.asc(),
        ).limit(effective_limit)
    ).all()
    return [serialize_admin_lookup_user(user) for user in users]


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
