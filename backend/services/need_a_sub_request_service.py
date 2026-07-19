"""Need a Sub request, waitlist, and requester/owner workflows."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import SubPost, SubPostRequest, User
from backend.services.need_a_sub_lifecycle_service import (
    add_request_status_history,
    change_request_status,
    expire_due_posts_and_requests,
    recalculate_filled_status,
)
from backend.services.need_a_sub_notification_service import (
    add_need_a_sub_notification,
    notify_owner_sub_request_received,
    notify_requester_sub_status,
    notify_waitlist_promoted,
    resolve_owner_request_activity_notification,
)
from backend.services.need_a_sub_post_service import (
    get_position_or_404,
    get_sub_post_for_update_or_404,
    get_sub_post_or_404,
    require_owner,
)
from backend.services.need_a_sub_rules import (
    ACTIVE_REQUEST_STATUSES,
    MAX_WAITLIST_REQUESTS_PER_POST,
    QUEUE_HOLD_REQUEST_STATUSES,
    ensure_aware,
    now_utc,
    require_before_post_start,
    require_live_sub_post,
    require_publicly_visible_sub_post,
)
from backend.services.sub_post_chat_service import (
    resolve_sub_chat_notifications_for_user as resolve_sub_chat_notification_for_user,
)


def get_sub_post_request_or_404(db: Session, request_id: uuid.UUID) -> SubPostRequest:
    sub_request = db.get(SubPostRequest, request_id)

    if sub_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub request not found.",
        )

    return sub_request


def get_sub_post_request_and_post_for_update(
    db: Session,
    request_id: uuid.UUID,
) -> tuple[SubPostRequest, SubPost]:
    request_snapshot = get_sub_post_request_or_404(db, request_id)
    sub_post = get_sub_post_for_update_or_404(db, request_snapshot.sub_post_id)
    sub_request = db.scalar(
        select(SubPostRequest)
        .where(SubPostRequest.id == request_id)
        .with_for_update()
    )
    if sub_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub request not found.",
        )
    return sub_request, sub_post


def count_waitlist_ahead(db: Session, sub_request: SubPostRequest) -> int:
    if sub_request.request_status != "sub_waitlist":
        return 0

    return db.scalar(
        select(func.count())
        .select_from(SubPostRequest)
        .where(
            SubPostRequest.sub_post_position_id == sub_request.sub_post_position_id,
            SubPostRequest.request_status == "sub_waitlist",
            SubPostRequest.created_at < sub_request.created_at,
        )
    ) or 0


def build_requester_display(user: User | None) -> tuple[str | None, str | None]:
    if user is None:
        return None, None

    name_parts = [
        value.strip()
        for value in [user.first_name or "", user.last_name or ""]
        if value and value.strip()
    ]
    display_name = " ".join(name_parts) if name_parts else "Pickup Lane Player"
    initials_source = name_parts if name_parts else ["Pickup", "Lane"]
    initials = "".join(part[:1].upper() for part in initials_source if part)[:2]

    return display_name, initials or None


def serialize_sub_post_request(
    db: Session,
    sub_request: SubPostRequest,
    include_waitlist_ahead: bool = False,
) -> dict:
    requester = db.get(User, sub_request.requester_user_id)
    requester_display_name, requester_initials = build_requester_display(requester)

    return {
        "id": sub_request.id,
        "sub_post_id": sub_request.sub_post_id,
        "sub_post_position_id": sub_request.sub_post_position_id,
        "requester_user_id": sub_request.requester_user_id,
        "requester_display_name": requester_display_name,
        "requester_initials": requester_initials,
        "request_status": sub_request.request_status,
        "confirmed_at": sub_request.confirmed_at,
        "declined_at": sub_request.declined_at,
        "sub_waitlisted_at": sub_request.sub_waitlisted_at,
        "canceled_at": sub_request.canceled_at,
        "expired_at": sub_request.expired_at,
        "no_show_reported_at": sub_request.no_show_reported_at,
        "waitlist_ahead_count": (
            count_waitlist_ahead(db, sub_request) if include_waitlist_ahead else None
        ),
        "created_at": sub_request.created_at,
        "updated_at": sub_request.updated_at,
    }


def list_owner_sub_post_requests(
    db: Session,
    sub_post_id: uuid.UUID,
    owner: User,
) -> list[dict]:
    expire_due_posts_and_requests(db)
    sub_post = get_sub_post_or_404(db, sub_post_id)
    require_owner(sub_post, owner)
    require_live_sub_post(sub_post, "Only active posts can be reviewed.")
    requests = list(
        db.scalars(
            select(SubPostRequest)
            .where(SubPostRequest.sub_post_id == sub_post_id)
            .order_by(SubPostRequest.created_at.asc())
        ).all()
    )
    return [
        serialize_sub_post_request(db, sub_request, include_waitlist_ahead=True)
        for sub_request in requests
    ]


def list_requester_sub_post_requests(
    db: Session,
    requester: User,
) -> list[dict]:
    expire_due_posts_and_requests(db)
    requests = list(
        db.scalars(
            select(SubPostRequest)
            .where(SubPostRequest.requester_user_id == requester.id)
            .order_by(SubPostRequest.created_at.desc())
        ).all()
    )
    return [
        serialize_sub_post_request(db, sub_request, include_waitlist_ahead=True)
        for sub_request in requests
    ]


def count_queued_slots(db: Session, sub_post_position_id: uuid.UUID) -> int:
    return db.scalar(
        select(func.count())
        .select_from(SubPostRequest)
        .where(
            SubPostRequest.sub_post_position_id == sub_post_position_id,
            SubPostRequest.request_status.in_(QUEUE_HOLD_REQUEST_STATUSES),
        )
    ) or 0


def count_post_waitlist_requests(db: Session, sub_post_id: uuid.UUID) -> int:
    return db.scalar(
        select(func.count())
        .select_from(SubPostRequest)
        .where(
            SubPostRequest.sub_post_id == sub_post_id,
            SubPostRequest.request_status == "sub_waitlist",
        )
    ) or 0


def create_request(
    db: Session,
    requester: User,
    sub_post_id: uuid.UUID,
    sub_post_position_id: uuid.UUID,
) -> SubPostRequest:
    expire_due_posts_and_requests(db)
    sub_post = get_sub_post_for_update_or_404(db, sub_post_id)
    position = get_position_or_404(db, sub_post_position_id, lock_for_update=True)
    current_time = now_utc()

    if sub_post.post_status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requests can only be created for open posts.",
        )
    require_publicly_visible_sub_post(
        sub_post,
        "Requests can only be created for open posts.",
    )

    if current_time >= ensure_aware(sub_post.expires_at):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This Need a Sub post is no longer accepting requests.",
        )

    if sub_post.owner_user_id == requester.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Owners cannot request their own Need a Sub post.",
        )

    if position.sub_post_id != sub_post.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Position does not belong to this Need a Sub post.",
        )

    existing_request = db.scalar(
        select(SubPostRequest).where(
            SubPostRequest.sub_post_id == sub_post.id,
            SubPostRequest.requester_user_id == requester.id,
            SubPostRequest.request_status.in_(ACTIVE_REQUEST_STATUSES),
        )
    )
    if existing_request is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already requested a spot for this post.",
        )

    initial_status = (
        "pending"
        if count_queued_slots(db, position.id) < position.spots_needed
        else "sub_waitlist"
    )
    if (
        initial_status == "sub_waitlist"
        and count_post_waitlist_requests(db, sub_post.id) >= MAX_WAITLIST_REQUESTS_PER_POST
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This Need a Sub waitlist is full.",
        )

    current_time = now_utc()
    new_request = SubPostRequest(
        id=uuid.uuid4(),
        sub_post_id=sub_post.id,
        sub_post_position_id=position.id,
        requester_user_id=requester.id,
        request_status=initial_status,
        sub_waitlisted_at=current_time if initial_status == "sub_waitlist" else None,
    )
    db.add(new_request)
    db.flush()
    add_request_status_history(
        db,
        new_request,
        old_status=None,
        new_status=initial_status,
        changed_by_user_id=requester.id,
        change_source="requester",
    )
    if initial_status == "pending":
        notify_owner_sub_request_received(
            db,
            sub_post,
            position,
            new_request,
            requester.id,
        )

    try:
        db.commit()
        db.refresh(new_request)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc.orig),
        ) from exc

    return new_request


def promote_next_waitlisted_request(
    db: Session,
    sub_post_position_id: uuid.UUID,
    changed_by_user_id: uuid.UUID | None,
    change_source: str,
) -> SubPostRequest | None:
    db.flush()
    position = get_position_or_404(db, sub_post_position_id, lock_for_update=True)

    if count_queued_slots(db, sub_post_position_id) >= position.spots_needed:
        return None

    next_request = db.scalar(
        select(SubPostRequest)
        .where(
            SubPostRequest.sub_post_position_id == sub_post_position_id,
            SubPostRequest.request_status == "sub_waitlist",
        )
        .order_by(SubPostRequest.created_at.asc())
    )

    if next_request is None:
        return None

    change_request_status(
        db,
        next_request,
        "pending",
        changed_by_user_id,
        change_source,
        "Automatically moved from waitlist when a review slot opened.",
    )
    return next_request


def owner_accept_request(db: Session, owner: User, request_id: uuid.UUID) -> SubPostRequest:
    expire_due_posts_and_requests(db)
    sub_request, sub_post = get_sub_post_request_and_post_for_update(db, request_id)
    position = get_position_or_404(db, sub_request.sub_post_position_id, lock_for_update=True)
    current_time = now_utc()
    require_owner(sub_post, owner)
    require_before_post_start(sub_post, "Requests cannot be accepted after the game starts.")

    if sub_request.request_status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending requests can be accepted.",
        )

    if sub_post.post_status != "active" or current_time >= ensure_aware(sub_post.expires_at):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This post is not accepting requests.",
        )
    require_publicly_visible_sub_post(
        sub_post,
        "This post is not accepting requests.",
    )

    if count_queued_slots(db, position.id) > position.spots_needed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This position is already full.",
        )

    change_request_status(
        db,
        sub_request,
        "confirmed",
        owner.id,
        "owner",
        current_time=current_time,
    )
    resolve_owner_request_activity_notification(
        db,
        sub_post=sub_post,
        sub_request=sub_request,
        read_at=current_time,
    )
    recalculate_filled_status(db, sub_post, owner.id, "owner")
    notify_requester_sub_status(
        db,
        sub_post=sub_post,
        sub_request=sub_request,
        notification_type="sub_request_confirmed",
        title=None,
        body=None,
        actor_user_id=owner.id,
    )
    db.commit()
    db.refresh(sub_request)
    return sub_request


def owner_decline_request(
    db: Session, owner: User, request_id: uuid.UUID, reason: str | None = None
) -> SubPostRequest:
    expire_due_posts_and_requests(db)
    sub_request, sub_post = get_sub_post_request_and_post_for_update(db, request_id)
    require_owner(sub_post, owner)
    require_live_sub_post(sub_post, "Only active posts can be reviewed.")
    require_before_post_start(sub_post, "Requests cannot be declined after the game starts.")

    if sub_request.request_status not in {"pending", "sub_waitlist"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending or waitlisted requests can be declined.",
        )

    was_pending = sub_request.request_status == "pending"
    position_id = sub_request.sub_post_position_id
    current_time = now_utc()
    change_request_status(
        db,
        sub_request,
        "declined",
        owner.id,
        "owner",
        reason,
        current_time=current_time,
    )
    if was_pending:
        resolve_owner_request_activity_notification(
            db,
            sub_post=sub_post,
            sub_request=sub_request,
            read_at=current_time,
        )
    notify_requester_sub_status(
        db,
        sub_post=sub_post,
        sub_request=sub_request,
        notification_type="sub_request_declined",
        title=None,
        body=None,
        actor_user_id=owner.id,
    )

    if was_pending:
        promoted_request = promote_next_waitlisted_request(
            db,
            position_id,
            owner.id,
            "owner",
        )
        notify_waitlist_promoted(
            db,
            sub_post,
            promoted_request,
            owner.id,
        )

    db.commit()
    db.refresh(sub_request)
    return sub_request


def requester_cancel_request(
    db: Session, requester: User, request_id: uuid.UUID
) -> SubPostRequest:
    expire_due_posts_and_requests(db)
    sub_request, sub_post = get_sub_post_request_and_post_for_update(db, request_id)

    if sub_request.requester_user_id != requester.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the requester can cancel this request.",
        )
    require_before_post_start(sub_post, "Requests cannot be canceled after the game starts.")
    require_live_sub_post(sub_post, "Only active posts can be updated.")

    if sub_request.request_status not in ACTIVE_REQUEST_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This request cannot be canceled.",
        )

    previous_status = sub_request.request_status
    should_promote = previous_status in {"pending", "confirmed"}
    was_confirmed = sub_request.request_status == "confirmed"
    position_id = sub_request.sub_post_position_id
    current_time = now_utc()
    change_request_status(
        db,
        sub_request,
        "canceled_by_player",
        requester.id,
        "requester",
        current_time=current_time,
    )
    if previous_status == "pending":
        resolve_owner_request_activity_notification(
            db,
            sub_post=sub_post,
            sub_request=sub_request,
            resolution="canceled",
            read_at=current_time,
        )
    elif previous_status == "confirmed":
        add_need_a_sub_notification(
            db,
            recipient_user_id=sub_post.owner_user_id,
            notification_type="sub_request_canceled_by_player",
            sub_post=sub_post,
            sub_request=sub_request,
            actor_user_id=requester.id,
        )

    if was_confirmed:
        resolve_sub_chat_notification_for_user(
            db,
            sub_post_id=sub_post.id,
            user_id=requester.id,
            read_at=current_time,
        )
        recalculate_filled_status(db, sub_post, requester.id, "requester")
    if should_promote:
        promoted_request = promote_next_waitlisted_request(
            db,
            position_id,
            requester.id,
            "requester",
        )
        notify_waitlist_promoted(
            db,
            sub_post,
            promoted_request,
            requester.id,
        )

    db.commit()
    db.refresh(sub_request)
    return sub_request


def owner_cancel_request(
    db: Session,
    owner: User,
    request_id: uuid.UUID,
    reason: str | None = None,
) -> SubPostRequest:
    expire_due_posts_and_requests(db)
    sub_request, sub_post = get_sub_post_request_and_post_for_update(db, request_id)
    require_owner(sub_post, owner)
    require_before_post_start(
        sub_post,
        "Confirmed players cannot be removed after the game starts.",
    )
    require_live_sub_post(sub_post, "Only active posts can be reviewed.")

    if sub_request.request_status != "confirmed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only confirmed requests can be canceled by owner.",
        )

    position_id = sub_request.sub_post_position_id
    current_time = now_utc()
    change_request_status(
        db,
        sub_request,
        "canceled_by_owner",
        owner.id,
        "owner",
        reason,
        current_time=current_time,
    )
    resolve_sub_chat_notification_for_user(
        db,
        sub_post_id=sub_post.id,
        user_id=sub_request.requester_user_id,
        read_at=current_time,
    )
    notify_requester_sub_status(
        db,
        sub_post=sub_post,
        sub_request=sub_request,
        notification_type="sub_request_canceled_by_owner",
        title=None,
        body=None,
        actor_user_id=owner.id,
    )

    recalculate_filled_status(db, sub_post, owner.id, "owner")
    promoted_request = promote_next_waitlisted_request(db, position_id, owner.id, "owner")
    notify_waitlist_promoted(
        db,
        sub_post,
        promoted_request,
        owner.id,
    )

    db.commit()
    db.refresh(sub_request)
    return sub_request


def owner_report_no_show(
    db: Session,
    owner: User,
    request_id: uuid.UUID,
    reason: str | None = None,
) -> SubPostRequest:
    expire_due_posts_and_requests(db)
    sub_request, sub_post = get_sub_post_request_and_post_for_update(db, request_id)
    require_owner(sub_post, owner)

    if sub_request.request_status != "confirmed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only confirmed requests can be reported as no-show.",
        )

    if now_utc() <= ensure_aware(sub_post.ends_at):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No-show can only be reported after the game ends.",
        )

    change_request_status(db, sub_request, "no_show_reported", owner.id, "owner", reason)
    resolve_sub_chat_notification_for_user(
        db,
        sub_post_id=sub_post.id,
        user_id=sub_request.requester_user_id,
    )
    db.commit()
    db.refresh(sub_request)
    return sub_request
