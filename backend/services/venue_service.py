"""Venue lookup and scaffold workflow helpers."""

import hashlib
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import User, Venue
from backend.schemas.venue_schema import VenueCreate, VenueUpdate
from backend.services.admin_action_service import (
    AUDIT_UNAVAILABLE_DETAIL,
    integrity_error_matches_table,
    record_admin_action,
)
from backend.services.query_pagination import (
    DEFAULT_COLLECTION_LIMIT,
    MAX_COLLECTION_LIMIT,
    bounded_collection_limit,
    bounded_collection_offset,
)

APPROVED_VENUE_STATUS = "approved"


def build_venue_conflict_detail(exc: IntegrityError) -> str:
    del exc
    return "Venue could not be saved."


# One facility lookup and creation routine for every path that creates a venue
# from a typed location: community publishing, host editing, official game
# creation, and direct venue creation (database architecture, Section 3.6).
# A venue is a facility, matched on its normalized name and full address; the
# neighborhood is descriptive and does not identify it.

FACILITY_NEEDS_STAFF_REVIEW_DETAIL = (
    "This location matches a venue that needs staff review. "
    "Contact support or choose another location."
)


def normalize_facility_value(value: str | None) -> str:
    """Case, spacing, and periods or commas do not change a facility's identity."""
    without_punctuation = (value or "").replace(".", " ").replace(",", " ")
    return " ".join(without_punctuation.lower().split())


def facility_location_lock_key(country_code: str, state: str, postal_code: str) -> int:
    key_material = (
        f"pickup-lane:venue:{normalize_facility_value(country_code)}:"
        f"{normalize_facility_value(state)}:{normalize_facility_value(postal_code)}"
    )
    digest = hashlib.blake2b(
        key_material.encode("utf-8"), digest_size=8, person=b"pl-venue"
    ).digest()
    return int.from_bytes(digest, byteorder="big", signed=True)


def find_or_create_facility_venue(
    db: Session,
    *,
    name: str,
    address_line_1: str,
    city: str,
    state: str,
    postal_code: str,
    country_code: str,
    neighborhood: str | None,
    new_venue_fields: dict[str, object],
) -> Venue:
    """Reuse the one active venue for this facility, or create it.

    Writers lock the location's state and postal code first, so two requests
    for the same new facility cannot both create it. An inactive, deleted, or
    duplicated match is left for staff to resolve instead of creating another
    copy. ``new_venue_fields`` holds the creator, approval, and any other
    columns used only when a new venue is created.
    """
    db.execute(
        select(
            func.pg_advisory_xact_lock(
                facility_location_lock_key(country_code, state, postal_code)
            )
        )
    )
    identity = (
        normalize_facility_value(name),
        normalize_facility_value(address_line_1),
        normalize_facility_value(city),
    )
    same_area_venues = db.scalars(
        select(Venue).where(
            func.upper(func.trim(Venue.country_code))
            == normalize_facility_value(country_code).upper(),
            func.lower(func.trim(Venue.state)) == normalize_facility_value(state),
            func.lower(func.trim(Venue.postal_code))
            == normalize_facility_value(postal_code),
        )
    ).all()
    matches = [
        venue
        for venue in same_area_venues
        if (
            normalize_facility_value(venue.name),
            normalize_facility_value(venue.address_line_1),
            normalize_facility_value(venue.city),
        )
        == identity
    ]
    usable_matches = [
        venue for venue in matches if venue.deleted_at is None and venue.is_active
    ]
    if len(usable_matches) == 1:
        return usable_matches[0]
    if matches:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=FACILITY_NEEDS_STAFF_REVIEW_DETAIL,
        )

    new_venue = Venue(
        id=uuid.uuid4(),
        name=name,
        address_line_1=address_line_1,
        city=city,
        state=state,
        postal_code=postal_code,
        country_code=country_code,
        neighborhood=neighborhood,
        **new_venue_fields,
    )
    db.add(new_venue)
    db.flush()
    return new_venue


def get_active_user_or_404(db: Session, user_id: uuid.UUID, detail: str) -> User:
    db_user = db.get(User, user_id)

    if db_user is None or db_user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )

    return db_user


def get_existing_venue_or_404(db: Session, venue_id: uuid.UUID) -> Venue:
    db_venue = db.get(Venue, venue_id)

    if db_venue is None or db_venue.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venue not found.",
        )

    return db_venue


def get_public_venue_or_404(db: Session, venue_id: uuid.UUID) -> Venue:
    db_venue = get_existing_venue_or_404(db, venue_id)

    if not db_venue.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venue not found.",
        )

    return db_venue


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
            approved_at = datetime.now(UTC)
    else:
        approved_by_user_id = None
        approved_at = None

    return approved_by_user_id, approved_at


def create_venue_record(db: Session, venue: VenueCreate) -> Venue:
    if venue.created_by_user_id is not None:
        get_active_user_or_404(
            db, venue.created_by_user_id, "Created-by user not found."
        )

    if venue.approved_by_user_id is not None:
        get_active_user_or_404(
            db, venue.approved_by_user_id, "Approved-by user not found."
        )

    approved_by_user_id, approved_at = normalize_venue_approval_fields(
        venue.venue_status,
        venue.approved_by_user_id,
        venue.approved_at,
    )

    try:
        new_venue = find_or_create_facility_venue(
            db,
            name=venue.name,
            address_line_1=venue.address_line_1,
            city=venue.city,
            state=venue.state,
            postal_code=venue.postal_code,
            country_code=venue.country_code,
            neighborhood=venue.neighborhood,
            new_venue_fields={
                "latitude": venue.latitude,
                "longitude": venue.longitude,
                "external_place_id": venue.external_place_id,
                "venue_status": venue.venue_status,
                "created_by_user_id": venue.created_by_user_id,
                "approved_by_user_id": approved_by_user_id,
                "approved_at": approved_at,
                "is_active": venue.is_active,
            },
        )
        db.commit()
        db.refresh(new_venue)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_venue_conflict_detail(exc),
        ) from exc

    return new_venue


def list_public_venue_records(
    db: Session,
    *,
    include_inactive: bool,
    limit: int = DEFAULT_COLLECTION_LIMIT,
    offset: int = 0,
) -> list[Venue]:
    if include_inactive:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )

    statement = (
        select(Venue)
        .where(
            Venue.deleted_at.is_(None),
            Venue.is_active.is_(True),
        )
        .order_by(Venue.created_at.asc(), Venue.id.asc())
        .offset(bounded_collection_offset(offset))
        .limit(bounded_collection_limit(limit, max_limit=MAX_COLLECTION_LIMIT))
    )
    venues = db.scalars(statement).all()
    return list(venues)


def update_venue_record(
    db: Session,
    venue_id: uuid.UUID,
    venue_update: VenueUpdate,
) -> Venue:
    db_venue = get_existing_venue_or_404(db, venue_id)

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

    db_venue.updated_at = datetime.now(UTC)

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


def delete_venue_record(
    db: Session,
    venue_id: uuid.UUID,
    admin_user: User,
) -> Venue:
    db_venue = db.scalar(
        select(Venue)
        .where(Venue.id == venue_id, Venue.deleted_at.is_(None))
        .execution_options(populate_existing=True)
        .with_for_update()
    )
    if db_venue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venue not found.",
        )

    prior_is_active = db_venue.is_active
    prior_venue_status = db_venue.venue_status
    now = datetime.now(UTC)

    db_venue.is_active = False
    db_venue.venue_status = "inactive"
    db_venue.updated_at = now
    db_venue.deleted_at = now

    try:
        db.add(db_venue)
        try:
            record_admin_action(
                db,
                admin_user_id=admin_user.id,
                action_type="delete_venue",
                outcome="succeeded",
                target_venue_id=db_venue.id,
                metadata={
                    "source": "admin_soft_delete",
                    "before": {
                        "is_active": prior_is_active,
                        "venue_status": prior_venue_status,
                        "deleted": False,
                    },
                    "after": {
                        "is_active": False,
                        "venue_status": "inactive",
                        "deleted": True,
                    },
                },
            )
        except (HTTPException, ValueError):
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=AUDIT_UNAVAILABLE_DETAIL,
            ) from None
        db.flush()
        db.commit()
    except IntegrityError as exc:
        audit_failure = integrity_error_matches_table(exc, "admin_actions")
        db.rollback()
        if audit_failure:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=AUDIT_UNAVAILABLE_DETAIL,
            ) from None
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_venue_conflict_detail(exc),
        ) from exc

    db.refresh(db_venue)
    return db_venue
