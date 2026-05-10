import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    SubPost,
    SubPostPosition,
    SubPostRequest,
    SubPostRequestStatusHistory,
    SubPostStatusHistory,
    User,
)
from backend.schemas import SubPostCreate, SubPostUpdate

POST_STATUSES = {"draft", "active", "filled", "expired", "canceled", "removed"}
REQUEST_STATUSES = {
    "pending",
    "confirmed",
    "declined",
    "sub_waitlist",
    "canceled_by_player",
    "canceled_by_owner",
    "no_show_reported",
    "expired",
}
ACTIVE_VISIBLE_POST_STATUSES = {"active", "filled"}
ACTIVE_REQUEST_STATUSES = {"pending", "confirmed", "sub_waitlist"}
QUEUE_HOLD_REQUEST_STATUSES = {"pending", "confirmed"}
MAX_WAITLIST_REQUESTS_PER_POST = 25
TERMINAL_REQUEST_STATUSES = {
    "declined",
    "canceled_by_player",
    "canceled_by_owner",
    "no_show_reported",
    "expired",
}
ADMIN_ROLES = {"admin", "moderator"}
POST_STATUS_CHANGE_SOURCES = {"owner", "admin", "system", "scheduled_job"}
VALID_POSITION_GROUPS_BY_POST_GROUP = {
    "open": {"open"},
    "men": {"open", "men"},
    "women": {"open", "women"},
    "coed": {"open", "men", "women"},
}


def ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def now_utc() -> datetime:
    return datetime.now(UTC)


def get_sub_post_or_404(db: Session, sub_post_id: uuid.UUID) -> SubPost:
    sub_post = db.get(SubPost, sub_post_id)

    if sub_post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub post not found.",
        )

    return sub_post


def get_sub_post_request_or_404(db: Session, request_id: uuid.UUID) -> SubPostRequest:
    sub_request = db.get(SubPostRequest, request_id)

    if sub_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub request not found.",
        )

    return sub_request


def get_position_or_404(db: Session, position_id: uuid.UUID) -> SubPostPosition:
    position = db.get(SubPostPosition, position_id)

    if position is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub position not found.",
        )

    return position


def require_owner(sub_post: SubPost, user: User) -> None:
    if sub_post.owner_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the post owner can perform this action.",
        )


def require_admin(user: User) -> None:
    if user.role not in ADMIN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an admin or moderator can perform this action.",
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


def normalize_post_status_change_source(change_source: str) -> str:
    if change_source in POST_STATUS_CHANGE_SOURCES:
        return change_source

    return "system"


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


def validate_post_creation(post_create: SubPostCreate) -> None:
    starts_at = ensure_aware(post_create.starts_at)
    ends_at = ensure_aware(post_create.ends_at)

    if starts_at <= now_utc():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="starts_at must be in the future.",
        )

    if ends_at <= starts_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ends_at must be greater than starts_at.",
        )

    if post_create.sport_type != "soccer":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="sport_type must be 'soccer'.",
        )

    if post_create.currency != "USD":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="currency must be 'USD'.",
        )

    if post_create.price_due_at_venue_cents < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="price_due_at_venue_cents must be greater than or equal to 0.",
        )

    if post_create.subs_needed <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="subs_needed must be greater than 0.",
        )

    required_location_values = [
        post_create.location_name,
        post_create.address_line_1,
        post_create.city,
        post_create.state,
        post_create.postal_code,
        post_create.country_code,
    ]
    if any(not value.strip() for value in required_location_values):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Location fields are required.",
        )

    if not post_create.positions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one position requirement is required.",
        )

    total_spots = sum(position.spots_needed for position in post_create.positions)
    if total_spots != post_create.subs_needed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Position spots must add up to subs_needed.",
        )

    allowed_groups = VALID_POSITION_GROUPS_BY_POST_GROUP[post_create.game_player_group]
    invalid_groups = {
        position.player_group
        for position in post_create.positions
        if position.player_group not in allowed_groups
    }
    if invalid_groups:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Position player groups are not compatible with the post group.",
        )


def create_sub_post(
    db: Session, owner: User, post_create: SubPostCreate
) -> SubPost:
    validate_post_creation(post_create)
    post_data = post_create.model_dump(exclude={"positions"})
    post_data["starts_at"] = ensure_aware(post_create.starts_at)
    post_data["ends_at"] = ensure_aware(post_create.ends_at)
    new_post = SubPost(
        id=uuid.uuid4(),
        owner_user_id=owner.id,
        post_status="active",
        expires_at=post_data["starts_at"],
        **post_data,
    )

    db.add(new_post)
    db.flush()

    for position_create in post_create.positions:
        db.add(
            SubPostPosition(
                id=uuid.uuid4(),
                sub_post_id=new_post.id,
                **position_create.model_dump(),
            )
        )

    add_post_status_history(
        db,
        new_post,
        old_status=None,
        new_status="active",
        changed_by_user_id=owner.id,
        change_source="owner",
    )

    try:
        db.commit()
        db.refresh(new_post)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc.orig),
        ) from exc

    return new_post


def count_position_requests(db: Session, position_id: uuid.UUID) -> dict[str, int]:
    rows = db.execute(
        select(SubPostRequest.request_status, func.count())
        .where(SubPostRequest.sub_post_position_id == position_id)
        .group_by(SubPostRequest.request_status)
    ).all()
    return {status_value: count for status_value, count in rows}


def serialize_sub_post_position(db: Session, position: SubPostPosition) -> dict:
    counts = count_position_requests(db, position.id)
    return {
        "id": position.id,
        "sub_post_id": position.sub_post_id,
        "position_label": position.position_label,
        "player_group": position.player_group,
        "spots_needed": position.spots_needed,
        "sort_order": position.sort_order,
        "pending_count": counts.get("pending", 0),
        "confirmed_count": counts.get("confirmed", 0),
        "sub_waitlist_count": counts.get("sub_waitlist", 0),
        "created_at": position.created_at,
        "updated_at": position.updated_at,
    }


def count_position_attached_requests(db: Session, position_id: uuid.UUID) -> int:
    return db.scalar(
        select(func.count())
        .select_from(SubPostRequest)
        .where(
            SubPostRequest.sub_post_position_id == position_id,
            SubPostRequest.request_status.notin_(TERMINAL_REQUEST_STATUSES),
        )
    ) or 0


def build_effective_post_create(db: Session, sub_post: SubPost, post_update: SubPostUpdate) -> SubPostCreate:
    update_data = post_update.model_dump(exclude_unset=True, exclude={"positions"})
    positions = post_update.positions if "positions" in post_update.model_fields_set else None

    current_data = {
        field: getattr(sub_post, field)
        for field in (
            "sport_type",
            "format_label",
            "skill_level",
            "game_player_group",
            "team_name",
            "starts_at",
            "ends_at",
            "timezone",
            "location_name",
            "address_line_1",
            "city",
            "state",
            "postal_code",
            "country_code",
            "neighborhood",
            "subs_needed",
            "price_due_at_venue_cents",
            "currency",
            "payment_note",
            "notes",
        )
    }
    current_data.update(update_data)
    current_data["positions"] = positions if positions is not None else [
        {
            "position_label": position.position_label,
            "player_group": position.player_group,
            "spots_needed": position.spots_needed,
            "sort_order": position.sort_order,
        }
        for position in list_positions(db, sub_post.id)
    ]

    if positions is not None:
        current_data["subs_needed"] = sum(position.spots_needed for position in positions)

    return SubPostCreate(**current_data)


def validate_position_update_safety(
    db: Session,
    existing_positions: list[SubPostPosition],
    new_positions: list,
) -> None:
    new_position_by_key = {
        (position.position_label, position.player_group): position
        for position in new_positions
    }

    for existing_position in existing_positions:
        attached_count = count_position_attached_requests(db, existing_position.id)
        if attached_count == 0:
            continue

        key = (existing_position.position_label, existing_position.player_group)
        new_position = new_position_by_key.get(key)
        if new_position is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sub requirements with active requests cannot be removed or changed.",
            )

        counts = count_position_requests(db, existing_position.id)
        minimum_spots = counts.get("pending", 0) + counts.get("confirmed", 0)
        if new_position.spots_needed < minimum_spots:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sub requirement spots cannot be lower than pending and confirmed requests.",
            )


def apply_position_updates(
    db: Session,
    sub_post: SubPost,
    new_positions: list,
) -> None:
    existing_positions = list_positions(db, sub_post.id)
    validate_position_update_safety(db, existing_positions, new_positions)

    existing_by_key = {
        (position.position_label, position.player_group): position
        for position in existing_positions
    }
    new_keys = {
        (position.position_label, position.player_group)
        for position in new_positions
    }

    for existing_position in existing_positions:
        key = (existing_position.position_label, existing_position.player_group)
        if key not in new_keys:
            if count_position_attached_requests(db, existing_position.id) > 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Sub requirements with active requests cannot be removed.",
                )
            db.delete(existing_position)

    for sort_order, position_update in enumerate(new_positions):
        key = (position_update.position_label, position_update.player_group)
        existing_position = existing_by_key.get(key)
        if existing_position is None:
            db.add(
                SubPostPosition(
                    id=uuid.uuid4(),
                    sub_post_id=sub_post.id,
                    position_label=position_update.position_label,
                    player_group=position_update.player_group,
                    spots_needed=position_update.spots_needed,
                    sort_order=sort_order,
                )
            )
            continue

        existing_position.spots_needed = position_update.spots_needed
        existing_position.sort_order = sort_order
        existing_position.updated_at = now_utc()
        db.add(existing_position)


def update_sub_post(
    db: Session,
    owner: User,
    sub_post_id: uuid.UUID,
    post_update: SubPostUpdate,
) -> SubPost:
    sub_post = get_sub_post_or_404(db, sub_post_id)
    require_owner(sub_post, owner)

    if sub_post.post_status not in {"active", "filled"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only active or filled posts can be edited.",
        )

    effective_post = build_effective_post_create(db, sub_post, post_update)
    validate_post_creation(effective_post)
    update_data = post_update.model_dump(exclude_unset=True, exclude={"positions"})
    new_positions = post_update.positions if "positions" in post_update.model_fields_set else None

    current_time = now_utc()
    for field_name, field_value in update_data.items():
        setattr(sub_post, field_name, field_value)

    if new_positions is not None:
        sub_post.subs_needed = sum(position.spots_needed for position in new_positions)
        apply_position_updates(db, sub_post, new_positions)

    sub_post.starts_at = ensure_aware(sub_post.starts_at)
    sub_post.ends_at = ensure_aware(sub_post.ends_at)
    sub_post.expires_at = sub_post.starts_at
    sub_post.updated_at = current_time
    db.add(sub_post)
    recalculate_filled_status(db, sub_post, owner.id, "owner")

    try:
        db.commit()
        db.refresh(sub_post)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc.orig),
        ) from exc

    return sub_post


def list_positions(db: Session, sub_post_id: uuid.UUID) -> list[SubPostPosition]:
    return list(
        db.scalars(
            select(SubPostPosition)
            .where(SubPostPosition.sub_post_id == sub_post_id)
            .order_by(SubPostPosition.sort_order.asc(), SubPostPosition.created_at.asc())
        ).all()
    )


def count_requests_by_status(db: Session, sub_post_id: uuid.UUID) -> dict[str, int]:
    rows = db.execute(
        select(SubPostRequest.request_status, func.count())
        .where(SubPostRequest.sub_post_id == sub_post_id)
        .group_by(SubPostRequest.request_status)
    ).all()
    return {status_value: count for status_value, count in rows}


def serialize_sub_post(db: Session, sub_post: SubPost) -> dict:
    counts = count_requests_by_status(db, sub_post.id)
    return {
        **{
            field: getattr(sub_post, field)
            for field in (
                "id",
                "owner_user_id",
                "post_status",
                "sport_type",
                "format_label",
                "skill_level",
                "game_player_group",
                "team_name",
                "starts_at",
                "ends_at",
                "timezone",
                "location_name",
                "address_line_1",
                "city",
                "state",
                "postal_code",
                "country_code",
                "neighborhood",
                "subs_needed",
                "price_due_at_venue_cents",
                "currency",
                "payment_note",
                "notes",
                "expires_at",
                "filled_at",
                "canceled_at",
                "canceled_by_user_id",
                "cancel_reason",
                "removed_at",
                "removed_by_user_id",
                "remove_reason",
                "created_at",
                "updated_at",
            )
        },
        "positions": [
            serialize_sub_post_position(db, position)
            for position in list_positions(db, sub_post.id)
        ],
        "pending_count": counts.get("pending", 0),
        "confirmed_count": counts.get("confirmed", 0),
        "sub_waitlist_count": counts.get("sub_waitlist", 0),
    }


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


def query_visible_posts(
    db: Session,
    city: str | None = None,
    state_value: str | None = None,
    starts_after: datetime | None = None,
    starts_before: datetime | None = None,
    skill_level: str | None = None,
    game_player_group: str | None = None,
    format_label: str | None = None,
    sport_type: str | None = None,
) -> list[SubPost]:
    statement = select(SubPost).where(
        SubPost.post_status.in_(ACTIVE_VISIBLE_POST_STATUSES),
        SubPost.starts_at >= now_utc(),
    )

    if city:
        statement = statement.where(SubPost.city == city)
    if state_value:
        statement = statement.where(SubPost.state == state_value)
    if starts_after:
        statement = statement.where(SubPost.starts_at >= ensure_aware(starts_after))
    if starts_before:
        statement = statement.where(SubPost.starts_at <= ensure_aware(starts_before))
    if skill_level:
        statement = statement.where(SubPost.skill_level == skill_level)
    if game_player_group:
        statement = statement.where(SubPost.game_player_group == game_player_group)
    if format_label:
        statement = statement.where(SubPost.format_label == format_label)
    if sport_type:
        statement = statement.where(SubPost.sport_type == sport_type)

    return list(db.scalars(statement.order_by(SubPost.starts_at.asc())).all())


def create_request(
    db: Session,
    requester: User,
    sub_post_id: uuid.UUID,
    sub_post_position_id: uuid.UUID,
) -> SubPostRequest:
    sub_post = get_sub_post_or_404(db, sub_post_id)
    position = get_position_or_404(db, sub_post_position_id)
    current_time = now_utc()

    if sub_post.post_status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requests can only be created for active posts.",
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

    initial_status = "pending" if count_queued_slots(db, position.id) < position.spots_needed else "sub_waitlist"
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


def recalculate_filled_status(
    db: Session,
    sub_post: SubPost,
    changed_by_user_id: uuid.UUID | None,
    change_source: str,
) -> None:
    db.flush()
    positions = list_positions(db, sub_post.id)
    is_filled = bool(positions) and all(position_is_filled(db, position) for position in positions)
    current_time = now_utc()
    post_change_source = normalize_post_status_change_source(change_source)

    if is_filled and sub_post.post_status == "active":
        old_status = sub_post.post_status
        sub_post.post_status = "filled"
        sub_post.filled_at = current_time
        sub_post.updated_at = current_time
        db.add(sub_post)
        add_post_status_history(
            db,
            sub_post,
            old_status,
            "filled",
            changed_by_user_id,
            post_change_source,
        )
    elif not is_filled and sub_post.post_status == "filled" and current_time < ensure_aware(sub_post.starts_at):
        old_status = sub_post.post_status
        sub_post.post_status = "active"
        sub_post.filled_at = None
        sub_post.updated_at = current_time
        db.add(sub_post)
        add_post_status_history(
            db,
            sub_post,
            old_status,
            "active",
            changed_by_user_id,
            post_change_source,
        )


def promote_next_waitlisted_request(
    db: Session,
    sub_post_position_id: uuid.UUID,
    changed_by_user_id: uuid.UUID | None,
    change_source: str,
) -> SubPostRequest | None:
    db.flush()
    position = get_position_or_404(db, sub_post_position_id)

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
    sub_request = get_sub_post_request_or_404(db, request_id)
    sub_post = get_sub_post_or_404(db, sub_request.sub_post_id)
    position = get_position_or_404(db, sub_request.sub_post_position_id)
    current_time = now_utc()
    require_owner(sub_post, owner)

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

    if count_queued_slots(db, position.id) > position.spots_needed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This position is already full.",
        )

    change_request_status(db, sub_request, "confirmed", owner.id, "owner", current_time=current_time)
    recalculate_filled_status(db, sub_post, owner.id, "owner")
    db.commit()
    db.refresh(sub_request)
    return sub_request


def owner_decline_request(
    db: Session, owner: User, request_id: uuid.UUID, reason: str | None = None
) -> SubPostRequest:
    sub_request = get_sub_post_request_or_404(db, request_id)
    sub_post = get_sub_post_or_404(db, sub_request.sub_post_id)
    require_owner(sub_post, owner)

    if sub_request.request_status not in {"pending", "sub_waitlist"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending or waitlisted requests can be declined.",
        )

    was_pending = sub_request.request_status == "pending"
    position_id = sub_request.sub_post_position_id
    change_request_status(db, sub_request, "declined", owner.id, "owner", reason)

    if was_pending:
        promote_next_waitlisted_request(db, position_id, owner.id, "owner")

    db.commit()
    db.refresh(sub_request)
    return sub_request


def requester_cancel_request(
    db: Session, requester: User, request_id: uuid.UUID
) -> SubPostRequest:
    sub_request = get_sub_post_request_or_404(db, request_id)
    sub_post = get_sub_post_or_404(db, sub_request.sub_post_id)

    if sub_request.requester_user_id != requester.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the requester can cancel this request.",
        )

    if sub_request.request_status not in ACTIVE_REQUEST_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This request cannot be canceled.",
        )

    should_promote = sub_request.request_status in {"pending", "confirmed"}
    was_confirmed = sub_request.request_status == "confirmed"
    position_id = sub_request.sub_post_position_id
    change_request_status(db, sub_request, "canceled_by_player", requester.id, "requester")

    if was_confirmed:
        recalculate_filled_status(db, sub_post, requester.id, "requester")
    if should_promote:
        promote_next_waitlisted_request(db, position_id, requester.id, "requester")

    db.commit()
    db.refresh(sub_request)
    return sub_request


def owner_cancel_request(
    db: Session,
    owner: User,
    request_id: uuid.UUID,
    reason: str | None = None,
) -> SubPostRequest:
    sub_request = get_sub_post_request_or_404(db, request_id)
    sub_post = get_sub_post_or_404(db, sub_request.sub_post_id)
    require_owner(sub_post, owner)

    if sub_request.request_status != "confirmed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only confirmed requests can be canceled by owner.",
        )

    position_id = sub_request.sub_post_position_id
    change_request_status(db, sub_request, "canceled_by_owner", owner.id, "owner", reason)

    recalculate_filled_status(db, sub_post, owner.id, "owner")
    promote_next_waitlisted_request(db, position_id, owner.id, "owner")

    db.commit()
    db.refresh(sub_request)
    return sub_request


def owner_report_no_show(
    db: Session,
    owner: User,
    request_id: uuid.UUID,
    reason: str | None = None,
) -> SubPostRequest:
    sub_request = get_sub_post_request_or_404(db, request_id)
    sub_post = get_sub_post_or_404(db, sub_request.sub_post_id)
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
    db.commit()
    db.refresh(sub_request)
    return sub_request


def cancel_sub_post(
    db: Session,
    owner: User,
    sub_post_id: uuid.UUID,
    reason: str | None = None,
) -> SubPost:
    sub_post = get_sub_post_or_404(db, sub_post_id)
    require_owner(sub_post, owner)

    if sub_post.post_status not in {"active", "filled"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only active or filled posts can be canceled.",
        )

    current_time = now_utc()
    old_status = sub_post.post_status
    sub_post.post_status = "canceled"
    sub_post.canceled_at = current_time
    sub_post.canceled_by_user_id = owner.id
    sub_post.cancel_reason = reason
    sub_post.updated_at = current_time
    db.add(sub_post)
    add_post_status_history(db, sub_post, old_status, "canceled", owner.id, "owner", reason)

    active_requests = db.scalars(
        select(SubPostRequest).where(
            SubPostRequest.sub_post_id == sub_post.id,
            SubPostRequest.request_status.in_(ACTIVE_REQUEST_STATUSES),
        )
    ).all()
    for sub_request in active_requests:
        change_request_status(
            db,
            sub_request,
            "canceled_by_owner",
            owner.id,
            "owner",
            "Post canceled by owner.",
            current_time,
        )

    db.commit()
    db.refresh(sub_post)
    return sub_post


def remove_sub_post(
    db: Session,
    admin_user: User,
    sub_post_id: uuid.UUID,
    reason: str | None = None,
) -> SubPost:
    require_admin(admin_user)
    sub_post = get_sub_post_or_404(db, sub_post_id)

    if sub_post.post_status == "removed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This post is already removed.",
        )

    old_status = sub_post.post_status
    current_time = now_utc()
    sub_post.post_status = "removed"
    sub_post.removed_at = current_time
    sub_post.removed_by_user_id = admin_user.id
    sub_post.remove_reason = reason
    sub_post.updated_at = current_time
    db.add(sub_post)
    add_post_status_history(
        db,
        sub_post,
        old_status,
        "removed",
        admin_user.id,
        "admin",
        reason,
    )
    db.commit()
    db.refresh(sub_post)
    return sub_post


def expire_due_posts_and_requests(db: Session) -> dict[str, int]:
    current_time = now_utc()
    expired_posts_count = 0
    expired_requests_count = 0

    posts = db.scalars(
        select(SubPost).where(
            SubPost.post_status.in_({"active", "filled"}),
            SubPost.expires_at <= current_time,
        )
    ).all()

    for sub_post in posts:
        old_status = sub_post.post_status
        sub_post.post_status = "expired"
        sub_post.updated_at = current_time
        db.add(sub_post)
        add_post_status_history(
            db,
            sub_post,
            old_status,
            "expired",
            None,
            "scheduled_job",
        )
        expired_posts_count += 1

    requests = db.scalars(
        select(SubPostRequest)
        .join(SubPost, SubPostRequest.sub_post_id == SubPost.id)
        .where(
            SubPost.expires_at <= current_time,
            SubPostRequest.request_status.in_({"pending", "sub_waitlist"}),
        )
    ).all()

    for sub_request in requests:
        change_request_status(
            db,
            sub_request,
            "expired",
            None,
            "scheduled_job",
            current_time=current_time,
        )
        expired_requests_count += 1

    db.commit()
    return {
        "posts_expired": expired_posts_count,
        "requests_expired": expired_requests_count,
    }
