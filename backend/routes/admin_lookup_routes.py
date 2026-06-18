from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, Venue
from backend.schemas import UserRead, VenueRead
from backend.services.admin_permission_service import (
    PERMISSION_OFFICIAL_GAMES_READ,
    PERMISSION_USERS_READ,
)
from backend.services.auth_service import require_admin_permission

router = APIRouter(prefix="/admin/lookups", tags=["admin_lookups"])


def normalized_like_query(query: str | None) -> str | None:
    normalized_query = " ".join((query or "").strip().lower().split())
    if not normalized_query:
        return None

    return f"%{normalized_query}%"


@router.get("/users", response_model=list[UserRead], status_code=status.HTTP_200_OK)
def list_admin_lookup_users(
    query: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_permission(PERMISSION_USERS_READ)),
) -> list[User]:
    del current_admin
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


@router.get("/venues", response_model=list[VenueRead], status_code=status.HTTP_200_OK)
def list_admin_lookup_venues(
    query: str | None = Query(default=None, max_length=120),
    include_inactive: bool = False,
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_OFFICIAL_GAMES_READ)
    ),
) -> list[Venue]:
    del current_admin
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
