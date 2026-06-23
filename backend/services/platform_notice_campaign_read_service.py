"""Read helpers and shared rules for platform notice campaigns."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models import (
    PlatformNoticeCampaign,
    PlatformNoticeCampaignDelivery,
    PlatformNoticeCampaignTargetUser,
)
from backend.schemas.platform_notice_campaign_schema import (
    PlatformNoticeCampaignDeliverySummary,
    PlatformNoticeCampaignRead,
)


def normalize_choice(
    value: str,
    *,
    field_name: str,
    allowed_values: set[str],
) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in allowed_values:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} is not supported.",
        )
    return normalized


def normalize_idempotency_key(value: str) -> str:
    normalized = str(value or "").strip()
    if len(normalized) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="idempotency_key must be at least 8 characters.",
        )
    if len(normalized) > 160:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="idempotency_key must be 160 characters or fewer.",
        )
    return normalized


def campaign_target_user_ids(
    db: Session,
    campaign_id: uuid.UUID,
) -> list[uuid.UUID]:
    return sorted(
        db.scalars(
            select(PlatformNoticeCampaignTargetUser.user_id).where(
                PlatformNoticeCampaignTargetUser.campaign_id == campaign_id
            )
        ).all(),
        key=str,
    )


def serialize_campaign(
    campaign: PlatformNoticeCampaign,
    target_user_ids: list[uuid.UUID],
    delivery_summary: PlatformNoticeCampaignDeliverySummary | None = None,
) -> PlatformNoticeCampaignRead:
    return PlatformNoticeCampaignRead(
        id=campaign.id,
        campaign_status=campaign.campaign_status,
        audience_type=campaign.audience_type,
        delivery_class=campaign.delivery_class,
        internal_name=campaign.internal_name,
        title=campaign.title,
        summary=campaign.summary,
        body=campaign.body,
        target_user_ids=target_user_ids,
        target_user_count=len(target_user_ids),
        delivery_summary=delivery_summary
        or PlatformNoticeCampaignDeliverySummary(),
        created_by_user_id=campaign.created_by_user_id,
        updated_by_user_id=campaign.updated_by_user_id,
        first_sent_at=campaign.first_sent_at,
        completed_at=campaign.completed_at,
        last_attempt_at=campaign.last_attempt_at,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )


def campaign_delivery_summaries(
    db: Session,
    campaign_ids: list[uuid.UUID],
) -> dict[uuid.UUID, PlatformNoticeCampaignDeliverySummary]:
    summaries = {
        campaign_id: PlatformNoticeCampaignDeliverySummary()
        for campaign_id in campaign_ids
    }
    if not campaign_ids:
        return summaries

    rows = db.execute(
        select(
            PlatformNoticeCampaignDelivery.campaign_id,
            PlatformNoticeCampaignDelivery.delivery_status,
            func.count(),
        )
        .where(PlatformNoticeCampaignDelivery.campaign_id.in_(campaign_ids))
        .group_by(
            PlatformNoticeCampaignDelivery.campaign_id,
            PlatformNoticeCampaignDelivery.delivery_status,
        )
    ).all()
    for campaign_id, delivery_status, row_count in rows:
        summary = summaries[campaign_id]
        summary.targeted_count += row_count
        if delivery_status == "delivered":
            summary.delivered_count += row_count
        elif delivery_status == "skipped":
            summary.skipped_count += row_count
        elif delivery_status == "failed":
            summary.failed_count += row_count
    return summaries


def campaign_delivery_summary(
    db: Session,
    campaign_id: uuid.UUID,
) -> PlatformNoticeCampaignDeliverySummary:
    return campaign_delivery_summaries(db, [campaign_id])[campaign_id]
