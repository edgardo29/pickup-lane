import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import HostPublishFee, User
from backend.routes.retired_route_helpers import raise_retired_mutation_route
from backend.schemas import (
    HostPublishFeeRead,
)
from backend.services.auth_service import require_active_user, require_active_admin
from backend.services.host_publish_fee_service import (
    get_host_publish_fee_record,
    list_current_host_publish_fee_records,
    list_host_publish_fee_records,
)
from backend.services.query_pagination import (
    DEFAULT_ADMIN_COLLECTION_LIMIT,
    DEFAULT_COLLECTION_LIMIT,
    MAX_ADMIN_COLLECTION_LIMIT,
    MAX_COLLECTION_LIMIT,
)

router = APIRouter(prefix="/host-publish-fees", tags=["host_publish_fees"])


@router.post(
    "",
    status_code=status.HTTP_410_GONE,
)
def create_host_publish_fee(
    current_admin: User = Depends(require_active_admin),
) -> None:
    del current_admin
    raise_retired_mutation_route(
        code="host_publish_fee_scaffold_removed",
        message=(
            "Direct host publish fee creation is no longer supported. Use "
            "product-owned publish and payment workflows."
        ),
    )


@router.get(
    "/me",
    response_model=list[HostPublishFeeRead],
    status_code=status.HTTP_200_OK,
)
def list_my_host_publish_fees(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=DEFAULT_COLLECTION_LIMIT, ge=1, le=MAX_COLLECTION_LIMIT),
    current_user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
) -> list[HostPublishFee]:
    return list_current_host_publish_fee_records(
        db,
        current_user=current_user,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{host_publish_fee_id}",
    response_model=HostPublishFeeRead,
    status_code=status.HTTP_200_OK,
)
def get_host_publish_fee(
    host_publish_fee_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
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
    offset: int = Query(default=0, ge=0),
    limit: int = Query(
        default=DEFAULT_ADMIN_COLLECTION_LIMIT,
        ge=1,
        le=MAX_ADMIN_COLLECTION_LIMIT,
    ),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_active_admin),
) -> list[HostPublishFee]:
    del current_admin
    return list_host_publish_fee_records(
        db,
        game_id=game_id,
        host_user_id=host_user_id,
        fee_status=fee_status,
        limit=limit,
        offset=offset,
    )


@router.patch(
    "/{host_publish_fee_id}",
    status_code=status.HTTP_410_GONE,
)
def update_host_publish_fee(
    host_publish_fee_id: uuid.UUID,
    current_admin: User = Depends(require_active_admin),
) -> None:
    del host_publish_fee_id, current_admin
    raise_retired_mutation_route(
        code="host_publish_fee_scaffold_removed",
        message=(
            "Direct host publish fee updates are no longer supported. Use "
            "product-owned publish and payment workflows."
        ),
    )
