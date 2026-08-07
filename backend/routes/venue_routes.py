import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, Venue
from backend.routes.retired_route_helpers import raise_retired_mutation_route
from backend.schemas import VenueRead
from backend.services.auth_service import require_active_admin
from backend.services.venue_service import (
    delete_venue_record,
    get_public_venue_or_404,
    list_public_venue_records,
)

router = APIRouter(prefix="/venues", tags=["venues"])


@router.post("", status_code=status.HTTP_410_GONE)
def create_venue(
    current_admin: User = Depends(require_active_admin),
) -> None:
    del current_admin
    raise_retired_mutation_route(
        code="venue_scaffold_removed",
        message=(
            "Direct venue creation is no longer supported. Use product-owned "
            "game creation or admin venue-image workflows."
        ),
    )


@router.get("/{venue_id}", response_model=VenueRead, status_code=status.HTTP_200_OK)
def get_venue(venue_id: uuid.UUID, db: Session = Depends(get_db)) -> Venue:
    return get_public_venue_or_404(db, venue_id)


@router.get("", response_model=list[VenueRead], status_code=status.HTTP_200_OK)
def list_venues(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
) -> list[Venue]:
    return list_public_venue_records(db, include_inactive=include_inactive)


@router.patch("/{venue_id}", status_code=status.HTTP_410_GONE)
def update_venue(
    venue_id: uuid.UUID,
    current_admin: User = Depends(require_active_admin),
) -> None:
    del venue_id, current_admin
    raise_retired_mutation_route(
        code="venue_scaffold_removed",
        message=(
            "Direct venue updates are no longer supported. Use product-owned "
            "game creation or admin venue-image workflows."
        ),
    )


@router.delete("/{venue_id}", response_model=VenueRead, status_code=status.HTTP_200_OK)
def delete_venue(
    venue_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> Venue:
    del current_admin
    return delete_venue_record(db, venue_id)
