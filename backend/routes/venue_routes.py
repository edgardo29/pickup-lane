import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, Venue
from backend.schemas import VenueCreate, VenueRead, VenueUpdate

router = APIRouter(prefix="/venues", tags=["venues"])

APPROVED_VENUE_STATUS = "approved"


def build_venue_conflict_detail(exc: IntegrityError) -> str:
    # The venues table does not currently have user-facing unique constraints,
    # so fall back to the database error text for now if an integrity issue
    # occurs.
    return str(exc.orig)


def get_active_user_or_404(db: Session, user_id: uuid.UUID, detail: str) -> User:
    db_user = db.get(User, user_id)

    if db_user is None or db_user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )

    return db_user


def normalize_venue_approval_fields(
    venue_status: str,
    approved_by_user_id: uuid.UUID | None,
    approved_at: datetime | None,
) -> tuple[uuid.UUID | None, datetime | None]:
    # Approved venues should always carry an approver and approval timestamp.
    # For every other status, approval metadata is cleared so the row cannot
    # drift into a half-approved state.
    if venue_status == APPROVED_VENUE_STATUS:
        if approved_by_user_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Approved venues require approved_by_user_id.",
            )

        if approved_at is None:
            approved_at = datetime.now(timezone.utc)
    else:
        approved_by_user_id = None
        approved_at = None

    return approved_by_user_id, approved_at


# This route creates a venue record that can later be reviewed or approved by
# the app's moderation flow.
@router.post("", response_model=VenueRead, status_code=status.HTTP_201_CREATED)
def create_venue(venue: VenueCreate, db: Session = Depends(get_db)) -> Venue:
    if venue.created_by_user_id is not None:
        get_active_user_or_404(db, venue.created_by_user_id, "Created-by user not found.")

    if venue.approved_by_user_id is not None:
        get_active_user_or_404(
            db, venue.approved_by_user_id, "Approved-by user not found."
        )

    approved_by_user_id, approved_at = normalize_venue_approval_fields(
        venue.venue_status,
        venue.approved_by_user_id,
        venue.approved_at,
    )

    new_venue = Venue(
        id=uuid.uuid4(),
        name=venue.name,
        address_line_1=venue.address_line_1,
        city=venue.city,
        state=venue.state,
        postal_code=venue.postal_code,
        country_code=venue.country_code,
        neighborhood=venue.neighborhood,
        latitude=venue.latitude,
        longitude=venue.longitude,
        external_place_id=venue.external_place_id,
        venue_status=venue.venue_status,
        created_by_user_id=venue.created_by_user_id,
        approved_by_user_id=approved_by_user_id,
        approved_at=approved_at,
        is_active=venue.is_active,
    )

    try:
        db.add(new_venue)
        db.commit()
        db.refresh(new_venue)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_venue_conflict_detail(exc),
        ) from exc

    return new_venue


# This route fetches a single venue record by its internal UUID.
@router.get("/{venue_id}", response_model=VenueRead, status_code=status.HTTP_200_OK)
def get_venue(venue_id: uuid.UUID, db: Session = Depends(get_db)) -> Venue:
    db_venue = db.get(Venue, venue_id)

    if db_venue is None or db_venue.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venue not found.",
        )

    return db_venue


# This route returns venue records currently stored in the app database.
@router.get("", response_model=list[VenueRead], status_code=status.HTTP_200_OK)
def list_venues(
    include_inactive: bool = False, db: Session = Depends(get_db)
) -> list[Venue]:
    statement = select(Venue).where(Venue.deleted_at.is_(None))

    if not include_inactive:
        statement = statement.where(Venue.is_active.is_(True))

    # Show the venues most relevant to the normal app flow first: active
    # records by default, then oldest-created records within that filtered set.
    venues = db.scalars(
        statement.order_by(Venue.created_at.asc())
    ).all()
    return list(venues)


# This route applies partial updates to an existing venue record.
@router.patch("/{venue_id}", response_model=VenueRead, status_code=status.HTTP_200_OK)
def update_venue(
    venue_id: uuid.UUID, venue_update: VenueUpdate, db: Session = Depends(get_db)
) -> Venue:
    db_venue = db.get(Venue, venue_id)

    if db_venue is None or db_venue.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venue not found.",
        )

    if venue_update.created_by_user_id is not None:
        get_active_user_or_404(
            db, venue_update.created_by_user_id, "Created-by user not found."
        )

    if venue_update.approved_by_user_id is not None:
        get_active_user_or_404(
            db, venue_update.approved_by_user_id, "Approved-by user not found."
        )

    update_data = venue_update.model_dump(exclude_unset=True)

    effective_venue_status = update_data.get("venue_status", db_venue.venue_status)
    effective_approved_by_user_id = update_data.get(
        "approved_by_user_id", db_venue.approved_by_user_id
    )
    effective_approved_at = update_data.get("approved_at", db_venue.approved_at)

    approved_by_user_id, approved_at = normalize_venue_approval_fields(
        effective_venue_status,
        effective_approved_by_user_id,
        effective_approved_at,
    )
    update_data["approved_by_user_id"] = approved_by_user_id
    update_data["approved_at"] = approved_at

    for field_name, field_value in update_data.items():
        setattr(db_venue, field_name, field_value)

    # Keep updated_at aligned with the latest venue change so downstream
    # clients can reliably track when the record was last modified.
    db_venue.updated_at = datetime.now(timezone.utc)

    try:
        db.add(db_venue)
        db.commit()
        db.refresh(db_venue)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_venue_conflict_detail(exc),
        ) from exc

    return db_venue


# This route performs a soft delete so the venue record stays available for
# history and review purposes without appearing in normal venue listings.
@router.delete("/{venue_id}", response_model=VenueRead, status_code=status.HTTP_200_OK)
def delete_venue(venue_id: uuid.UUID, db: Session = Depends(get_db)) -> Venue:
    db_venue = db.get(Venue, venue_id)

    if db_venue is None or db_venue.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venue not found.",
        )

    db_venue.is_active = False
    db_venue.venue_status = "inactive"
    db_venue.updated_at = datetime.now(timezone.utc)
    db_venue.deleted_at = datetime.now(timezone.utc)

    try:
        db.add(db_venue)
        db.commit()
        db.refresh(db_venue)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_venue_conflict_detail(exc),
        ) from exc

    return db_venue
