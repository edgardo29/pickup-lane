import uuid
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    AdminAction,
    Notification,
    SubPost,
    SubPostPosition,
    SubPostRequest,
    SubPostRequestStatusHistory,
    SubPostStatusHistory,
    User,
)
from backend.schemas import (
    MAX_SUB_POST_POSITION_ROWS,
    MAX_SUB_POST_TOTAL_SUBS,
    SubPostCreate,
    SubPostUpdate,
)
from backend.services.admin_action_service import (
    normalize_idempotency_key,
    normalize_optional_text,
    record_admin_action,
)
from backend.services.admin_permission_service import PERMISSION_NEED_A_SUB_MODERATE
from backend.services.auth_service import require_user_admin_permission
from backend.services.notification_service import (
    build_need_a_sub_notification_fields,
    reopen_aggregated_notification,
    resolve_aggregated_notification,
)
from backend.services.sub_post_chat_service import (
    resolve_sub_chat_notifications_for_post,
    resolve_sub_chat_notifications_for_user as resolve_sub_chat_notification_for_user,
)

POST_STATUSES = {"active", "filled", "expired", "canceled", "removed"}
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
MAX_SUB_POST_SCHEDULE_DAYS_AHEAD = 14
VALID_FORMAT_LABELS = {
    "3v3",
    "4v4",
    "5v5",
    "6v6",
    "7v7",
    "8v8",
    "9v9",
    "10v10",
    "11v11",
}
VALID_SKILL_LEVELS = {
    "any",
    "beginner",
    "recreational",
    "intermediate",
    "advanced",
    "competitive",
}
VALID_ENVIRONMENT_TYPES = {"indoor", "outdoor"}
VALID_POSITION_LABELS = {"field_player", "goalkeeper"}
TERMINAL_REQUEST_STATUSES = {
    "declined",
    "canceled_by_player",
    "canceled_by_owner",
    "no_show_reported",
    "expired",
}
SUB_POST_UPDATED_RECIPIENT_STATUSES = {"pending", "confirmed", "sub_waitlist"}
SUB_POST_UPDATED_STRUCTURAL_FIELDS = (
    "starts_at",
    "ends_at",
    "location_name",
    "address_line_1",
    "city",
    "state",
    "postal_code",
    "neighborhood",
    "format_label",
    "environment_type",
    "skill_level",
    "game_player_group",
    "price_due_at_venue_cents",
)
POST_STATUS_CHANGE_SOURCES = {"owner", "admin", "system", "scheduled_job"}
VALID_POSITION_GROUPS_BY_POST_GROUP = {
    "men": {"men"},
    "women": {"women"},
    "coed": {"open", "men", "women"},
}
PLAYER_GROUP_DISPLAY_LABELS = {
    "open": "Any",
    "men": "Men's",
    "women": "Women's",
}
POSITION_DISPLAY_LABELS = {
    "field_player": "Field Player",
    "goalkeeper": "Goalkeeper",
}


def ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def now_utc() -> datetime:
    return datetime.now(UTC)


def get_local_date(value: datetime, timezone: str | None) -> date:
    try:
        local_timezone = ZoneInfo(timezone or "UTC")
    except ZoneInfoNotFoundError:
        local_timezone = UTC

    return ensure_aware(value).astimezone(local_timezone).date()


def get_sub_post_or_404(db: Session, sub_post_id: uuid.UUID) -> SubPost:
    sub_post = db.get(SubPost, sub_post_id)

    if sub_post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub post not found.",
        )

    return sub_post


def get_sub_post_for_update_or_404(db: Session, sub_post_id: uuid.UUID) -> SubPost:
    sub_post = db.scalar(
        select(SubPost)
        .where(SubPost.id == sub_post_id)
        .with_for_update()
    )

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


def get_position_or_404(
    db: Session,
    position_id: uuid.UUID,
    lock_for_update: bool = False,
) -> SubPostPosition:
    if lock_for_update:
        position = db.scalar(
            select(SubPostPosition)
            .where(SubPostPosition.id == position_id)
            .with_for_update()
        )
    else:
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


def require_before_post_start(sub_post: SubPost, detail: str) -> None:
    if now_utc() >= ensure_aware(sub_post.starts_at):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )


def require_live_sub_post(sub_post: SubPost, detail: str) -> None:
    if sub_post.post_status not in ACTIVE_VISIBLE_POST_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
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
    current_time = now_utc()

    if starts_at <= current_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="starts_at must be in the future.",
        )

    if starts_at > current_time + timedelta(days=MAX_SUB_POST_SCHEDULE_DAYS_AHEAD):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Need a Sub posts can be scheduled up to 14 days in advance."
            ),
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

    if post_create.format_label not in VALID_FORMAT_LABELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="format_label is not supported.",
        )

    if post_create.environment_type not in VALID_ENVIRONMENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="environment_type is not supported.",
        )

    if post_create.skill_level not in VALID_SKILL_LEVELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="skill_level is not supported.",
        )

    if post_create.game_player_group not in VALID_POSITION_GROUPS_BY_POST_GROUP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="game_player_group is not supported.",
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

    if post_create.subs_needed > MAX_SUB_POST_TOTAL_SUBS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Need a Sub posts can include up to {MAX_SUB_POST_TOTAL_SUBS} total subs.",
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

    if len(post_create.positions) > MAX_SUB_POST_POSITION_ROWS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Need a Sub posts can include up to {MAX_SUB_POST_POSITION_ROWS} sub requirements.",
        )

    total_spots = sum(position.spots_needed for position in post_create.positions)
    if total_spots != post_create.subs_needed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Position spots must add up to subs_needed.",
        )

    seen_position_keys = set()
    groups_by_position_label: dict[str, set[str]] = {}
    for position in post_create.positions:
        if position.position_label not in VALID_POSITION_LABELS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="position_label is not supported.",
            )

        position_key = (position.position_label, position.player_group)
        if position_key in seen_position_keys:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Each position and player group row must be unique.",
            )
        seen_position_keys.add(position_key)
        groups_by_position_label.setdefault(position.position_label, set()).add(position.player_group)

    for position_label, groups in groups_by_position_label.items():
        if "open" in groups and ({"men", "women"} & groups):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Any player rows cannot be combined with Men or Women rows "
                    "for the same position."
                ),
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


def validate_owner_live_post_date_limit(
    db: Session,
    owner_user_id: uuid.UUID,
    starts_on_local: date,
    exclude_sub_post_id: uuid.UUID | None = None,
) -> None:
    statement = select(SubPost).where(
        SubPost.owner_user_id == owner_user_id,
        SubPost.starts_on_local == starts_on_local,
        SubPost.post_status.in_(ACTIVE_VISIBLE_POST_STATUSES),
    )

    if exclude_sub_post_id is not None:
        statement = statement.where(SubPost.id != exclude_sub_post_id)

    existing_post = db.scalar(statement.limit(1))
    if existing_post is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "You already have an active Need a Sub post for this date."
            ),
        )


def create_sub_post(
    db: Session, owner: User, post_create: SubPostCreate
) -> SubPost:
    expire_due_posts_and_requests(db)
    validate_post_creation(post_create)
    post_data = post_create.model_dump(exclude={"positions"})
    post_data["starts_at"] = ensure_aware(post_create.starts_at)
    post_data["ends_at"] = ensure_aware(post_create.ends_at)
    post_data["starts_on_local"] = get_local_date(
        post_data["starts_at"],
        post_data["timezone"],
    )
    validate_owner_live_post_date_limit(
        db,
        owner.id,
        post_data["starts_on_local"],
    )
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
            "environment_type",
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


def validate_edit_keeps_post_date(
    sub_post: SubPost,
    post_update: SubPostUpdate,
) -> None:
    existing_date = sub_post.starts_on_local or get_local_date(
        sub_post.starts_at,
        sub_post.timezone,
    )
    effective_timezone = (
        post_update.timezone
        if "timezone" in post_update.model_fields_set and post_update.timezone
        else sub_post.timezone
    )
    effective_starts_at = (
        post_update.starts_at
        if "starts_at" in post_update.model_fields_set and post_update.starts_at
        else sub_post.starts_at
    )

    if get_local_date(effective_starts_at, effective_timezone) != existing_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Post date cannot be changed.",
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
    sub_post = get_sub_post_for_update_or_404(db, sub_post_id)
    require_owner(sub_post, owner)

    if sub_post.post_status not in {"active", "filled"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only active or filled posts can be edited.",
        )

    require_before_post_start(sub_post, "Posts cannot be edited after the game starts.")
    validate_edit_keeps_post_date(sub_post, post_update)

    effective_post = build_effective_post_create(db, sub_post, post_update)
    validate_post_creation(effective_post)
    next_starts_on_local = get_local_date(
        effective_post.starts_at,
        effective_post.timezone,
    )
    validate_owner_live_post_date_limit(
        db,
        owner.id,
        next_starts_on_local,
        exclude_sub_post_id=sub_post.id,
    )
    update_data = post_update.model_dump(exclude_unset=True, exclude={"positions"})
    new_positions = post_update.positions if "positions" in post_update.model_fields_set else None

    current_time = now_utc()
    structural_snapshot_before = capture_sub_post_structural_snapshot(sub_post)
    for field_name, field_value in update_data.items():
        setattr(sub_post, field_name, field_value)

    if new_positions is not None:
        sub_post.subs_needed = sum(position.spots_needed for position in new_positions)
        apply_position_updates(db, sub_post, new_positions)

    sub_post.starts_at = ensure_aware(sub_post.starts_at)
    sub_post.ends_at = ensure_aware(sub_post.ends_at)
    sub_post.starts_on_local = next_starts_on_local
    sub_post.expires_at = sub_post.starts_at
    sub_post.updated_at = current_time
    db.add(sub_post)
    recalculate_filled_status(db, sub_post, owner.id, "owner")
    if sub_post_structural_snapshot_changed(structural_snapshot_before, sub_post):
        notify_active_requesters_sub_post_updated(
            db,
            sub_post=sub_post,
            actor_user_id=owner.id,
            event_at=current_time,
        )

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
                "environment_type",
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


def serialize_public_sub_post(db: Session, sub_post: SubPost) -> dict:
    counts = count_requests_by_status(db, sub_post.id)
    return {
        **{
            field: getattr(sub_post, field)
            for field in (
                "id",
                "post_status",
                "sport_type",
                "format_label",
                "environment_type",
                "skill_level",
                "game_player_group",
                "starts_at",
                "ends_at",
                "timezone",
                "location_name",
                "city",
                "state",
                "neighborhood",
                "subs_needed",
                "price_due_at_venue_cents",
                "currency",
                "expires_at",
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


def is_publicly_visible_sub_post(sub_post: SubPost) -> bool:
    return (
        sub_post.post_status in ACTIVE_VISIBLE_POST_STATUSES
        and ensure_aware(sub_post.starts_at) >= now_utc()
    )


def user_can_view_private_sub_post(
    db: Session,
    sub_post: SubPost,
    user: User | None,
) -> bool:
    if user is None:
        return False

    if is_publicly_visible_sub_post(sub_post):
        return True

    if sub_post.post_status not in {"active", "filled", "expired"}:
        return False

    chat_access_closes_at = ensure_aware(sub_post.ends_at) + timedelta(hours=24)
    if now_utc() > chat_access_closes_at:
        return False

    if sub_post.owner_user_id == user.id:
        return True

    return (
        db.scalar(
            select(SubPostRequest.id).where(
                SubPostRequest.sub_post_id == sub_post.id,
                SubPostRequest.requester_user_id == user.id,
                SubPostRequest.request_status == "confirmed",
            )
        )
        is not None
    )


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
    position = get_position_or_404(db, sub_request.sub_post_position_id)
    notify_owner_sub_request_received(
        db,
        sub_post,
        position,
        sub_request,
        sub_request.requester_user_id,
        event_at=promotion_time,
    )


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
    require_live_sub_post(sub_post, "Only active or filled posts can be reviewed.")
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


def query_visible_posts(
    db: Session,
    city: str | None = None,
    state_value: str | None = None,
    starts_after: datetime | None = None,
    starts_before: datetime | None = None,
    skill_level: str | None = None,
    game_player_group: str | None = None,
    format_label: str | None = None,
    environment_type: str | None = None,
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
    if environment_type:
        statement = statement.where(SubPost.environment_type == environment_type)
    if sport_type:
        statement = statement.where(SubPost.sport_type == sport_type)

    return list(db.scalars(statement.order_by(SubPost.starts_at.asc())).all())


def query_owner_posts(db: Session, owner: User) -> list[SubPost]:
    current_time = now_utc()

    return list(
        db.scalars(
            select(SubPost)
            .where(
                SubPost.owner_user_id == owner.id,
                SubPost.post_status.in_(ACTIVE_VISIBLE_POST_STATUSES),
                SubPost.starts_at >= current_time,
            )
            .order_by(SubPost.starts_at.desc(), SubPost.created_at.desc())
        ).all()
    )


def create_request(
    db: Session,
    requester: User,
    sub_post_id: uuid.UUID,
    sub_post_position_id: uuid.UUID,
) -> SubPostRequest:
    sub_post = get_sub_post_for_update_or_404(db, sub_post_id)
    position = get_position_or_404(db, sub_post_position_id, lock_for_update=True)
    current_time = now_utc()

    if sub_post.post_status not in {"active", "filled"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requests can only be created for open posts.",
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

    if count_queued_slots(db, position.id) > position.spots_needed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This position is already full.",
        )

    change_request_status(db, sub_request, "confirmed", owner.id, "owner", current_time=current_time)
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
    sub_request, sub_post = get_sub_post_request_and_post_for_update(db, request_id)
    require_owner(sub_post, owner)
    require_live_sub_post(sub_post, "Only active or filled posts can be reviewed.")
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
    sub_request, sub_post = get_sub_post_request_and_post_for_update(db, request_id)

    if sub_request.requester_user_id != requester.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the requester can cancel this request.",
        )
    require_before_post_start(sub_post, "Requests cannot be canceled after the game starts.")
    require_live_sub_post(sub_post, "Only active or filled posts can be updated.")

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
    sub_request, sub_post = get_sub_post_request_and_post_for_update(db, request_id)
    require_owner(sub_post, owner)
    require_before_post_start(sub_post, "Confirmed players cannot be removed after the game starts.")
    require_live_sub_post(sub_post, "Only active or filled posts can be reviewed.")

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


def cancel_sub_post(
    db: Session,
    owner: User,
    sub_post_id: uuid.UUID,
    reason: str | None = None,
) -> SubPost:
    sub_post = get_sub_post_for_update_or_404(db, sub_post_id)
    require_owner(sub_post, owner)

    if sub_post.post_status not in {"active", "filled"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only active or filled posts can be canceled.",
        )

    require_before_post_start(sub_post, "Posts cannot be canceled after the game starts.")

    current_time = now_utc()
    old_status = sub_post.post_status
    sub_post.post_status = "canceled"
    sub_post.canceled_at = current_time
    sub_post.canceled_by_user_id = owner.id
    sub_post.cancel_reason = reason
    sub_post.updated_at = current_time
    db.add(sub_post)
    add_post_status_history(db, sub_post, old_status, "canceled", owner.id, "owner", reason)
    resolve_sub_chat_notifications_for_post(
        db,
        sub_post_id=sub_post.id,
        read_at=current_time,
    )

    active_requests = db.scalars(
        select(SubPostRequest).where(
            SubPostRequest.sub_post_id == sub_post.id,
            SubPostRequest.request_status.in_(ACTIVE_REQUEST_STATUSES),
        )
    ).all()
    for sub_request in active_requests:
        previous_status = sub_request.request_status
        change_request_status(
            db,
            sub_request,
            "canceled_by_owner",
            owner.id,
            "owner",
            "Post canceled by owner.",
            current_time,
        )
        if previous_status == "pending":
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
            notification_type="sub_post_canceled",
            title=None,
            body=None,
            actor_user_id=owner.id,
        )

    db.commit()
    db.refresh(sub_post)
    return sub_post


def get_existing_remove_sub_post_action(
    db: Session,
    *,
    admin_user_id: uuid.UUID,
    sub_post_id: uuid.UUID,
    idempotency_key: str,
) -> AdminAction | None:
    return db.scalar(
        select(AdminAction)
        .where(
            AdminAction.action_type == "remove_sub_post",
            AdminAction.admin_user_id == admin_user_id,
            AdminAction.target_sub_post_id == sub_post_id,
            AdminAction.idempotency_key == idempotency_key,
        )
        .order_by(AdminAction.created_at.desc(), AdminAction.id.desc())
        .limit(1)
    )


def validate_remove_sub_post_replay(
    action: AdminAction,
    *,
    expected_reason: str,
) -> None:
    if action.reason != expected_reason:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "idempotency_key was already used for a different "
                "Need a Sub removal request."
            ),
        )


def get_removed_sub_post_replay_result(
    db: Session,
    *,
    action: AdminAction,
    sub_post_id: uuid.UUID,
    expected_reason: str,
) -> SubPost:
    validate_remove_sub_post_replay(action, expected_reason=expected_reason)
    sub_post = db.get(SubPost, sub_post_id)
    if sub_post is None or sub_post.post_status != "removed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Removal audit exists but the Need a Sub post is not removed.",
        )
    return sub_post


def remove_sub_post(
    db: Session,
    admin_user: User,
    sub_post_id: uuid.UUID,
    reason: str | None = None,
    idempotency_key_value: str | None = None,
) -> SubPost:
    require_user_admin_permission(admin_user, PERMISSION_NEED_A_SUB_MODERATE)
    normalized_reason = normalize_optional_text(reason, "remove_reason")
    if normalized_reason is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="remove_sub_post requires a reason.",
        )
    idempotency_key = normalize_idempotency_key(idempotency_key_value)
    if idempotency_key is None or len(idempotency_key) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="idempotency_key must be at least 8 characters.",
        )

    existing_action = get_existing_remove_sub_post_action(
        db,
        admin_user_id=admin_user.id,
        sub_post_id=sub_post_id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        return get_removed_sub_post_replay_result(
            db,
            action=existing_action,
            sub_post_id=sub_post_id,
            expected_reason=normalized_reason,
        )

    sub_post = get_sub_post_for_update_or_404(db, sub_post_id)
    existing_action = get_existing_remove_sub_post_action(
        db,
        admin_user_id=admin_user.id,
        sub_post_id=sub_post.id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        return get_removed_sub_post_replay_result(
            db,
            action=existing_action,
            sub_post_id=sub_post.id,
            expected_reason=normalized_reason,
        )

    if sub_post.post_status == "removed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This post is already removed.",
        )

    old_status = sub_post.post_status
    actor_role = "moderator" if admin_user.role == "moderator" else "admin"
    current_time = now_utc()
    record_admin_action(
        db,
        admin_user_id=admin_user.id,
        action_type="remove_sub_post",
        target_user_id=sub_post.owner_user_id,
        target_sub_post_id=sub_post.id,
        reason=normalized_reason,
        metadata={
            "source": "need_a_sub",
            "old_status": old_status,
            "new_status": "removed",
            "removed_by": actor_role,
        },
        idempotency_key=idempotency_key,
        created_at=current_time,
    )

    sub_post.post_status = "removed"
    sub_post.removed_at = current_time
    sub_post.removed_by_user_id = admin_user.id
    sub_post.remove_reason = normalized_reason
    sub_post.updated_at = current_time
    db.add(sub_post)
    add_post_status_history(
        db,
        sub_post,
        old_status,
        "removed",
        admin_user.id,
        "admin",
        normalized_reason,
    )
    resolve_sub_chat_notifications_for_post(
        db,
        sub_post_id=sub_post.id,
        read_at=current_time,
    )
    add_need_a_sub_notification(
        db,
        recipient_user_id=sub_post.owner_user_id,
        notification_type="sub_post_removed",
        sub_post=sub_post,
        actor_user_id=admin_user.id,
        event_at=current_time,
    )

    active_requests = db.scalars(
        select(SubPostRequest).where(
            SubPostRequest.sub_post_id == sub_post.id,
            SubPostRequest.request_status.in_(ACTIVE_REQUEST_STATUSES),
        )
    ).all()
    for sub_request in active_requests:
        previous_status = sub_request.request_status
        change_request_status(
            db,
            sub_request,
            "canceled_by_owner",
            admin_user.id,
            "admin",
            normalized_reason,
            current_time,
        )
        if previous_status == "pending":
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
            notification_type="sub_post_removed",
            title=None,
            body=None,
            actor_user_id=admin_user.id,
            event_at=current_time,
        )

    try:
        db.commit()
        db.refresh(sub_post)
        return sub_post
    except IntegrityError as exc:
        db.rollback()
        existing_action = get_existing_remove_sub_post_action(
            db,
            admin_user_id=admin_user.id,
            sub_post_id=sub_post_id,
            idempotency_key=idempotency_key,
        )
        if existing_action is not None:
            return get_removed_sub_post_replay_result(
                db,
                action=existing_action,
                sub_post_id=sub_post_id,
                expected_reason=normalized_reason,
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Need a Sub post could not be removed.",
        ) from exc


def expire_due_posts_and_requests(db: Session) -> dict[str, int]:
    current_time = now_utc()
    expired_posts_count = 0
    expired_requests_count = 0

    posts = db.scalars(
        select(SubPost).where(
            SubPost.post_status.in_({"active", "filled"}),
            SubPost.expires_at <= current_time,
        ).with_for_update()
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
        "posts_expired": expired_posts_count,
        "requests_expired": expired_requests_count,
    }
