import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User, VenueApprovalRequest
from backend.routes.retired_route_helpers import raise_retired_mutation_route
from backend.schemas import (
    VenueApprovalRequestRead,
)
from backend.services.auth_service import require_active_admin
from backend.services.venue_approval_request_service import (
    get_venue_approval_request_record,
    list_venue_approval_request_records,
)

router = APIRouter(
    prefix="/venue-approval-requests",
    tags=["venue_approval_requests"],
)


@router.post(
    "",
    status_code=status.HTTP_410_GONE,
)
def create_venue_approval_request(
    current_admin: User = Depends(require_active_admin),
) -> None:
    del current_admin
    raise_retired_mutation_route(
        code="venue_approval_request_scaffold_removed",
        message=(
            "Direct venue approval request creation is no longer supported. "
            "Use product-owned venue approval workflows."
        ),
    )


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
    status_code=status.HTTP_410_GONE,
)
def update_venue_approval_request(
    venue_approval_request_id: uuid.UUID,
    current_admin: User = Depends(require_active_admin),
) -> None:
    del venue_approval_request_id, current_admin
    raise_retired_mutation_route(
        code="venue_approval_request_scaffold_removed",
        message=(
            "Direct venue approval request updates are no longer supported. "
            "Use product-owned venue approval workflows."
        ),
    )
