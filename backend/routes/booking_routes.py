import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Booking, User
from backend.schemas import BookingCreate, BookingRead, BookingUpdate
from backend.services.auth_service import get_current_app_user, require_active_admin
from backend.services.booking_service import (
    create_booking_workflow,
    get_booking_for_user_or_404,
    list_bookings as list_bookings_workflow,
    list_current_user_bookings,
    update_booking_workflow,
)

router = APIRouter(prefix="/bookings", tags=["bookings"])


# Admin-only endpoint for protected booking creation.
@router.post("", response_model=BookingRead, status_code=status.HTTP_201_CREATED)
def create_booking(
    booking: BookingCreate,
    db: Session = Depends(get_db),
    _current_admin: User = Depends(require_active_admin),
) -> Booking:
    return create_booking_workflow(db, booking)


@router.get("/me", response_model=list[BookingRead], status_code=status.HTTP_200_OK)
def list_my_bookings(
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> list[Booking]:
    return list_current_user_bookings(db, current_user)


# Fetches a booking visible to the current buyer or money admins.
@router.get("/{booking_id}", response_model=BookingRead, status_code=status.HTTP_200_OK)
def get_booking(
    booking_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_app_user),
) -> Booking:
    return get_booking_for_user_or_404(db, booking_id, current_user)


# Lists own bookings, or all matching bookings for active admins.
@router.get("", response_model=list[BookingRead], status_code=status.HTTP_200_OK)
def list_bookings(
    buyer_user_id: uuid.UUID | None = None,
    game_id: uuid.UUID | None = None,
    booking_status: str | None = None,
    payment_status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_app_user),
) -> list[Booking]:
    return list_bookings_workflow(
        db,
        current_user,
        buyer_user_id=buyer_user_id,
        game_id=game_id,
        booking_status=booking_status,
        payment_status=payment_status,
    )


# Admin-only endpoint for protected booking updates.
@router.patch("/{booking_id}", response_model=BookingRead, status_code=status.HTTP_200_OK)
def update_booking(
    booking_id: uuid.UUID,
    booking_update: BookingUpdate,
    db: Session = Depends(get_db),
    _current_admin: User = Depends(require_active_admin),
) -> Booking:
    return update_booking_workflow(db, booking_id, booking_update)
