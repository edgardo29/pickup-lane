import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, VenueApprovalRequest
from backend.schemas import (
    VenueApprovalRequestCreate,
    VenueApprovalRequestRead,
    VenueApprovalRequestUpdate,
)
from backend.services.auth_service import require_active_admin
from backend.services.venue_approval_request_service import (
    create_venue_approval_request_record,
    get_venue_approval_request_record,
    list_venue_approval_request_records,
    update_venue_approval_request_record,
)

router = APIRouter(
    prefix="/venue-approval-requests",
    tags=["venue_approval_requests"],
)


@router.post(
    "",
    response_model=VenueApprovalRequestRead,
    status_code=status.HTTP_201_CREATED,
)
def create_venue_approval_request(
    venue_approval_request: VenueApprovalRequestCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> VenueApprovalRequest:
    del current_admin
    return create_venue_approval_request_record(db, venue_approval_request)


@router.get(
    "/{venue_approval_request_id}",
    response_model=VenueApprovalRequestRead,
    status_code=status.HTTP_200_OK,
)
def get_venue_approval_request(
    venue_approval_request_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> VenueApprovalRequest:
    del current_admin
    return get_venue_approval_request_record(db, venue_approval_request_id)


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
    current_admin: User = Depends(require_active_admin),
) -> list[VenueApprovalRequest]:
    del current_admin
    return list_venue_approval_request_records(
        db,
        submitted_by_user_id=submitted_by_user_id,
        venue_id=venue_id,
        reviewed_by_user_id=reviewed_by_user_id,
        request_status=request_status,
    )


@router.patch(
    "/{venue_approval_request_id}",
    response_model=VenueApprovalRequestRead,
    status_code=status.HTTP_200_OK,
)
def update_venue_approval_request(
    venue_approval_request_id: uuid.UUID,
    venue_approval_request_update: VenueApprovalRequestUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> VenueApprovalRequest:
    del current_admin
    return update_venue_approval_request_record(
        db,
        venue_approval_request_id,
        venue_approval_request_update,
    )
