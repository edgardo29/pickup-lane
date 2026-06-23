"""Draft platform notice campaign authoring workflows."""

import hashlib
import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    PlatformNoticeCampaign,
    PlatformNoticeCampaignDelivery,
    PlatformNoticeCampaignTargetUser,
    User,
)
from backend.schemas.platform_notice_campaign_schema import (
    PlatformNoticeCampaignCreate,
    PlatformNoticeCampaignDeliverySummary,
    PlatformNoticeCampaignListRead,
    PlatformNoticeCampaignRead,
    PlatformNoticeCampaignUpdate,
)
from backend.services.admin_action_service import record_admin_action
from backend.services.admin_permission_service import PERMISSION_NOTIFICATIONS_MANAGE
from backend.services.auth_service import require_user_admin_permission

CAMPAIGN_STATUSES = {
    "draft",
    "sending",
    "completed",
    "completed_with_failures",
    "failed",
    "cancelled",
}
AUDIENCE_TYPES = {"all_active_users", "selected_users"}
DELIVERY_CLASSES = {"mandatory", "preference_controlled"}
MAX_SELECTED_USERS = 500
MAX_SEARCH_LENGTH = 200


def normalize_single_line_text(
    value: str,
    *,
    field_name: str,
    max_length: int,
) -> str:
    normalized = " ".join(str(value or "").strip().split())
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} is required.",
        )
    if len(normalized) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be {max_length} characters or fewer.",
        )
    return normalized


def normalize_body(value: str) -> str:
    normalized = str(value or "").replace("\r\n", "\n").strip()
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="body is required.",
        )
    if len(normalized) > 4000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="body must be 4000 characters or fewer.",
        )
    return normalized


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


def normalize_target_user_ids(user_ids: list[uuid.UUID] | None) -> list[uuid.UUID]:
    normalized = sorted(set(user_ids or []), key=str)
    if len(normalized) > MAX_SELECTED_USERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"target_user_ids cannot contain more than {MAX_SELECTED_USERS} users.",
        )
    return normalized


def validate_audience(
    audience_type: str,
    target_user_ids: list[uuid.UUID],
) -> None:
    if audience_type == "all_active_users" and target_user_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="all_active_users campaigns cannot include target_user_ids.",
        )
    if audience_type == "selected_users" and not target_user_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="selected_users campaigns require at least one target user.",
        )


def validate_active_target_users(
    db: Session,
    target_user_ids: list[uuid.UUID],
) -> None:
    if not target_user_ids:
        return

    active_user_ids = set(
        db.scalars(
            select(User.id).where(
                User.id.in_(target_user_ids),
                User.account_status == "active",
                User.deleted_at.is_(None),
            )
        ).all()
    )
    unavailable_user_ids = set(target_user_ids) - active_user_ids
    if unavailable_user_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All selected target users must have active accounts.",
        )


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


def get_campaign_or_404(
    db: Session,
    campaign_id: uuid.UUID,
) -> PlatformNoticeCampaign:
    campaign = db.get(PlatformNoticeCampaign, campaign_id)
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Platform notice campaign not found.",
        )
    return campaign


def get_existing_campaign_by_idempotency_key(
    db: Session,
    *,
    creator_user_id: uuid.UUID,
    idempotency_key: str,
) -> PlatformNoticeCampaign | None:
    return db.scalar(
        select(PlatformNoticeCampaign).where(
            PlatformNoticeCampaign.created_by_user_id == creator_user_id,
            PlatformNoticeCampaign.creation_idempotency_key == idempotency_key,
        )
    )


def normalized_create_values(
    payload: PlatformNoticeCampaignCreate,
) -> tuple[dict[str, str], list[uuid.UUID]]:
    audience_type = normalize_choice(
        payload.audience_type,
        field_name="audience_type",
        allowed_values=AUDIENCE_TYPES,
    )
    target_user_ids = normalize_target_user_ids(payload.target_user_ids)
    validate_audience(audience_type, target_user_ids)
    values = {
        "campaign_status": "draft",
        "audience_type": audience_type,
        "delivery_class": normalize_choice(
            payload.delivery_class,
            field_name="delivery_class",
            allowed_values=DELIVERY_CLASSES,
        ),
        "internal_name": normalize_single_line_text(
            payload.internal_name,
            field_name="internal_name",
            max_length=160,
        ),
        "title": normalize_single_line_text(
            payload.title,
            field_name="title",
            max_length=150,
        ),
        "summary": normalize_single_line_text(
            payload.summary,
            field_name="summary",
            max_length=500,
        ),
        "body": normalize_body(payload.body),
        "creation_idempotency_key": normalize_idempotency_key(
            payload.idempotency_key
        ),
    }
    values["creation_request_fingerprint"] = creation_request_fingerprint(
        values,
        target_user_ids,
    )
    return values, target_user_ids


def creation_request_fingerprint(
    values: dict[str, str],
    target_user_ids: list[uuid.UUID],
) -> str:
    fingerprint_payload = {
        field_name: values[field_name]
        for field_name in (
            "audience_type",
            "delivery_class",
            "internal_name",
            "title",
            "summary",
            "body",
        )
    }
    fingerprint_payload["target_user_ids"] = [
        str(user_id) for user_id in target_user_ids
    ]
    serialized_payload = json.dumps(
        fingerprint_payload,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized_payload.encode("utf-8")).hexdigest()


def campaign_matches_create_request(
    campaign: PlatformNoticeCampaign,
    values: dict[str, str],
) -> bool:
    return (
        campaign.creation_request_fingerprint
        == values["creation_request_fingerprint"]
    )


def return_idempotent_campaign_or_conflict(
    db: Session,
    *,
    campaign: PlatformNoticeCampaign,
    values: dict[str, str],
) -> PlatformNoticeCampaignRead:
    if not campaign_matches_create_request(campaign, values):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="idempotency_key was already used for a different campaign.",
        )
    return serialize_campaign(
        campaign,
        campaign_target_user_ids(db, campaign.id),
        campaign_delivery_summary(db, campaign.id),
    )


def create_platform_notice_campaign(
    db: Session,
    *,
    creator_user: User,
    payload: PlatformNoticeCampaignCreate,
) -> PlatformNoticeCampaignRead:
    require_user_admin_permission(creator_user, PERMISSION_NOTIFICATIONS_MANAGE)
    values, target_user_ids = normalized_create_values(payload)

    existing_campaign = get_existing_campaign_by_idempotency_key(
        db,
        creator_user_id=creator_user.id,
        idempotency_key=values["creation_idempotency_key"],
    )
    if existing_campaign is not None:
        return return_idempotent_campaign_or_conflict(
            db,
            campaign=existing_campaign,
            values=values,
        )

    validate_active_target_users(db, target_user_ids)
    now = datetime.now(timezone.utc)
    campaign = PlatformNoticeCampaign(
        id=uuid.uuid4(),
        **values,
        created_by_user_id=creator_user.id,
        updated_by_user_id=creator_user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(campaign)

    try:
        # admin_actions and support_flags have an existing FK cycle, so flush
        # the new campaign before staging its audit row.
        db.flush()
        for user_id in target_user_ids:
            db.add(
                PlatformNoticeCampaignTargetUser(
                    campaign_id=campaign.id,
                    user_id=user_id,
                    created_at=now,
                )
            )

        record_admin_action(
            db,
            admin_user_id=creator_user.id,
            action_type="create_platform_notice_campaign",
            target_platform_notice_campaign_id=campaign.id,
            idempotency_key=values["creation_idempotency_key"],
            created_at=now,
            metadata={
                "campaign_status": campaign.campaign_status,
                "audience_type": campaign.audience_type,
                "delivery_class": campaign.delivery_class,
                "selected_user_count": len(target_user_ids),
            },
        )
        db.commit()
        db.refresh(campaign)
    except IntegrityError as exc:
        db.rollback()
        existing_campaign = get_existing_campaign_by_idempotency_key(
            db,
            creator_user_id=creator_user.id,
            idempotency_key=values["creation_idempotency_key"],
        )
        if existing_campaign is not None:
            return return_idempotent_campaign_or_conflict(
                db,
                campaign=existing_campaign,
                values=values,
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Platform notice campaign could not be created.",
        ) from exc

    return serialize_campaign(campaign, target_user_ids)


def list_platform_notice_campaigns(
    db: Session,
    *,
    viewer_user: User,
    campaign_status: str | None = None,
    audience_type: str | None = None,
    delivery_class: str | None = None,
    search: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> PlatformNoticeCampaignListRead:
    require_user_admin_permission(viewer_user, PERMISSION_NOTIFICATIONS_MANAGE)
    filters = []
    if campaign_status is not None:
        filters.append(
            PlatformNoticeCampaign.campaign_status
            == normalize_choice(
                campaign_status,
                field_name="campaign_status",
                allowed_values=CAMPAIGN_STATUSES,
            )
        )
    if audience_type is not None:
        filters.append(
            PlatformNoticeCampaign.audience_type
            == normalize_choice(
                audience_type,
                field_name="audience_type",
                allowed_values=AUDIENCE_TYPES,
            )
        )
    if delivery_class is not None:
        filters.append(
            PlatformNoticeCampaign.delivery_class
            == normalize_choice(
                delivery_class,
                field_name="delivery_class",
                allowed_values=DELIVERY_CLASSES,
            )
        )
    if search is not None:
        normalized_search = " ".join(search.strip().split())
        if len(normalized_search) > MAX_SEARCH_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"search must be {MAX_SEARCH_LENGTH} characters or fewer.",
            )
        if normalized_search:
            search_pattern = f"%{normalized_search}%"
            filters.append(
                or_(
                    PlatformNoticeCampaign.internal_name.ilike(search_pattern),
                    PlatformNoticeCampaign.title.ilike(search_pattern),
                )
            )

    campaign_ids_query = (
        select(PlatformNoticeCampaign)
        .where(*filters)
        .order_by(
            PlatformNoticeCampaign.created_at.desc(),
            PlatformNoticeCampaign.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    )
    campaigns = list(db.scalars(campaign_ids_query).all())
    total_count = db.scalar(
        select(func.count())
        .select_from(PlatformNoticeCampaign)
        .where(*filters)
    ) or 0

    target_ids_by_campaign: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
    campaign_ids = [campaign.id for campaign in campaigns]
    if campaigns:
        target_rows = db.execute(
            select(
                PlatformNoticeCampaignTargetUser.campaign_id,
                PlatformNoticeCampaignTargetUser.user_id,
            )
            .where(
                PlatformNoticeCampaignTargetUser.campaign_id.in_(
                    campaign_ids
                )
            )
            .order_by(
                PlatformNoticeCampaignTargetUser.campaign_id,
                PlatformNoticeCampaignTargetUser.user_id,
            )
        ).all()
        for campaign_id, user_id in target_rows:
            target_ids_by_campaign[campaign_id].append(user_id)
    delivery_summaries = campaign_delivery_summaries(db, campaign_ids)

    return PlatformNoticeCampaignListRead(
        campaigns=[
            serialize_campaign(
                campaign,
                target_ids_by_campaign.get(campaign.id, []),
                delivery_summaries[campaign.id],
            )
            for campaign in campaigns
        ],
        total_count=total_count,
        offset=offset,
        limit=limit,
    )


def get_platform_notice_campaign(
    db: Session,
    *,
    campaign_id: uuid.UUID,
    viewer_user: User,
) -> PlatformNoticeCampaignRead:
    require_user_admin_permission(viewer_user, PERMISSION_NOTIFICATIONS_MANAGE)
    campaign = get_campaign_or_404(db, campaign_id)
    return serialize_campaign(
        campaign,
        campaign_target_user_ids(db, campaign.id),
        campaign_delivery_summary(db, campaign.id),
    )


def campaign_snapshot(
    campaign: PlatformNoticeCampaign,
    *,
    selected_user_count: int,
) -> dict[str, object]:
    return {
        "campaign_status": campaign.campaign_status,
        "audience_type": campaign.audience_type,
        "delivery_class": campaign.delivery_class,
        "selected_user_count": selected_user_count,
    }


def update_platform_notice_campaign(
    db: Session,
    *,
    campaign_id: uuid.UUID,
    editor_user: User,
    payload: PlatformNoticeCampaignUpdate,
) -> PlatformNoticeCampaignRead:
    require_user_admin_permission(editor_user, PERMISSION_NOTIFICATIONS_MANAGE)
    campaign = get_campaign_or_404(db, campaign_id)
    if campaign.campaign_status != "draft":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only draft platform notice campaigns can be edited.",
        )

    update_data = payload.model_dump(exclude_unset=True)
    existing_target_user_ids = campaign_target_user_ids(db, campaign.id)
    before = campaign_snapshot(
        campaign,
        selected_user_count=len(existing_target_user_ids),
    )

    effective_audience_type = campaign.audience_type
    if "audience_type" in update_data:
        effective_audience_type = normalize_choice(
            update_data["audience_type"],
            field_name="audience_type",
            allowed_values=AUDIENCE_TYPES,
        )

    targets_were_provided = "target_user_ids" in update_data
    effective_target_user_ids = (
        normalize_target_user_ids(update_data.get("target_user_ids"))
        if targets_were_provided
        else existing_target_user_ids
    )
    if effective_audience_type == "all_active_users":
        if targets_were_provided and effective_target_user_ids:
            validate_audience(effective_audience_type, effective_target_user_ids)
        effective_target_user_ids = []
    elif campaign.audience_type != effective_audience_type and not targets_were_provided:
        effective_target_user_ids = []

    validate_audience(effective_audience_type, effective_target_user_ids)
    if targets_were_provided or campaign.audience_type != effective_audience_type:
        validate_active_target_users(db, effective_target_user_ids)

    normalized_updates: dict[str, str] = {
        "audience_type": effective_audience_type,
    }
    if "delivery_class" in update_data:
        normalized_updates["delivery_class"] = normalize_choice(
            update_data["delivery_class"],
            field_name="delivery_class",
            allowed_values=DELIVERY_CLASSES,
        )
    if "internal_name" in update_data:
        normalized_updates["internal_name"] = normalize_single_line_text(
            update_data["internal_name"],
            field_name="internal_name",
            max_length=160,
        )
    if "title" in update_data:
        normalized_updates["title"] = normalize_single_line_text(
            update_data["title"],
            field_name="title",
            max_length=150,
        )
    if "summary" in update_data:
        normalized_updates["summary"] = normalize_single_line_text(
            update_data["summary"],
            field_name="summary",
            max_length=500,
        )
    if "body" in update_data:
        normalized_updates["body"] = normalize_body(update_data["body"])

    changed_fields = [
        field_name
        for field_name, field_value in normalized_updates.items()
        if getattr(campaign, field_name) != field_value
    ]
    if effective_target_user_ids != existing_target_user_ids:
        changed_fields.append("target_user_ids")
    if not changed_fields:
        return serialize_campaign(
            campaign,
            existing_target_user_ids,
            campaign_delivery_summary(db, campaign.id),
        )

    now = datetime.now(timezone.utc)
    for field_name, field_value in normalized_updates.items():
        setattr(campaign, field_name, field_value)
    campaign.updated_by_user_id = editor_user.id
    campaign.updated_at = now
    db.add(campaign)

    if effective_target_user_ids != existing_target_user_ids:
        db.execute(
            delete(PlatformNoticeCampaignTargetUser).where(
                PlatformNoticeCampaignTargetUser.campaign_id == campaign.id
            )
        )
        for user_id in effective_target_user_ids:
            db.add(
                PlatformNoticeCampaignTargetUser(
                    campaign_id=campaign.id,
                    user_id=user_id,
                    created_at=now,
                )
            )

    after = campaign_snapshot(
        campaign,
        selected_user_count=len(effective_target_user_ids),
    )
    record_admin_action(
        db,
        admin_user_id=editor_user.id,
        action_type="update_platform_notice_campaign",
        target_platform_notice_campaign_id=campaign.id,
        created_at=now,
        metadata={
            "changed_fields": sorted(changed_fields),
            "before": before,
            "after": after,
        },
    )

    try:
        db.commit()
        db.refresh(campaign)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Platform notice campaign could not be updated.",
        ) from exc

    return serialize_campaign(
        campaign,
        effective_target_user_ids,
        campaign_delivery_summary(db, campaign.id),
    )
