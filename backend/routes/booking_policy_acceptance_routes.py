import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import BookingPolicyAcceptance, User
from backend.routes.retired_route_helpers import raise_retired_mutation_route
from backend.schemas import (
    BookingPolicyAcceptanceRead,
)
from backend.services.auth_service import require_active_admin
from backend.services.booking_policy_acceptance_service import (
    get_booking_policy_acceptance_record,
    list_booking_policy_acceptance_records,
)
from backend.services.query_pagination import (
    DEFAULT_ADMIN_COLLECTION_LIMIT,
    MAX_ADMIN_COLLECTION_LIMIT,
)

router = APIRouter(
    prefix="/booking-policy-acceptances",
    tags=["booking_policy_acceptances"],
)


@router.post(
    "",
    status_code=status.HTTP_410_GONE,
)
def create_booking_policy_acceptance(
    current_admin: User = Depends(require_active_admin),
) -> None:
    del current_admin
    raise_retired_mutation_route(
        code="booking_policy_acceptance_scaffold_removed",
        message=(
            "Direct booking policy acceptance creation is no longer supported. "
            "Booking policy state is recorded by product-owned workflows."
        ),
    )


@router.get(
    "/{booking_policy_acceptance_id}",
    response_model=BookingPolicyAcceptanceRead,
    status_code=status.HTTP_200_OK,
)
def get_booking_policy_acceptance(
    booking_policy_acceptance_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> BookingPolicyAcceptance:
    del current_admin
    return get_booking_policy_acceptance_record(db, booking_policy_acceptance_id)


@router.get(
    "",
    response_model=list[BookingPolicyAcceptanceRead],
    status_code=status.HTTP_200_OK,
)
def list_booking_policy_acceptances(
    booking_id: uuid.UUID | None = None,
    policy_document_id: uuid.UUID | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(
        default=DEFAULT_ADMIN_COLLECTION_LIMIT,
        ge=1,
        le=MAX_ADMIN_COLLECTION_LIMIT,
    ),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> list[BookingPolicyAcceptance]:
    del current_admin
    return list_booking_policy_acceptance_records(
        db,
        booking_id=booking_id,
        policy_document_id=policy_document_id,
        limit=limit,
        offset=offset,
    )


@router.patch(
    "/{booking_policy_acceptance_id}",
    status_code=status.HTTP_410_GONE,
)
def update_booking_policy_acceptance(
    booking_policy_acceptance_id: uuid.UUID,
    current_admin: User = Depends(require_active_admin),
) -> None:
    del booking_policy_acceptance_id, current_admin
    raise_retired_mutation_route(
        code="booking_policy_acceptance_scaffold_removed",
        message=(
            "Direct booking policy acceptance updates are no longer supported. "
            "Booking policy state is recorded by product-owned workflows."
        ),
    )
