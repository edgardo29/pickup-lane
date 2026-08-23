import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Booking, User
from backend.routes.retired_route_helpers import raise_retired_mutation_route
from backend.schemas import BookingRead
from backend.services.auth_service import get_current_app_user, require_active_admin
from backend.services.booking_service import (
    get_booking_for_user_or_404,
    list_bookings as list_bookings_workflow,
    list_current_user_bookings,
)
from backend.services.query_pagination import (
    DEFAULT_COLLECTION_LIMIT,
    MAX_COLLECTION_LIMIT,
)

router = APIRouter(prefix="/bookings", tags=["bookings"])


# Retired public/admin scaffold. Supported booking mutations are service-owned.
@router.post("", status_code=status.HTTP_410_GONE)
def create_booking(
    _current_admin: User = Depends(require_active_admin),
) -> None:
    del _current_admin
    raise_retired_mutation_route(
        code="booking_scaffold_removed",
        message=(
            "Direct booking creation is no longer supported. Use product-owned "
            "join, checkout, roster, payment, or admin workflows."
        ),
    )


@router.get("/me", response_model=list[BookingRead], status_code=status.HTTP_200_OK)
def list_my_bookings(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(
        default=DEFAULT_COLLECTION_LIMIT,
        ge=1,
        le=MAX_COLLECTION_LIMIT,
    ),
    current_user: User = Depends(get_current_app_user),
    db: Session = Depends(get_db),
) -> list[Booking]:
    return list_current_user_bookings(
        db,
        current_user,
        limit=limit,
        offset=offset,
    )


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
    offset: int = Query(default=0, ge=0),
    limit: int = Query(
        default=DEFAULT_COLLECTION_LIMIT,
        ge=1,
        le=MAX_COLLECTION_LIMIT,
    ),
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
        limit=limit,
        offset=offset,
    )


# Retired public/admin scaffold. Supported booking mutations are service-owned.
@router.patch("/{booking_id}", status_code=status.HTTP_410_GONE)
def update_booking(
    booking_id: uuid.UUID,
    _current_admin: User = Depends(require_active_admin),
) -> None:
    del booking_id, _current_admin
    raise_retired_mutation_route(
        code="booking_scaffold_removed",
        message=(
            "Direct booking updates are no longer supported. Use product-owned "
            "join, checkout, roster, payment, or admin workflows."
        ),
    )
