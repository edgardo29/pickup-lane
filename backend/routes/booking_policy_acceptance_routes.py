import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import BookingPolicyAcceptance, User
from backend.schemas import (
    BookingPolicyAcceptanceCreate,
    BookingPolicyAcceptanceRead,
    BookingPolicyAcceptanceUpdate,
)
from backend.services.admin_permission_service import PERMISSION_POLICIES_MANAGE
from backend.services.auth_service import require_admin_permission
from backend.services.booking_policy_acceptance_service import (
    create_booking_policy_acceptance_record,
    get_booking_policy_acceptance_record,
    list_booking_policy_acceptance_records,
    update_booking_policy_acceptance_record,
)

router = APIRouter(
    prefix="/booking-policy-acceptances",
    tags=["booking_policy_acceptances"],
)


@router.post(
    "",
    response_model=BookingPolicyAcceptanceRead,
    status_code=status.HTTP_201_CREATED,
)
def create_booking_policy_acceptance(
    booking_policy_acceptance: BookingPolicyAcceptanceCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_POLICIES_MANAGE)
    ),
) -> BookingPolicyAcceptance:
    del current_admin
    return create_booking_policy_acceptance_record(db, booking_policy_acceptance)


@router.get(
    "/{booking_policy_acceptance_id}",
    response_model=BookingPolicyAcceptanceRead,
    status_code=status.HTTP_200_OK,
)
def get_booking_policy_acceptance(
    booking_policy_acceptance_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_POLICIES_MANAGE)
    ),
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
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_POLICIES_MANAGE)
    ),
) -> list[BookingPolicyAcceptance]:
    del current_admin
    return list_booking_policy_acceptance_records(
        db,
        booking_id=booking_id,
        policy_document_id=policy_document_id,
    )


@router.patch(
    "/{booking_policy_acceptance_id}",
    response_model=BookingPolicyAcceptanceRead,
    status_code=status.HTTP_200_OK,
)
def update_booking_policy_acceptance(
    booking_policy_acceptance_id: uuid.UUID,
    booking_policy_acceptance_update: BookingPolicyAcceptanceUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_POLICIES_MANAGE)
    ),
) -> BookingPolicyAcceptance:
    del current_admin
    return update_booking_policy_acceptance_record(
        db,
        booking_policy_acceptance_id,
        booking_policy_acceptance_update,
    )
