from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, Venue
from backend.schemas import UserRead, VenueRead
from backend.services.auth_service import require_active_admin
from backend.services.admin_lookup_service import (
    list_admin_lookup_users as list_admin_lookup_users_workflow,
    list_admin_lookup_venues as list_admin_lookup_venues_workflow,
)

router = APIRouter(prefix="/admin/lookups", tags=["admin_lookups"])


@router.get("/users", response_model=list[UserRead], status_code=status.HTTP_200_OK)
def list_admin_lookup_users(
    query: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    _current_admin: User = Depends(require_active_admin),
) -> list[User]:
    return list_admin_lookup_users_workflow(db, query=query, limit=limit)


@router.get("/venues", response_model=list[VenueRead], status_code=status.HTTP_200_OK)
def list_admin_lookup_venues(
    query: str | None = Query(default=None, max_length=120),
    include_inactive: bool = False,
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    _current_admin: User = Depends(require_active_admin),
) -> list[Venue]:
    return list_admin_lookup_venues_workflow(
        db,
        query=query,
        include_inactive=include_inactive,
        limit=limit,
    )
