import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, Venue
from backend.schemas import VenueCreate, VenueRead, VenueUpdate
from backend.services.auth_service import require_active_admin
from backend.services.venue_service import (
    create_venue_record,
    delete_venue_record,
    get_public_venue_or_404,
    list_public_venue_records,
    update_venue_record,
)

router = APIRouter(prefix="/venues", tags=["venues"])


@router.post("", response_model=VenueRead, status_code=status.HTTP_201_CREATED)
def create_venue(
    venue: VenueCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> Venue:
    del current_admin
    return create_venue_record(db, venue)


@router.get("/{venue_id}", response_model=VenueRead, status_code=status.HTTP_200_OK)
def get_venue(venue_id: uuid.UUID, db: Session = Depends(get_db)) -> Venue:
    return get_public_venue_or_404(db, venue_id)


@router.get("", response_model=list[VenueRead], status_code=status.HTTP_200_OK)
def list_venues(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
) -> list[Venue]:
    return list_public_venue_records(db, include_inactive=include_inactive)


@router.patch("/{venue_id}", response_model=VenueRead, status_code=status.HTTP_200_OK)
def update_venue(
    venue_id: uuid.UUID,
    venue_update: VenueUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> Venue:
    del current_admin
    return update_venue_record(db, venue_id, venue_update)


@router.delete("/{venue_id}", response_model=VenueRead, status_code=status.HTTP_200_OK)
def delete_venue(
    venue_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> Venue:
    del current_admin
    return delete_venue_record(db, venue_id)
