import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas import (
    PlatformNoticeCampaignAttemptListRead,
    PlatformNoticeCampaignCreate,
    PlatformNoticeCampaignDeliveryListRead,
    PlatformNoticeCampaignDeliveryRequest,
    PlatformNoticeCampaignDeliveryResult,
    PlatformNoticeCampaignListRead,
    PlatformNoticeCampaignRead,
    PlatformNoticeCampaignUpdate,
)
from backend.services.admin_permission_service import PERMISSION_NOTIFICATIONS_MANAGE
from backend.services.auth_service import require_admin_permission
from backend.services.platform_notice_campaign_service import (
    create_platform_notice_campaign,
    get_platform_notice_campaign,
    list_platform_notice_campaigns,
    update_platform_notice_campaign,
)
from backend.services.platform_notice_delivery_service import (
    list_platform_notice_campaign_attempts,
    list_platform_notice_campaign_deliveries,
    retry_failed_platform_notice_campaign,
    send_platform_notice_campaign,
)

router = APIRouter(
    prefix="/admin/platform-notice-campaigns",
    tags=["platform_notice_campaigns"],
)


@router.post(
    "",
    response_model=PlatformNoticeCampaignRead,
    status_code=status.HTTP_201_CREATED,
)
def create_platform_notice_campaign_route(
    payload: PlatformNoticeCampaignCreate,
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_NOTIFICATIONS_MANAGE)
    ),
    db: Session = Depends(get_db),
) -> PlatformNoticeCampaignRead:
    return create_platform_notice_campaign(
        db,
        creator_user=current_admin,
        payload=payload,
    )


@router.get(
    "",
    response_model=PlatformNoticeCampaignListRead,
    status_code=status.HTTP_200_OK,
)
def list_platform_notice_campaigns_route(
    campaign_status: str | None = None,
    audience_type: str | None = None,
    delivery_class: str | None = None,
    search: str | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_NOTIFICATIONS_MANAGE)
    ),
    db: Session = Depends(get_db),
) -> PlatformNoticeCampaignListRead:
    return list_platform_notice_campaigns(
        db,
        viewer_user=current_admin,
        campaign_status=campaign_status,
        audience_type=audience_type,
        delivery_class=delivery_class,
        search=search,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{campaign_id}",
    response_model=PlatformNoticeCampaignRead,
    status_code=status.HTTP_200_OK,
)
def get_platform_notice_campaign_route(
    campaign_id: uuid.UUID,
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_NOTIFICATIONS_MANAGE)
    ),
    db: Session = Depends(get_db),
) -> PlatformNoticeCampaignRead:
    return get_platform_notice_campaign(
        db,
        campaign_id=campaign_id,
        viewer_user=current_admin,
    )


@router.patch(
    "/{campaign_id}",
    response_model=PlatformNoticeCampaignRead,
    status_code=status.HTTP_200_OK,
)
def update_platform_notice_campaign_route(
    campaign_id: uuid.UUID,
    payload: PlatformNoticeCampaignUpdate,
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_NOTIFICATIONS_MANAGE)
    ),
    db: Session = Depends(get_db),
) -> PlatformNoticeCampaignRead:
    return update_platform_notice_campaign(
        db,
        campaign_id=campaign_id,
        editor_user=current_admin,
        payload=payload,
    )


@router.post(
    "/{campaign_id}/send",
    response_model=PlatformNoticeCampaignDeliveryResult,
    status_code=status.HTTP_200_OK,
)
def send_platform_notice_campaign_route(
    campaign_id: uuid.UUID,
    payload: PlatformNoticeCampaignDeliveryRequest,
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_NOTIFICATIONS_MANAGE)
    ),
    db: Session = Depends(get_db),
) -> PlatformNoticeCampaignDeliveryResult:
    return send_platform_notice_campaign(
        db,
        campaign_id=campaign_id,
        admin_user=current_admin,
        idempotency_key=payload.idempotency_key,
    )


@router.post(
    "/{campaign_id}/retry-failed",
    response_model=PlatformNoticeCampaignDeliveryResult,
    status_code=status.HTTP_200_OK,
)
def retry_failed_platform_notice_campaign_route(
    campaign_id: uuid.UUID,
    payload: PlatformNoticeCampaignDeliveryRequest,
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_NOTIFICATIONS_MANAGE)
    ),
    db: Session = Depends(get_db),
) -> PlatformNoticeCampaignDeliveryResult:
    return retry_failed_platform_notice_campaign(
        db,
        campaign_id=campaign_id,
        admin_user=current_admin,
        idempotency_key=payload.idempotency_key,
    )


@router.get(
    "/{campaign_id}/deliveries",
    response_model=PlatformNoticeCampaignDeliveryListRead,
    status_code=status.HTTP_200_OK,
)
def list_platform_notice_campaign_deliveries_route(
    campaign_id: uuid.UUID,
    delivery_status: str | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_NOTIFICATIONS_MANAGE)
    ),
    db: Session = Depends(get_db),
) -> PlatformNoticeCampaignDeliveryListRead:
    return list_platform_notice_campaign_deliveries(
        db,
        campaign_id=campaign_id,
        viewer_user=current_admin,
        delivery_status=delivery_status,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{campaign_id}/attempts",
    response_model=PlatformNoticeCampaignAttemptListRead,
    status_code=status.HTTP_200_OK,
)
def list_platform_notice_campaign_attempts_route(
    campaign_id: uuid.UUID,
    attempt_type: str | None = None,
    attempt_status: str | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    current_admin: User = Depends(
        require_admin_permission(PERMISSION_NOTIFICATIONS_MANAGE)
    ),
    db: Session = Depends(get_db),
) -> PlatformNoticeCampaignAttemptListRead:
    return list_platform_notice_campaign_attempts(
        db,
        campaign_id=campaign_id,
        viewer_user=current_admin,
        attempt_type=attempt_type,
        attempt_status=attempt_status,
        offset=offset,
        limit=limit,
    )
