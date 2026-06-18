import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import BookingStatusHistory, User
from backend.schemas import (
    BookingStatusHistoryCreate,
    BookingStatusHistoryRead,
    BookingStatusHistoryUpdate,
)
from backend.services.admin_permission_service import (
    PERMISSION_MONEY_PAYMENT_MANAGE,
    PERMISSION_MONEY_READ,
)
from backend.services.auth_service import require_admin_permission
from backend.services.status_history_service import (
    create_booking_status_history_record,
    get_booking_status_history_record,
    list_booking_status_history_records,
    update_booking_status_history_record,
)

router = APIRouter(prefix="/booking-status-history", tags=["booking_status_history"])


@router.post(
    "",
    response_model=BookingStatusHistoryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_booking_status_history(
    booking_status_history: BookingStatusHistoryCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_MONEY_PAYMENT_MANAGE)
    ),
) -> BookingStatusHistory:
    del current_admin
    return create_booking_status_history_record(db, booking_status_history)


@router.get(
    "/{history_id}",
    response_model=BookingStatusHistoryRead,
    status_code=status.HTTP_200_OK,
)
def get_booking_status_history(
    history_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_permission(PERMISSION_MONEY_READ)),
) -> BookingStatusHistory:
    del current_admin
    return get_booking_status_history_record(db, history_id)


@router.get(
    "",
    response_model=list[BookingStatusHistoryRead],
    status_code=status.HTTP_200_OK,
)
def list_booking_status_history(
    booking_id: uuid.UUID | None = None,
    changed_by_user_id: uuid.UUID | None = None,
    change_source: str | None = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_permission(PERMISSION_MONEY_READ)),
) -> list[BookingStatusHistory]:
    del current_admin
    return list_booking_status_history_records(
        db,
        booking_id=booking_id,
        changed_by_user_id=changed_by_user_id,
        change_source=change_source,
    )


@router.patch(
    "/{history_id}",
    response_model=BookingStatusHistoryRead,
    status_code=status.HTTP_200_OK,
)
def update_booking_status_history(
    history_id: uuid.UUID,
    history_update: BookingStatusHistoryUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_MONEY_PAYMENT_MANAGE)
    ),
) -> BookingStatusHistory:
    del current_admin
    return update_booking_status_history_record(db, history_id, history_update)
