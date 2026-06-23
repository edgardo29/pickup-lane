"""Need a Sub notification creation, aggregation, and resolution helpers."""

import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Notification, SubPost, SubPostPosition, SubPostRequest
from backend.services.notification_event_service import (
    build_need_a_sub_notification_fields,
    reopen_aggregated_notification,
    resolve_aggregated_notification,
)
from backend.services.need_a_sub_rules import (
    SUB_POST_UPDATED_RECIPIENT_STATUSES,
    SUB_POST_UPDATED_STRUCTURAL_FIELDS,
    ensure_aware,
    now_utc,
)


def get_notification_position_or_404(
    db: Session,
    position_id: uuid.UUID,
) -> SubPostPosition:
    position = db.get(SubPostPosition, position_id)

    if position is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub position not found.",
        )

    return position


def add_need_a_sub_notification(
    db: Session,
    *,
    recipient_user_id: uuid.UUID,
    notification_type: str,
    sub_post: SubPost,
    sub_request: SubPostRequest | None = None,
    actor_user_id: uuid.UUID | None = None,
    event_at: datetime | None = None,
    title: str | None = None,
    summary: str | None = None,
    body: str | None = None,
) -> None:
    actor_id = actor_user_id if actor_user_id != recipient_user_id else None
    db.add(
        Notification(
            id=uuid.uuid4(),
            user_id=recipient_user_id,
            notification_type=notification_type,
            notification_category="game_activity",
            notification_domain="need_a_sub",
            **build_need_a_sub_notification_fields(
                sub_post,
                notification_type,
                event_at=event_at or now_utc(),
                title=title,
                summary=summary,
                body=body,
            ),
            actor_user_id=actor_id,
            related_sub_post_id=sub_post.id,
            related_sub_post_request_id=sub_request.id if sub_request else None,
            related_sub_post_position_id=(
                sub_request.sub_post_position_id if sub_request else None
            ),
            is_read=False,
            read_at=None,
        )
    )


def owner_request_activity_aggregation_key(
    sub_post_id: uuid.UUID,
    requester_user_id: uuid.UUID,
    owner_user_id: uuid.UUID,
) -> str:
    return (
        f"need_a_sub:post:{sub_post_id}:requester:{requester_user_id}:"
        f"owner:{owner_user_id}:request_activity"
    )


def sub_post_updated_aggregation_key(
    sub_post_id: uuid.UUID,
    recipient_user_id: uuid.UUID,
) -> str:
    return f"need_a_sub:post:{sub_post_id}:user:{recipient_user_id}:sub_post_updated"


def capture_sub_post_structural_snapshot(sub_post: SubPost) -> dict[str, object]:
    snapshot = {
        field_name: getattr(sub_post, field_name)
        for field_name in SUB_POST_UPDATED_STRUCTURAL_FIELDS
    }

    for field_name in ("starts_at", "ends_at"):
        value = snapshot[field_name]
        if isinstance(value, datetime):
            snapshot[field_name] = ensure_aware(value)

    return snapshot


def sub_post_structural_snapshot_changed(
    before: dict[str, object],
    sub_post: SubPost,
) -> bool:
    after = capture_sub_post_structural_snapshot(sub_post)
    return any(before[field_name] != after[field_name] for field_name in before)


def notify_active_requesters_sub_post_updated(
    db: Session,
    *,
    sub_post: SubPost,
    actor_user_id: uuid.UUID,
    event_at: datetime,
) -> None:
    active_requests = db.scalars(
        select(SubPostRequest).where(
            SubPostRequest.sub_post_id == sub_post.id,
            SubPostRequest.request_status.in_(SUB_POST_UPDATED_RECIPIENT_STATUSES),
        )
    ).all()

    notified_user_ids: set[uuid.UUID] = set()
    for sub_request in active_requests:
        recipient_user_id = sub_request.requester_user_id
        if recipient_user_id == actor_user_id or recipient_user_id in notified_user_ids:
            continue

        notified_user_ids.add(recipient_user_id)
        aggregation_key = sub_post_updated_aggregation_key(
            sub_post.id,
            recipient_user_id,
        )
        notification_fields = build_need_a_sub_notification_fields(
            sub_post,
            "sub_post_updated",
            event_at=event_at,
        )
        notification_fields.update(
            {
                "actor_user_id": actor_user_id,
                "related_sub_post_id": sub_post.id,
                "related_sub_post_request_id": sub_request.id,
                "related_sub_post_position_id": sub_request.sub_post_position_id,
            }
        )
        reopen_aggregated_notification(
            db,
            user_id=recipient_user_id,
            notification_type="sub_post_updated",
            notification_category="game_activity",
            notification_domain="need_a_sub",
            aggregation_key=aggregation_key,
            values=notification_fields,
            aggregate_count_mode="clear",
        )


def resolve_owner_request_activity_notification(
    db: Session,
    *,
    sub_post: SubPost,
    sub_request: SubPostRequest,
    resolution: str = "handled",
    read_at: datetime | None = None,
) -> None:
    if resolution == "canceled":
        values = {
            "title": "Request canceled",
            "summary": "A pending request was canceled.",
            "body": "A player canceled their pending request before it was reviewed.",
        }
    else:
        values = {
            "title": "Request handled",
            "summary": "This request was handled.",
            "body": "This pending request no longer needs review.",
        }

    resolve_aggregated_notification(
        db,
        user_id=sub_post.owner_user_id,
        aggregation_key=owner_request_activity_aggregation_key(
            sub_post.id,
            sub_request.requester_user_id,
            sub_post.owner_user_id,
        ),
        values=values,
        read_at=read_at,
    )


def notify_owner_sub_request_received(
    db: Session,
    sub_post: SubPost,
    position: SubPostPosition,
    sub_request: SubPostRequest,
    requester_user_id: uuid.UUID,
    event_at: datetime | None = None,
) -> None:
    effective_event_at = event_at or now_utc()
    aggregation_key = owner_request_activity_aggregation_key(
        sub_post.id,
        requester_user_id,
        sub_post.owner_user_id,
    )
    notification_fields = build_need_a_sub_notification_fields(
        sub_post,
        "sub_request_received",
        event_at=effective_event_at,
    )
    notification_fields.update(
        {
            "actor_user_id": requester_user_id,
            "related_sub_post_id": sub_post.id,
            "related_sub_post_request_id": sub_request.id,
            "related_sub_post_position_id": position.id,
        }
    )
    reopen_aggregated_notification(
        db,
        user_id=sub_post.owner_user_id,
        notification_type="sub_request_received",
        notification_category="game_activity",
        notification_domain="need_a_sub",
        aggregation_key=aggregation_key,
        values=notification_fields,
        aggregate_count_mode="clear",
    )


def notify_requester_sub_status(
    db: Session,
    *,
    sub_post: SubPost,
    sub_request: SubPostRequest,
    notification_type: str,
    title: str | None,
    body: str | None,
    actor_user_id: uuid.UUID | None,
    event_at: datetime | None = None,
) -> None:
    add_need_a_sub_notification(
        db,
        recipient_user_id=sub_request.requester_user_id,
        notification_type=notification_type,
        sub_post=sub_post,
        sub_request=sub_request,
        actor_user_id=actor_user_id,
        title=title,
        body=body,
        event_at=event_at,
    )


def notify_requester_waitlist_promoted(
    db: Session,
    sub_post: SubPost,
    sub_request: SubPostRequest | None,
    actor_user_id: uuid.UUID | None,
    event_at: datetime | None = None,
) -> None:
    if sub_request is None:
        return

    notify_requester_sub_status(
        db,
        sub_post=sub_post,
        sub_request=sub_request,
        notification_type="sub_waitlist_promoted_to_pending",
        title=None,
        body=None,
        actor_user_id=actor_user_id,
        event_at=event_at,
    )


def notify_waitlist_promoted(
    db: Session,
    sub_post: SubPost,
    sub_request: SubPostRequest | None,
    actor_user_id: uuid.UUID | None,
) -> None:
    if sub_request is None:
        return

    promotion_time = ensure_aware(sub_request.updated_at)
    notify_requester_waitlist_promoted(
        db,
        sub_post,
        sub_request,
        actor_user_id,
        event_at=promotion_time,
    )
    position = get_notification_position_or_404(db, sub_request.sub_post_position_id)
    notify_owner_sub_request_received(
        db,
        sub_post,
        position,
        sub_request,
        sub_request.requester_user_id,
        event_at=promotion_time,
    )
