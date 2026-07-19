"""Need a Sub status history and lifecycle state helpers."""

import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models import (
    SubPost,
    SubPostPosition,
    SubPostRequest,
    SubPostRequestStatusHistory,
    SubPostStatusHistory,
    User,
)
from backend.services.auth_service import user_is_active_admin
from backend.services.admin_review_service import (
    close_open_content_moderation_case_for_sub_post_lifecycle,
)
from backend.services.need_a_sub_notification_service import (
    resolve_owner_request_activity_notification,
)
from backend.services.need_a_sub_rules import (
    ACTIVE_VISIBLE_POST_STATUSES,
    EXPIRABLE_REQUEST_STATUSES,
    ensure_aware,
    now_utc,
)


def add_post_status_history(
    db: Session,
    sub_post: SubPost,
    old_status: str | None,
    new_status: str,
    changed_by_user_id: uuid.UUID | None,
    change_source: str,
    change_reason: str | None = None,
) -> None:
    db.add(
        SubPostStatusHistory(
            id=uuid.uuid4(),
            sub_post_id=sub_post.id,
            old_status=old_status,
            new_status=new_status,
            changed_by_user_id=changed_by_user_id,
            change_source=change_source,
            change_reason=change_reason,
        )
    )


def add_request_status_history(
    db: Session,
    sub_request: SubPostRequest,
    old_status: str | None,
    new_status: str,
    changed_by_user_id: uuid.UUID | None,
    change_source: str,
    change_reason: str | None = None,
) -> None:
    db.add(
        SubPostRequestStatusHistory(
            id=uuid.uuid4(),
            sub_post_request_id=sub_request.id,
            old_status=old_status,
            new_status=new_status,
            changed_by_user_id=changed_by_user_id,
            change_source=change_source,
            change_reason=change_reason,
        )
    )


def change_request_status(
    db: Session,
    sub_request: SubPostRequest,
    new_status: str,
    changed_by_user_id: uuid.UUID | None,
    change_source: str,
    change_reason: str | None = None,
    current_time: datetime | None = None,
) -> None:
    current_time = current_time or now_utc()
    old_status = sub_request.request_status
    sub_request.request_status = new_status
    sub_request.updated_at = current_time

    if new_status == "confirmed":
        sub_request.confirmed_at = current_time
    elif new_status == "declined":
        sub_request.declined_at = current_time
    elif new_status == "sub_waitlist":
        sub_request.sub_waitlisted_at = current_time
    elif new_status in {"canceled_by_player", "canceled_by_owner"}:
        sub_request.canceled_at = current_time
    elif new_status == "expired":
        sub_request.expired_at = current_time
    elif new_status == "no_show_reported":
        sub_request.no_show_reported_at = current_time

    db.add(sub_request)
    add_request_status_history(
        db,
        sub_request,
        old_status=old_status,
        new_status=new_status,
        changed_by_user_id=changed_by_user_id,
        change_source=change_source,
        change_reason=change_reason,
    )


def list_lifecycle_positions(
    db: Session,
    sub_post_id: uuid.UUID,
) -> list[SubPostPosition]:
    return list(
        db.scalars(
            select(SubPostPosition)
            .where(SubPostPosition.sub_post_id == sub_post_id)
            .order_by(SubPostPosition.sort_order.asc(), SubPostPosition.created_at.asc())
        ).all()
    )


def position_is_filled(db: Session, position: SubPostPosition) -> bool:
    confirmed_count = db.scalar(
        select(func.count())
        .select_from(SubPostRequest)
        .where(
            SubPostRequest.sub_post_position_id == position.id,
            SubPostRequest.request_status == "confirmed",
        )
    ) or 0
    return confirmed_count >= position.spots_needed


def sub_post_is_full(db: Session, sub_post: SubPost) -> bool:
    positions = list_lifecycle_positions(db, sub_post.id)
    return bool(positions) and all(
        position_is_filled(db, position) for position in positions
    )


def recalculate_filled_status(
    db: Session,
    sub_post: SubPost,
    changed_by_user_id: uuid.UUID | None,
    change_source: str,
) -> None:
    db.flush()
    is_filled = sub_post_is_full(db, sub_post)
    current_time = now_utc()

    if sub_post.post_status != "active":
        return

    if is_filled and sub_post.filled_at is None:
        sub_post.filled_at = current_time
        sub_post.updated_at = current_time
        db.add(sub_post)
    elif not is_filled and sub_post.filled_at is not None and current_time < ensure_aware(
        sub_post.starts_at
    ):
        sub_post.filled_at = None
        sub_post.updated_at = current_time
        db.add(sub_post)


def get_sub_post_for_history_or_404(db: Session, sub_post_id: uuid.UUID) -> SubPost:
    sub_post = db.get(SubPost, sub_post_id)

    if sub_post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub post not found.",
        )

    return sub_post


def get_sub_post_request_for_history_or_404(
    db: Session,
    request_id: uuid.UUID,
) -> SubPostRequest:
    sub_request = db.get(SubPostRequest, request_id)

    if sub_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub request not found.",
        )

    return sub_request


def list_sub_post_status_history(
    db: Session,
    sub_post_id: uuid.UUID,
    current_user: User,
) -> list[SubPostStatusHistory]:
    sub_post = get_sub_post_for_history_or_404(db, sub_post_id)

    if (
        sub_post.owner_user_id != current_user.id
        and not user_is_active_admin(current_user)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot view this post history.",
        )

    return list(
        db.scalars(
            select(SubPostStatusHistory)
            .where(SubPostStatusHistory.sub_post_id == sub_post_id)
            .order_by(SubPostStatusHistory.created_at.asc())
        ).all()
    )


def list_sub_post_request_status_history(
    db: Session,
    request_id: uuid.UUID,
    current_user: User,
) -> list[SubPostRequestStatusHistory]:
    sub_request = get_sub_post_request_for_history_or_404(db, request_id)
    sub_post = get_sub_post_for_history_or_404(db, sub_request.sub_post_id)
    can_view = (
        sub_request.requester_user_id == current_user.id
        or sub_post.owner_user_id == current_user.id
        or user_is_active_admin(current_user)
    )

    if not can_view:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot view this request history.",
        )

    return list(
        db.scalars(
            select(SubPostRequestStatusHistory)
            .where(SubPostRequestStatusHistory.sub_post_request_id == request_id)
            .order_by(SubPostRequestStatusHistory.created_at.asc())
        ).all()
    )


def expire_due_posts_and_requests(db: Session) -> dict[str, int]:
    current_time = now_utc()
    expired_posts_count = 0
    completed_posts_count = 0
    expired_requests_count = 0

    posts = db.scalars(
        select(SubPost).where(
            SubPost.post_status.in_(ACTIVE_VISIBLE_POST_STATUSES),
            SubPost.expires_at <= current_time,
        ).with_for_update()
    ).all()

    for sub_post in posts:
        old_status = sub_post.post_status
        new_status = "completed" if sub_post_is_full(db, sub_post) else "expired"
        sub_post.post_status = new_status
        if new_status == "completed" and sub_post.filled_at is None:
            sub_post.filled_at = current_time
        sub_post.updated_at = current_time
        db.add(sub_post)
        add_post_status_history(
            db,
            sub_post,
            old_status,
            new_status,
            None,
            "scheduled_job",
        )
        close_open_content_moderation_case_for_sub_post_lifecycle(
            db,
            sub_post_id=sub_post.id,
            closure_outcome="no_action_needed",
            closure_reason=(
                "Need a Sub post was completed before moderation review was completed."
                if new_status == "completed"
                else "Need a Sub post expired before moderation review was completed."
            ),
            lifecycle_action=(
                "post_completed" if new_status == "completed" else "post_expired"
            ),
            trigger_actor_type="scheduled_job",
            previous_post_status=old_status,
            new_post_status=new_status,
            closed_at=current_time,
        )
        if new_status == "completed":
            completed_posts_count += 1
        else:
            expired_posts_count += 1

    requests = db.scalars(
        select(SubPostRequest)
        .join(SubPost, SubPostRequest.sub_post_id == SubPost.id)
        .where(
            SubPost.expires_at <= current_time,
            SubPostRequest.request_status.in_(EXPIRABLE_REQUEST_STATUSES),
        )
    ).all()

    for sub_request in requests:
        previous_status = sub_request.request_status
        change_request_status(
            db,
            sub_request,
            "expired",
            None,
            "scheduled_job",
            current_time=current_time,
        )
        if previous_status == "pending":
            sub_post = db.get(SubPost, sub_request.sub_post_id)
            if sub_post is not None:
                resolve_owner_request_activity_notification(
                    db,
                    sub_post=sub_post,
                    sub_request=sub_request,
                    read_at=current_time,
                )
        expired_requests_count += 1

    db.commit()
    return {
        "posts_completed": completed_posts_count,
        "posts_expired": expired_posts_count,
        "requests_expired": expired_requests_count,
    }
