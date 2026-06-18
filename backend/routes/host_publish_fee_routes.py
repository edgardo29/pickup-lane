import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import HostPublishFee, User
from backend.schemas import (
    HostPublishFeeCreate,
    HostPublishFeeRead,
    HostPublishFeeUpdate,
)
from backend.services.admin_permission_service import (
    PERMISSION_MONEY_PAYMENT_MANAGE,
    PERMISSION_MONEY_READ,
)
from backend.services.auth_service import require_active_user, require_admin_permission
from backend.services.host_publish_fee_service import (
    create_host_publish_fee_record,
    get_host_publish_fee_record,
    list_current_host_publish_fee_records,
    list_host_publish_fee_records,
    update_host_publish_fee_record,
)

router = APIRouter(prefix="/host-publish-fees", tags=["host_publish_fees"])


@router.post(
    "",
    response_model=HostPublishFeeRead,
    status_code=status.HTTP_201_CREATED,
)
def create_host_publish_fee(
    host_publish_fee: HostPublishFeeCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_MONEY_PAYMENT_MANAGE)
    ),
) -> HostPublishFee:
    del current_admin
    return create_host_publish_fee_record(db, host_publish_fee)


@router.get(
    "/me",
    response_model=list[HostPublishFeeRead],
    status_code=status.HTTP_200_OK,
)
def list_my_host_publish_fees(
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> list[HostPublishFee]:
    return list_current_host_publish_fee_records(db, current_user=current_user)


@router.get(
    "/{host_publish_fee_id}",
    response_model=HostPublishFeeRead,
    status_code=status.HTTP_200_OK,
)
def get_host_publish_fee(
    host_publish_fee_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_permission(PERMISSION_MONEY_READ)),
) -> HostPublishFee:
    del current_admin
    return get_host_publish_fee_record(db, host_publish_fee_id)


@router.get(
    "",
    response_model=list[HostPublishFeeRead],
    status_code=status.HTTP_200_OK,
)
def list_host_publish_fees(
    game_id: uuid.UUID | None = None,
    host_user_id: uuid.UUID | None = None,
    fee_status: str | None = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin_permission(PERMISSION_MONEY_READ)),
) -> list[HostPublishFee]:
    del current_admin
    return list_host_publish_fee_records(
        db,
        game_id=game_id,
        host_user_id=host_user_id,
        fee_status=fee_status,
    )


@router.patch(
    "/{host_publish_fee_id}",
    response_model=HostPublishFeeRead,
    status_code=status.HTTP_200_OK,
)
def update_host_publish_fee(
    host_publish_fee_id: uuid.UUID,
    host_publish_fee_update: HostPublishFeeUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_MONEY_PAYMENT_MANAGE)
    ),
) -> HostPublishFee:
    del current_admin
    return update_host_publish_fee_record(
        db,
        host_publish_fee_id,
        host_publish_fee_update,
    )
