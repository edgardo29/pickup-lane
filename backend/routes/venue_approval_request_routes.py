import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, Venue, VenueApprovalRequest
from backend.schemas import (
    VenueApprovalRequestCreate,
    VenueApprovalRequestRead,
    VenueApprovalRequestUpdate,
)

router = APIRouter(
    prefix="/venue-approval-requests",
    tags=["venue_approval_requests"],
)

VALID_REQUEST_STATUSES = {
    "pending_review",
    "approved",
    "rejected",
    "inactive",
}
REVIEWED_REQUEST_STATUSES = {
    "approved",
    "rejected",
    "inactive",
}
REQUESTED_TEXT_FIELDS = {
    "requested_name",
    "requested_address_line_1",
    "requested_city",
    "requested_state",
    "requested_postal_code",
}


def build_venue_approval_request_conflict_detail(exc: IntegrityError) -> str:
    error_text = str(exc.orig)

    if "ck_venue_approval_requests_request_status" in error_text:
        return "request_status is not supported."

    if "ck_venue_approval_requests_requested_country_code" in error_text:
        return "requested_country_code must be exactly 2 characters."

    if "ck_venue_approval_requests_reviewed_status_requires_reviewed_at" in error_text:
        return "Reviewed venue approval requests require reviewed_at."

    if "ck_venue_approval_requests_approved_requires_venue_id" in error_text:
        return "Approved venue approval requests require venue_id."

    return error_text


def get_active_user_or_404(db: Session, user_id: uuid.UUID, detail: str) -> User:
    db_user = db.get(User, user_id)

    if db_user is None or db_user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )

    return db_user


def get_venue_or_404(db: Session, venue_id: uuid.UUID) -> Venue:
    db_venue = db.get(Venue, venue_id)

    if db_venue is None or db_venue.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venue not found.",
        )

    return db_venue


def validate_venue_approval_request_business_rules(
    request_data: dict[str, Any],
) -> None:
    for field_name in (
        "submitted_by_user_id",
        "requested_name",
        "requested_address_line_1",
        "requested_city",
        "requested_state",
        "requested_postal_code",
        "requested_country_code",
        "request_status",
    ):
        if request_data[field_name] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} cannot be null.",
            )

    for field_name in REQUESTED_TEXT_FIELDS:
        if not request_data[field_name].strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} must not be empty.",
            )

    if request_data["request_status"] not in VALID_REQUEST_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="request_status is not supported.",
        )

    if not request_data["requested_country_code"].strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="requested_country_code must not be empty.",
        )

    if len(request_data["requested_country_code"]) != 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="requested_country_code must be exactly 2 characters.",
        )

    if (
        request_data["request_status"] in REVIEWED_REQUEST_STATUSES
        and request_data["reviewed_at"] is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reviewed venue approval requests require reviewed_at.",
        )

    if (
        request_data["request_status"] in REVIEWED_REQUEST_STATUSES
        and request_data["reviewed_by_user_id"] is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reviewed venue approval requests require reviewed_by_user_id.",
        )

    if request_data["request_status"] == "approved" and request_data["venue_id"] is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Approved venue approval requests require venue_id.",
        )


def validate_venue_approval_request_references(
    db: Session,
    request_data: dict[str, Any],
) -> None:
    get_active_user_or_404(
        db,
        request_data["submitted_by_user_id"],
        "Submitted by user not found.",
    )

    if request_data["venue_id"] is not None:
        get_venue_or_404(db, request_data["venue_id"])

    if request_data["reviewed_by_user_id"] is not None:
        get_active_user_or_404(
            db,
            request_data["reviewed_by_user_id"],
            "Reviewed by user not found.",
        )


def validate_venue_approval_request_update_rules(
    update_data: dict[str, Any],
) -> None:
    for field_name in (
        "requested_name",
        "requested_address_line_1",
        "requested_city",
        "requested_state",
        "requested_postal_code",
        "requested_country_code",
        "request_status",
    ):
        if field_name in update_data and update_data[field_name] is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{field_name} cannot be null.",
            )


def normalize_venue_approval_request_fields(
    request_data: dict[str, Any],
) -> dict[str, Any]:
    normalized_data = dict(request_data)

    if (
        "requested_country_code" in normalized_data
        and normalized_data["requested_country_code"] is not None
    ):
        normalized_data["requested_country_code"] = normalized_data[
            "requested_country_code"
        ].strip().upper()

    return normalized_data


# This route creates one user-submitted venue approval request for admin review.
@router.post(
    "",
    response_model=VenueApprovalRequestRead,
    status_code=status.HTTP_201_CREATED,
)
def create_venue_approval_request(
    venue_approval_request: VenueApprovalRequestCreate,
    db: Session = Depends(get_db),
) -> VenueApprovalRequest:
    request_data = normalize_venue_approval_request_fields(
        venue_approval_request.model_dump()
    )
    validate_venue_approval_request_business_rules(request_data)
    validate_venue_approval_request_references(db, request_data)

    new_venue_approval_request = VenueApprovalRequest(
        id=uuid.uuid4(),
        **request_data,
    )

    try:
        db.add(new_venue_approval_request)
        db.commit()
        db.refresh(new_venue_approval_request)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_venue_approval_request_conflict_detail(exc),
        ) from exc

    return new_venue_approval_request


# This route fetches a single venue approval request by its internal UUID.
@router.get(
    "/{venue_approval_request_id}",
    response_model=VenueApprovalRequestRead,
    status_code=status.HTTP_200_OK,
)
def get_venue_approval_request(
    venue_approval_request_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> VenueApprovalRequest:
    db_venue_approval_request = db.get(
        VenueApprovalRequest,
        venue_approval_request_id,
    )

    if db_venue_approval_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venue approval request not found.",
        )

    return db_venue_approval_request


# This route returns venue approval requests currently stored in the app database.
@router.get(
    "",
    response_model=list[VenueApprovalRequestRead],
    status_code=status.HTTP_200_OK,
)
def list_venue_approval_requests(
    submitted_by_user_id: uuid.UUID | None = None,
    venue_id: uuid.UUID | None = None,
    reviewed_by_user_id: uuid.UUID | None = None,
    request_status: str | None = None,
    db: Session = Depends(get_db),
) -> list[VenueApprovalRequest]:
    statement = select(VenueApprovalRequest)

    if submitted_by_user_id is not None:
        statement = statement.where(
            VenueApprovalRequest.submitted_by_user_id == submitted_by_user_id
        )

    if venue_id is not None:
        statement = statement.where(VenueApprovalRequest.venue_id == venue_id)

    if reviewed_by_user_id is not None:
        statement = statement.where(
            VenueApprovalRequest.reviewed_by_user_id == reviewed_by_user_id
        )

    if request_status is not None:
        if request_status not in VALID_REQUEST_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="request_status is not supported.",
            )
        statement = statement.where(VenueApprovalRequest.request_status == request_status)

    venue_approval_requests = db.scalars(
        statement.order_by(VenueApprovalRequest.created_at.desc())
    ).all()
    return list(venue_approval_requests)


# This route applies partial corrections or admin review updates to a venue request.
@router.patch(
    "/{venue_approval_request_id}",
    response_model=VenueApprovalRequestRead,
    status_code=status.HTTP_200_OK,
)
def update_venue_approval_request(
    venue_approval_request_id: uuid.UUID,
    venue_approval_request_update: VenueApprovalRequestUpdate,
    db: Session = Depends(get_db),
) -> VenueApprovalRequest:
    db_venue_approval_request = db.get(
        VenueApprovalRequest,
        venue_approval_request_id,
    )

    if db_venue_approval_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Venue approval request not found.",
        )

    update_data = normalize_venue_approval_request_fields(
        venue_approval_request_update.model_dump(exclude_unset=True)
    )
    validate_venue_approval_request_update_rules(update_data)

    effective_request_data = {
        "submitted_by_user_id": db_venue_approval_request.submitted_by_user_id,
        "venue_id": update_data.get("venue_id", db_venue_approval_request.venue_id),
        "requested_name": update_data.get(
            "requested_name",
            db_venue_approval_request.requested_name,
        ),
        "requested_address_line_1": update_data.get(
            "requested_address_line_1",
            db_venue_approval_request.requested_address_line_1,
        ),
        "requested_city": update_data.get(
            "requested_city",
            db_venue_approval_request.requested_city,
        ),
        "requested_state": update_data.get(
            "requested_state",
            db_venue_approval_request.requested_state,
        ),
        "requested_postal_code": update_data.get(
            "requested_postal_code",
            db_venue_approval_request.requested_postal_code,
        ),
        "requested_country_code": update_data.get(
            "requested_country_code",
            db_venue_approval_request.requested_country_code,
        ),
        "request_status": update_data.get(
            "request_status",
            db_venue_approval_request.request_status,
        ),
        "reviewed_by_user_id": update_data.get(
            "reviewed_by_user_id",
            db_venue_approval_request.reviewed_by_user_id,
        ),
        "reviewed_at": update_data.get(
            "reviewed_at",
            db_venue_approval_request.reviewed_at,
        ),
        "review_notes": update_data.get(
            "review_notes",
            db_venue_approval_request.review_notes,
        ),
    }
    validate_venue_approval_request_business_rules(effective_request_data)
    validate_venue_approval_request_references(db, effective_request_data)

    for field_name, field_value in update_data.items():
        setattr(db_venue_approval_request, field_name, field_value)

    db_venue_approval_request.updated_at = datetime.now(timezone.utc)

    try:
        db.add(db_venue_approval_request)
        db.commit()
        db.refresh(db_venue_approval_request)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_venue_approval_request_conflict_detail(exc),
        ) from exc

    return db_venue_approval_request
