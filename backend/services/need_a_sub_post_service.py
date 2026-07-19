"""Need a Sub post, position, visibility, and moderation workflows."""

import uuid
from base64 import urlsafe_b64decode, urlsafe_b64encode
from binascii import Error as BinasciiError
from datetime import date, datetime, timedelta
from json import JSONDecodeError, dumps, loads

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    AdminAction,
    AdminTargetNotice,
    SubPost,
    SubPostPosition,
    SubPostRequest,
    User,
)
from backend.schemas.sub_post_schema import (
    MAX_SUB_POST_POSITION_ROWS,
    MAX_SUB_POST_TOTAL_SUBS,
    SubPostCreate,
    SubPostListRead,
    SubPostUpdate,
)
from backend.services.admin_action_service import record_admin_action
from backend.services.admin_record_rules import (
    normalize_idempotency_key,
    normalize_optional_text,
)
from backend.services.admin_review_service import (
    close_open_content_moderation_case_for_sub_post_lifecycle,
)
from backend.services.admin_target_notice_service import create_admin_target_notice
from backend.services.auth_service import require_active_admin_user
from backend.services.need_a_sub_lifecycle_service import (
    add_post_status_history,
    change_request_status,
    expire_due_posts_and_requests,
    recalculate_filled_status,
)
from backend.services.need_a_sub_notification_service import (
    add_need_a_sub_notification,
    capture_sub_post_structural_snapshot,
    notify_active_requesters_sub_post_updated,
    notify_requester_sub_status,
    resolve_owner_request_activity_notification,
    sub_post_structural_snapshot_changed,
)
from backend.services.moderation_surfacing_service import surface_need_a_sub_post_text
from backend.services.need_a_sub_rules import (
    ACTIVE_REQUEST_STATUSES,
    ACTIVE_VISIBLE_POST_STATUSES,
    MAX_SUB_POST_SCHEDULE_DAYS_AHEAD,
    TERMINAL_REQUEST_STATUSES,
    VALID_ENVIRONMENT_TYPES,
    VALID_FORMAT_LABELS,
    VALID_POSITION_GROUPS_BY_POST_GROUP,
    VALID_POSITION_LABELS,
    VALID_SKILL_LEVELS,
    ensure_aware,
    get_local_date,
    now_utc,
    require_before_post_start,
    sub_post_is_publicly_visible,
)
from backend.services.sub_post_chat_service import (
    close_sub_post_chat_for_post,
    resolve_sub_chat_notifications_for_post,
)

SUB_POST_CARD_DEFAULT_LIMIT = 40
SUB_POST_CARD_MAX_LIMIT = 100
SUB_POST_CARD_VALID_VIEWS = {"all", "mine"}


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
        groups_by_position_label.setdefault(position.position_label, set()).add(
            position.player_group
        )

    for groups in groups_by_position_label.values():
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


def create_sub_post(db: Session, owner: User, post_create: SubPostCreate) -> SubPost:
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

    surface_need_a_sub_post_text(db, sub_post_id=new_post.id)
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


def list_positions(db: Session, sub_post_id: uuid.UUID) -> list[SubPostPosition]:
    return list(
        db.scalars(
            select(SubPostPosition)
            .where(SubPostPosition.sub_post_id == sub_post_id)
            .order_by(SubPostPosition.sort_order.asc(), SubPostPosition.created_at.asc())
        ).all()
    )


def build_effective_post_create(
    db: Session,
    sub_post: SubPost,
    post_update: SubPostUpdate,
) -> SubPostCreate:
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

    if sub_post.post_status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only active posts can be edited.",
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

    surface_need_a_sub_post_text(db, sub_post_id=sub_post.id)
    return sub_post


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
                "public_visibility_status",
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
                "public_visibility_status",
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
    return sub_post_is_publicly_visible(sub_post)


def user_can_view_private_sub_post(
    db: Session,
    sub_post: SubPost,
    user: User | None,
) -> bool:
    if user is None:
        return False

    if is_publicly_visible_sub_post(sub_post):
        return True

    if sub_post.post_status not in {"active", "completed", "expired"}:
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
        SubPost.public_visibility_status == "visible",
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


def list_sub_post_cards(
    db: Session,
    *,
    view: str = "all",
    starts_on: date,
    current_user: User | None = None,
    limit: int = SUB_POST_CARD_DEFAULT_LIMIT,
    cursor: str | None = None,
) -> SubPostListRead:
    expire_due_posts_and_requests(db)

    if view not in SUB_POST_CARD_VALID_VIEWS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="view must be 'all' or 'mine'.",
        )

    if view == "mine" and current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in to view your Need a Sub posts.",
        )

    effective_limit = min(limit, SUB_POST_CARD_MAX_LIMIT)
    cursor_payload = decode_sub_post_card_cursor(cursor) if cursor else None
    validate_sub_post_card_cursor_context(
        cursor_payload,
        starts_on=starts_on,
        view=view,
    )

    statement = select(SubPost).where(
        SubPost.post_status.in_(ACTIVE_VISIBLE_POST_STATUSES),
        SubPost.public_visibility_status == "visible",
        SubPost.starts_on_local == starts_on,
        SubPost.starts_at >= now_utc(),
    )

    if view == "mine":
        statement = statement.where(SubPost.owner_user_id == current_user.id)

    if cursor_payload is not None:
        statement = statement.where(build_sub_post_card_cursor_filter(cursor_payload))

    statement = statement.order_by(
        SubPost.starts_at.asc(),
        SubPost.created_at.asc(),
        SubPost.id.asc(),
    )

    posts = list(db.scalars(statement.limit(effective_limit + 1)).all())
    page_posts = posts[:effective_limit]
    has_more = len(posts) > effective_limit
    next_cursor = None

    if has_more and page_posts:
        next_cursor = encode_sub_post_card_cursor(
            post=page_posts[-1],
            starts_on=starts_on,
            view=view,
        )

    return SubPostListRead(
        posts=serialize_public_sub_posts_for_list(db, page_posts),
        next_cursor=next_cursor,
        has_more=has_more,
        limit=effective_limit,
    )


def encode_sub_post_card_cursor(
    *,
    post: SubPost,
    starts_on: date,
    view: str,
) -> str:
    payload = {
        "view": view,
        "starts_on": starts_on.isoformat(),
        "starts_at": post.starts_at.isoformat(),
        "created_at": post.created_at.isoformat(),
        "id": str(post.id),
    }
    serialized = dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return urlsafe_b64encode(serialized).decode("ascii")


def decode_sub_post_card_cursor(cursor: str | None) -> dict[str, object] | None:
    if cursor is None:
        return None

    try:
        decoded = urlsafe_b64decode(cursor.encode("ascii"))
        payload = loads(decoded.decode("utf-8"))
    except (BinasciiError, JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor is invalid.",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor is invalid.",
        )

    required_keys = {"view", "starts_on", "starts_at", "created_at", "id"}
    if not required_keys.issubset(payload.keys()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor is invalid.",
        )

    return payload


def validate_sub_post_card_cursor_context(
    cursor_payload: dict[str, object] | None,
    *,
    starts_on: date,
    view: str,
) -> None:
    if cursor_payload is None:
        return

    if (
        cursor_payload["starts_on"] != starts_on.isoformat()
        or cursor_payload["view"] != view
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor does not match the current query.",
        )


def build_sub_post_card_cursor_filter(cursor_payload: dict[str, object]):
    starts_at = parse_sub_post_card_cursor_datetime(cursor_payload, "starts_at")
    created_at = parse_sub_post_card_cursor_datetime(cursor_payload, "created_at")
    post_id = parse_sub_post_card_cursor_uuid(cursor_payload)

    return or_(
        SubPost.starts_at > starts_at,
        and_(SubPost.starts_at == starts_at, SubPost.created_at > created_at),
        and_(
            SubPost.starts_at == starts_at,
            SubPost.created_at == created_at,
            SubPost.id > post_id,
        ),
    )


def parse_sub_post_card_cursor_datetime(
    cursor_payload: dict[str, object],
    key: str,
) -> datetime:
    value = cursor_payload[key]
    if not isinstance(value, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor is invalid.",
        )

    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor is invalid.",
        ) from exc


def parse_sub_post_card_cursor_uuid(cursor_payload: dict[str, object]) -> uuid.UUID:
    value = cursor_payload["id"]
    if not isinstance(value, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor is invalid.",
        )

    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor is invalid.",
        ) from exc


def serialize_public_sub_posts_for_list(
    db: Session,
    posts: list[SubPost],
) -> list[dict]:
    if not posts:
        return []

    post_ids = [post.id for post in posts]
    request_counts_by_post: dict[uuid.UUID, dict[str, int]] = {}
    request_counts_by_position: dict[uuid.UUID, dict[str, int]] = {}
    positions_by_post: dict[uuid.UUID, list[dict]] = {}

    for post_id, request_status, count in db.execute(
        select(
            SubPostRequest.sub_post_id,
            SubPostRequest.request_status,
            func.count(),
        )
        .where(SubPostRequest.sub_post_id.in_(post_ids))
        .group_by(SubPostRequest.sub_post_id, SubPostRequest.request_status)
    ).all():
        request_counts_by_post.setdefault(post_id, {})[request_status] = count

    positions = list(
        db.scalars(
            select(SubPostPosition)
            .where(SubPostPosition.sub_post_id.in_(post_ids))
            .order_by(
                SubPostPosition.sub_post_id.asc(),
                SubPostPosition.sort_order.asc(),
                SubPostPosition.created_at.asc(),
            )
        ).all()
    )
    position_ids = [position.id for position in positions]

    if position_ids:
        for position_id, request_status, count in db.execute(
            select(
                SubPostRequest.sub_post_position_id,
                SubPostRequest.request_status,
                func.count(),
            )
            .where(SubPostRequest.sub_post_position_id.in_(position_ids))
            .group_by(
                SubPostRequest.sub_post_position_id,
                SubPostRequest.request_status,
            )
        ).all():
            request_counts_by_position.setdefault(position_id, {})[
                request_status
            ] = count

    for position in positions:
        counts = request_counts_by_position.get(position.id, {})
        positions_by_post.setdefault(position.sub_post_id, []).append(
            {
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
        )

    serialized_posts = []
    for post in posts:
        counts = request_counts_by_post.get(post.id, {})
        serialized_posts.append(
            {
                **{
                    field: getattr(post, field)
                    for field in (
                        "id",
                        "post_status",
                        "public_visibility_status",
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
                "positions": positions_by_post.get(post.id, []),
                "pending_count": counts.get("pending", 0),
                "confirmed_count": counts.get("confirmed", 0),
                "sub_waitlist_count": counts.get("sub_waitlist", 0),
            }
        )

    return serialized_posts


def create_sub_post_workflow(
    db: Session,
    owner: User,
    post_create: SubPostCreate,
) -> dict:
    return serialize_sub_post(db, create_sub_post(db, owner, post_create))


def list_visible_sub_posts(
    db: Session,
    *,
    city: str | None = None,
    state_value: str | None = None,
    starts_after: datetime | None = None,
    starts_before: datetime | None = None,
    skill_level: str | None = None,
    game_player_group: str | None = None,
    format_label: str | None = None,
    environment_type: str | None = None,
    sport_type: str | None = None,
) -> list[dict]:
    expire_due_posts_and_requests(db)
    posts = query_visible_posts(
        db,
        city=city,
        state_value=state_value,
        starts_after=starts_after,
        starts_before=starts_before,
        skill_level=skill_level,
        game_player_group=game_player_group,
        format_label=format_label,
        environment_type=environment_type,
        sport_type=sport_type,
    )
    return [serialize_public_sub_post(db, post) for post in posts]


def list_owner_sub_posts(db: Session, owner: User) -> list[dict]:
    expire_due_posts_and_requests(db)
    posts = query_owner_posts(db, owner)
    return [serialize_sub_post(db, post) for post in posts]


def get_visible_sub_post_detail(
    db: Session,
    sub_post_id: uuid.UUID,
    current_user: User | None,
) -> dict:
    expire_due_posts_and_requests(db)
    sub_post = get_sub_post_or_404(db, sub_post_id)

    if user_can_view_private_sub_post(db, sub_post, current_user):
        return serialize_sub_post(db, sub_post)

    if not is_publicly_visible_sub_post(sub_post):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub post not found.",
        )

    return serialize_public_sub_post(db, sub_post)


def update_sub_post_workflow(
    db: Session,
    owner: User,
    sub_post_id: uuid.UUID,
    post_update: SubPostUpdate,
) -> dict:
    expire_due_posts_and_requests(db)
    return serialize_sub_post(db, update_sub_post(db, owner, sub_post_id, post_update))


def cancel_sub_post(
    db: Session,
    owner: User,
    sub_post_id: uuid.UUID,
    reason: str | None = None,
) -> SubPost:
    sub_post = get_sub_post_for_update_or_404(db, sub_post_id)
    require_owner(sub_post, owner)

    if sub_post.post_status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only active posts can be cancelled.",
        )

    require_before_post_start(sub_post, "Posts cannot be cancelled after the game starts.")

    current_time = now_utc()
    old_status = sub_post.post_status
    sub_post.post_status = "cancelled"
    sub_post.canceled_at = current_time
    sub_post.canceled_by_user_id = owner.id
    sub_post.cancel_reason = reason
    sub_post.updated_at = current_time
    db.add(sub_post)
    add_post_status_history(db, sub_post, old_status, "cancelled", owner.id, "owner", reason)
    close_open_content_moderation_case_for_sub_post_lifecycle(
        db,
        sub_post_id=sub_post.id,
        closure_outcome="no_action_needed",
        closure_reason=(
            "Need a Sub post was cancelled by its owner before moderation "
            "review was completed."
        ),
        lifecycle_action="owner_cancelled",
        trigger_actor_type="owner",
        trigger_actor_user_id=owner.id,
        previous_post_status=old_status,
        new_post_status="cancelled",
        closed_at=current_time,
    )
    close_sub_post_chat_for_post(
        db,
        sub_post_id=sub_post.id,
        closed_at=current_time,
    )
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
            "Post cancelled by owner.",
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


def cancel_sub_post_workflow(
    db: Session,
    owner: User,
    sub_post_id: uuid.UUID,
    reason: str | None = None,
) -> dict:
    expire_due_posts_and_requests(db)
    return serialize_sub_post(db, cancel_sub_post(db, owner, sub_post_id, reason))


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


def get_notice_ids_for_admin_action(
    db: Session,
    admin_action_id: uuid.UUID,
) -> list[uuid.UUID]:
    return list(
        db.scalars(
            select(AdminTargetNotice.id)
            .where(AdminTargetNotice.admin_action_id == admin_action_id)
            .order_by(AdminTargetNotice.created_at.asc(), AdminTargetNotice.id.asc())
        ).all()
    )


def remove_sub_post(
    db: Session,
    admin_user: User,
    sub_post_id: uuid.UUID,
    reason: str | None = None,
    idempotency_key_value: str | None = None,
) -> SubPost:
    require_active_admin_user(admin_user)
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
    current_time = now_utc()
    audit_action = record_admin_action(
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
            "removed_by": "admin",
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
    close_open_content_moderation_case_for_sub_post_lifecycle(
        db,
        sub_post_id=sub_post.id,
        closure_outcome="enforcement_applied",
        closure_reason=(
            "Need a Sub post was removed by an admin before moderation "
            "review was completed."
        ),
        lifecycle_action="admin_removed",
        trigger_actor_type="admin",
        trigger_actor_user_id=admin_user.id,
        closed_by_user_id=admin_user.id,
        admin_action=audit_action,
        previous_post_status=old_status,
        new_post_status="removed",
        closed_at=current_time,
    )
    close_sub_post_chat_for_post(
        db,
        sub_post_id=sub_post.id,
        closed_at=current_time,
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
    owner_notice = create_admin_target_notice(
        db,
        notice_type="need_sub_post_removed",
        title="Need a Sub post removed",
        body="Your Need a Sub post was removed by Pickup Lane admin.",
        recipient_user_id=sub_post.owner_user_id,
        target_user_id=sub_post.owner_user_id,
        target_sub_post_id=sub_post.id,
        admin_action=audit_action,
        created_by_user_id=admin_user.id,
        user_safe_reason=normalized_reason,
    )

    active_requests = db.scalars(
        select(SubPostRequest).where(
            SubPostRequest.sub_post_id == sub_post.id,
            SubPostRequest.request_status.in_(ACTIVE_REQUEST_STATUSES),
        )
    ).all()
    closed_request_ids: list[str] = []
    requester_notices: list[AdminTargetNotice] = []
    for sub_request in active_requests:
        previous_status = sub_request.request_status
        change_request_status(
            db,
            sub_request,
            "closed_by_admin",
            admin_user.id,
            "admin",
            normalized_reason,
            current_time,
        )
        closed_request_ids.append(str(sub_request.id))
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
        requester_notices.append(
            create_admin_target_notice(
                db,
                notice_type="need_sub_post_removed",
                title="Need a Sub request closed",
                body="A Need a Sub post you requested was removed by Pickup Lane admin.",
                recipient_user_id=sub_request.requester_user_id,
                target_user_id=sub_request.requester_user_id,
                target_sub_post_id=sub_post.id,
                target_sub_post_request_id=sub_request.id,
                admin_action=audit_action,
                created_by_user_id=admin_user.id,
                user_safe_reason=normalized_reason,
            )
        )
    db.flush()
    notice_ids = [owner_notice.id, *(notice.id for notice in requester_notices)]
    metadata = dict(audit_action.metadata_ or {})
    metadata["notice_ids"] = [str(notice_id) for notice_id in notice_ids]
    metadata["closed_request_ids"] = closed_request_ids
    audit_action.metadata_ = metadata

    try:
        db.add(audit_action)
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


def remove_sub_post_workflow(
    db: Session,
    admin_user: User,
    sub_post_id: uuid.UUID,
    reason: str | None = None,
    idempotency_key_value: str | None = None,
) -> dict:
    expire_due_posts_and_requests(db)
    return serialize_sub_post(
        db,
        remove_sub_post(
            db,
            admin_user,
            sub_post_id,
            reason,
            idempotency_key_value,
        ),
    )


def list_public_sub_post_positions(db: Session, sub_post_id: uuid.UUID) -> list[dict]:
    expire_due_posts_and_requests(db)
    sub_post = get_sub_post_or_404(db, sub_post_id)

    if sub_post.post_status not in ACTIVE_VISIBLE_POST_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub post not found.",
        )
    if sub_post.public_visibility_status != "visible":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub post not found.",
        )

    return [
        serialize_sub_post_position(db, position)
        for position in list_positions(db, sub_post_id)
    ]
