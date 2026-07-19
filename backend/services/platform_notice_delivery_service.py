"""Transactional delivery workflows for platform notice campaigns."""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    Notification,
    PlatformNoticeCampaign,
    PlatformNoticeCampaignAttempt,
    PlatformNoticeCampaignDelivery,
    User,
)
from backend.schemas.platform_notice_campaign_schema import (
    PlatformNoticeCampaignAttemptListRead,
    PlatformNoticeCampaignAttemptRead,
    PlatformNoticeCampaignDeliveryListRead,
    PlatformNoticeCampaignDeliveryRead,
    PlatformNoticeCampaignDeliveryResult,
)
from backend.services.admin_action_service import record_admin_action
from backend.services.notification_event_service import build_app_notification_fields
from backend.services.platform_notice_campaign_read_service import (
    campaign_delivery_summary,
    campaign_target_user_ids,
    normalize_choice,
    normalize_idempotency_key,
    serialize_campaign,
)

DELIVERY_STATUSES = {"pending", "delivered", "skipped", "failed"}
ATTEMPT_TYPES = {"initial_send", "retry_failed"}
ATTEMPT_STATUSES = {
    "in_progress",
    "completed",
    "completed_with_failures",
    "failed",
}


def serialize_delivery(
    delivery: PlatformNoticeCampaignDelivery,
) -> PlatformNoticeCampaignDeliveryRead:
    return PlatformNoticeCampaignDeliveryRead(
        id=delivery.id,
        campaign_id=delivery.campaign_id,
        recipient_user_id=delivery.recipient_user_id,
        recipient_user_id_snapshot=delivery.recipient_user_id_snapshot,
        delivery_status=delivery.delivery_status,
        skip_reason=delivery.skip_reason,
        failure_code=delivery.failure_code,
        notification_id=delivery.notification_id,
        attempt_count=delivery.attempt_count,
        last_attempt_at=delivery.last_attempt_at,
        delivered_at=delivery.delivered_at,
        created_at=delivery.created_at,
        updated_at=delivery.updated_at,
    )


def serialize_attempt(
    attempt: PlatformNoticeCampaignAttempt,
) -> PlatformNoticeCampaignAttemptRead:
    return PlatformNoticeCampaignAttemptRead(
        id=attempt.id,
        campaign_id=attempt.campaign_id,
        attempt_type=attempt.attempt_type,
        attempt_status=attempt.attempt_status,
        idempotency_key=attempt.idempotency_key,
        targeted_count=attempt.targeted_count,
        delivered_count=attempt.delivered_count,
        skipped_count=attempt.skipped_count,
        failed_count=attempt.failed_count,
        created_by_user_id=attempt.created_by_user_id,
        started_at=attempt.started_at,
        completed_at=attempt.completed_at,
        created_at=attempt.created_at,
    )


def serialize_delivery_result(
    db: Session,
    *,
    campaign: PlatformNoticeCampaign,
    attempt: PlatformNoticeCampaignAttempt,
) -> PlatformNoticeCampaignDeliveryResult:
    return PlatformNoticeCampaignDeliveryResult(
        campaign=serialize_campaign(
            campaign,
            campaign_target_user_ids(db, campaign.id),
            campaign_delivery_summary(db, campaign.id),
        ),
        attempt=serialize_attempt(attempt),
    )


def get_campaign_for_update_or_404(
    db: Session,
    campaign_id: uuid.UUID,
) -> PlatformNoticeCampaign:
    campaign = db.scalar(
        select(PlatformNoticeCampaign)
        .where(PlatformNoticeCampaign.id == campaign_id)
        .with_for_update()
    )
    if campaign is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Platform notice campaign not found.",
        )
    return campaign


def recipient_skip_reason(user: User | None) -> str | None:
    if user is None or user.deleted_at is not None or user.account_status == "deleted":
        return "deleted"
    if user.account_status == "suspended":
        return "suspended"
    if user.account_status == "pending_deletion":
        return "pending_deletion"
    if user.account_status != "active":
        return "inactive"
    return None


def campaign_notification_aggregation_key(
    campaign_id: uuid.UUID,
    user_id: uuid.UUID,
) -> str:
    return f"admin_notice:campaign:{campaign_id}:user:{user_id}"


def create_or_get_campaign_notification(
    db: Session,
    *,
    campaign: PlatformNoticeCampaign,
    recipient_user_id: uuid.UUID,
    event_at: datetime,
) -> Notification:
    aggregation_key = campaign_notification_aggregation_key(
        campaign.id,
        recipient_user_id,
    )
    existing_notification = db.scalar(
        select(Notification).where(
            Notification.user_id == recipient_user_id,
            Notification.aggregation_key == aggregation_key,
        )
    )
    if existing_notification is not None:
        return existing_notification

    notification_fields = build_app_notification_fields(
        "admin_notice",
        event_at=event_at,
        source_type="pickup_lane",
        subject_label="Pickup Lane",
        title=campaign.title,
        summary=campaign.summary,
        body=campaign.body,
        force_action_null=True,
    )
    notification_fields["aggregation_key"] = aggregation_key
    notification = Notification(
        id=uuid.uuid4(),
        user_id=recipient_user_id,
        notification_type="admin_notice",
        notification_category="app",
        notification_domain="admin",
        actor_user_id=None,
        is_read=False,
        read_at=None,
        created_at=event_at,
        updated_at=event_at,
        **notification_fields,
    )
    db.add(notification)
    return notification


def initial_recipient_ids(
    db: Session,
    campaign: PlatformNoticeCampaign,
) -> list[uuid.UUID]:
    if campaign.audience_type == "selected_users":
        return campaign_target_user_ids(db, campaign.id)
    return list(
        db.scalars(
            select(User.id)
            .where(
                User.account_status == "active",
                User.deleted_at.is_(None),
            )
            .order_by(User.id)
        ).all()
    )


def create_initial_deliveries(
    db: Session,
    *,
    campaign: PlatformNoticeCampaign,
    created_at: datetime,
) -> list[PlatformNoticeCampaignDelivery]:
    existing_count = db.scalar(
        select(func.count())
        .select_from(PlatformNoticeCampaignDelivery)
        .where(PlatformNoticeCampaignDelivery.campaign_id == campaign.id)
    ) or 0
    if existing_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Campaign already has a recipient snapshot.",
        )

    deliveries = [
        PlatformNoticeCampaignDelivery(
            id=uuid.uuid4(),
            campaign_id=campaign.id,
            recipient_user_id=user_id,
            recipient_user_id_snapshot=user_id,
            delivery_status="pending",
            attempt_count=0,
            created_at=created_at,
            updated_at=created_at,
        )
        for user_id in initial_recipient_ids(db, campaign)
    ]
    db.add_all(deliveries)
    return deliveries


def failed_deliveries(
    db: Session,
    campaign_id: uuid.UUID,
) -> list[PlatformNoticeCampaignDelivery]:
    return list(
        db.scalars(
            select(PlatformNoticeCampaignDelivery)
            .where(
                PlatformNoticeCampaignDelivery.campaign_id == campaign_id,
                PlatformNoticeCampaignDelivery.delivery_status == "failed",
            )
            .order_by(
                PlatformNoticeCampaignDelivery.created_at,
                PlatformNoticeCampaignDelivery.id,
            )
        ).all()
    )


def attempt_status_for_counts(
    *,
    delivered_count: int,
    failed_count: int,
) -> str:
    if not failed_count:
        return "completed"
    if delivered_count:
        return "completed_with_failures"
    return "failed"


def campaign_status_for_summary(
    *,
    delivered_count: int,
    failed_count: int,
) -> str:
    if not failed_count:
        return "completed"
    if delivered_count:
        return "completed_with_failures"
    return "failed"


def failure_code_for_exception(exc: Exception) -> str:
    if isinstance(exc, IntegrityError):
        return "notification_conflict"
    return "delivery_error"


def process_delivery(
    db: Session,
    *,
    campaign: PlatformNoticeCampaign,
    delivery: PlatformNoticeCampaignDelivery,
    attempted_at: datetime,
) -> str:
    user = db.get(User, delivery.recipient_user_id_snapshot)
    skip_reason = recipient_skip_reason(user)
    if skip_reason is not None:
        delivery.recipient_user_id = user.id if user is not None else None
        delivery.delivery_status = "skipped"
        delivery.skip_reason = skip_reason
        delivery.failure_code = None
        delivery.notification_id = None
        delivery.delivered_at = None
        delivery.updated_at = attempted_at
        db.add(delivery)
        return "skipped"

    delivery.recipient_user_id = user.id
    delivery.delivery_status = "pending"
    delivery.skip_reason = None
    delivery.failure_code = None
    delivery.notification_id = None
    delivery.delivered_at = None
    delivery.attempt_count += 1
    delivery.last_attempt_at = attempted_at
    delivery.updated_at = attempted_at
    db.add(delivery)

    try:
        with db.begin_nested():
            notification = create_or_get_campaign_notification(
                db,
                campaign=campaign,
                recipient_user_id=user.id,
                event_at=attempted_at,
            )
            db.flush()
            notification_id = notification.id
    except Exception as exc:
        delivery.delivery_status = "failed"
        delivery.failure_code = failure_code_for_exception(exc)
        delivery.updated_at = attempted_at
        db.add(delivery)
        return "failed"

    delivery.delivery_status = "delivered"
    delivery.failure_code = None
    delivery.notification_id = notification_id
    delivery.delivered_at = attempted_at
    delivery.updated_at = attempted_at
    db.add(delivery)
    return "delivered"


def get_existing_attempt(
    db: Session,
    *,
    campaign_id: uuid.UUID,
    idempotency_key: str,
) -> PlatformNoticeCampaignAttempt | None:
    return db.scalar(
        select(PlatformNoticeCampaignAttempt).where(
            PlatformNoticeCampaignAttempt.campaign_id == campaign_id,
            PlatformNoticeCampaignAttempt.idempotency_key == idempotency_key,
        )
    )


def run_delivery_attempt(
    db: Session,
    *,
    campaign_id: uuid.UUID,
    admin_user: User,
    idempotency_key: str,
    attempt_type: str,
) -> PlatformNoticeCampaignDeliveryResult:
    normalized_key = normalize_idempotency_key(idempotency_key)
    campaign = get_campaign_for_update_or_404(db, campaign_id)

    existing_attempt = get_existing_attempt(
        db,
        campaign_id=campaign.id,
        idempotency_key=normalized_key,
    )
    if existing_attempt is not None:
        if existing_attempt.attempt_type != attempt_type:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="idempotency_key was already used for a different delivery operation.",
            )
        return serialize_delivery_result(
            db,
            campaign=campaign,
            attempt=existing_attempt,
        )

    now = datetime.now(timezone.utc)
    if attempt_type == "initial_send":
        if campaign.campaign_status != "draft":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only draft platform notice campaigns can be sent.",
            )
        deliveries = create_initial_deliveries(
            db,
            campaign=campaign,
            created_at=now,
        )
        campaign.first_sent_at = now
    else:
        if campaign.campaign_status in {"draft", "sending", "cancelled"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Campaign is not eligible for failed-delivery retry.",
            )
        deliveries = failed_deliveries(db, campaign.id)
        if not deliveries:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Campaign has no failed deliveries to retry.",
            )

    attempt = PlatformNoticeCampaignAttempt(
        id=uuid.uuid4(),
        campaign_id=campaign.id,
        attempt_type=attempt_type,
        attempt_status="in_progress",
        idempotency_key=normalized_key,
        targeted_count=len(deliveries),
        delivered_count=0,
        skipped_count=0,
        failed_count=0,
        created_by_user_id=admin_user.id,
        started_at=now,
        completed_at=None,
        created_at=now,
    )
    db.add(attempt)
    campaign.campaign_status = "sending"
    campaign.last_attempt_at = now
    campaign.completed_at = None
    campaign.updated_by_user_id = admin_user.id
    campaign.updated_at = now
    db.add(campaign)
    db.flush()

    result_counts = {"delivered": 0, "skipped": 0, "failed": 0}
    for delivery in deliveries:
        outcome = process_delivery(
            db,
            campaign=campaign,
            delivery=delivery,
            attempted_at=now,
        )
        result_counts[outcome] += 1

    attempt.delivered_count = result_counts["delivered"]
    attempt.skipped_count = result_counts["skipped"]
    attempt.failed_count = result_counts["failed"]
    attempt.attempt_status = attempt_status_for_counts(
        delivered_count=attempt.delivered_count,
        failed_count=attempt.failed_count,
    )
    attempt.completed_at = now
    db.add(attempt)
    db.flush()

    summary = campaign_delivery_summary(db, campaign.id)
    campaign.campaign_status = campaign_status_for_summary(
        delivered_count=summary.delivered_count,
        failed_count=summary.failed_count,
    )
    campaign.completed_at = now
    campaign.updated_at = now
    db.add(campaign)

    action_type = (
        "send_platform_notice_campaign"
        if attempt_type == "initial_send"
        else "retry_platform_notice_campaign"
    )
    record_admin_action(
        db,
        admin_user_id=admin_user.id,
        action_type=action_type,
        target_platform_notice_campaign_id=campaign.id,
        idempotency_key=normalized_key,
        created_at=now,
        metadata={
            "attempt_id": str(attempt.id),
            "attempt_type": attempt.attempt_type,
            "campaign_status": campaign.campaign_status,
            "targeted_count": attempt.targeted_count,
            "delivered_count": attempt.delivered_count,
            "skipped_count": attempt.skipped_count,
            "failed_count": attempt.failed_count,
        },
    )

    try:
        db.commit()
        db.refresh(campaign)
        db.refresh(attempt)
    except IntegrityError as exc:
        db.rollback()
        replay_attempt = get_existing_attempt(
            db,
            campaign_id=campaign_id,
            idempotency_key=normalized_key,
        )
        if replay_attempt is not None and replay_attempt.attempt_type == attempt_type:
            replay_campaign = db.get(PlatformNoticeCampaign, campaign_id)
            if replay_campaign is not None:
                return serialize_delivery_result(
                    db,
                    campaign=replay_campaign,
                    attempt=replay_attempt,
                )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Platform notice delivery attempt could not be completed.",
        ) from exc

    return serialize_delivery_result(db, campaign=campaign, attempt=attempt)


def send_platform_notice_campaign(
    db: Session,
    *,
    campaign_id: uuid.UUID,
    admin_user: User,
    idempotency_key: str,
) -> PlatformNoticeCampaignDeliveryResult:
    return run_delivery_attempt(
        db,
        campaign_id=campaign_id,
        admin_user=admin_user,
        idempotency_key=idempotency_key,
        attempt_type="initial_send",
    )


def retry_failed_platform_notice_campaign(
    db: Session,
    *,
    campaign_id: uuid.UUID,
    admin_user: User,
    idempotency_key: str,
) -> PlatformNoticeCampaignDeliveryResult:
    return run_delivery_attempt(
        db,
        campaign_id=campaign_id,
        admin_user=admin_user,
        idempotency_key=idempotency_key,
        attempt_type="retry_failed",
    )


def list_platform_notice_campaign_deliveries(
    db: Session,
    *,
    campaign_id: uuid.UUID,
    viewer_user: User,
    delivery_status: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> PlatformNoticeCampaignDeliveryListRead:
    if db.get(PlatformNoticeCampaign, campaign_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Platform notice campaign not found.",
        )

    filters = [PlatformNoticeCampaignDelivery.campaign_id == campaign_id]
    if delivery_status is not None:
        filters.append(
            PlatformNoticeCampaignDelivery.delivery_status
            == normalize_choice(
                delivery_status,
                field_name="delivery_status",
                allowed_values=DELIVERY_STATUSES,
            )
        )
    deliveries = list(
        db.scalars(
            select(PlatformNoticeCampaignDelivery)
            .where(*filters)
            .order_by(
                PlatformNoticeCampaignDelivery.created_at,
                PlatformNoticeCampaignDelivery.id,
            )
            .offset(offset)
            .limit(limit)
        ).all()
    )
    total_count = db.scalar(
        select(func.count())
        .select_from(PlatformNoticeCampaignDelivery)
        .where(*filters)
    ) or 0
    return PlatformNoticeCampaignDeliveryListRead(
        deliveries=[serialize_delivery(delivery) for delivery in deliveries],
        total_count=total_count,
        offset=offset,
        limit=limit,
    )


def list_platform_notice_campaign_attempts(
    db: Session,
    *,
    campaign_id: uuid.UUID,
    viewer_user: User,
    attempt_type: str | None = None,
    attempt_status: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> PlatformNoticeCampaignAttemptListRead:
    if db.get(PlatformNoticeCampaign, campaign_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Platform notice campaign not found.",
        )

    filters = [PlatformNoticeCampaignAttempt.campaign_id == campaign_id]
    if attempt_type is not None:
        filters.append(
            PlatformNoticeCampaignAttempt.attempt_type
            == normalize_choice(
                attempt_type,
                field_name="attempt_type",
                allowed_values=ATTEMPT_TYPES,
            )
        )
    if attempt_status is not None:
        filters.append(
            PlatformNoticeCampaignAttempt.attempt_status
            == normalize_choice(
                attempt_status,
                field_name="attempt_status",
                allowed_values=ATTEMPT_STATUSES,
            )
        )
    attempts = list(
        db.scalars(
            select(PlatformNoticeCampaignAttempt)
            .where(*filters)
            .order_by(
                PlatformNoticeCampaignAttempt.created_at.desc(),
                PlatformNoticeCampaignAttempt.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        ).all()
    )
    total_count = db.scalar(
        select(func.count())
        .select_from(PlatformNoticeCampaignAttempt)
        .where(*filters)
    ) or 0
    return PlatformNoticeCampaignAttemptListRead(
        attempts=[serialize_attempt(attempt) for attempt in attempts],
        total_count=total_count,
        offset=offset,
        limit=limit,
    )
