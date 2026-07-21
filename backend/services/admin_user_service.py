"""Read-only Admin Users search, list, and detail workflows."""

import uuid
from base64 import urlsafe_b64decode, urlsafe_b64encode
from binascii import Error as BinasciiError
from datetime import UTC, datetime
from json import JSONDecodeError, dumps, loads

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from backend.models import (
    Booking,
    Game,
    GameParticipant,
    SubPost,
    SubPostRequest,
    User,
    UserStats,
)
from backend.schemas.admin_user_schema import (
    AdminUserAuditActionSummaryRead,
    AdminUserDetailRead,
    AdminUserGameActivityItemRead,
    AdminUserGameActivityRead,
    AdminUserListRead,
    AdminUserListPageRead,
    AdminUserNeedASubActivityItemRead,
    AdminUserNeedASubActivityRead,
    AdminUserProfileRead,
    AdminUserStatsSummaryRead,
)
from backend.services.admin_action_service import list_admin_actions
from backend.services.auth_service import ADMIN_ROLE

ADMIN_USER_ACCOUNT_STATUSES = (
    "active",
    "suspended",
    "pending_deletion",
    "deleted",
)
ADMIN_USER_HOSTING_STATUSES = (
    "not_eligible",
    "eligible",
    "restricted",
)
ADMIN_USER_ROLES = ("player", "admin")
ADMIN_USER_LIST_CURSOR_SORT = "created_at_desc_v1"
ADMIN_USER_DETAIL_ACTIVITY_LIMIT = 5
ADMIN_USER_PLAYER_PARTICIPANT_TYPES = {"registered_user", "admin_added"}
ADMIN_USER_CANCELLED_PARTICIPANT_STATUSES = {
    "cancelled",
    "late_cancelled",
    "removed",
    "refunded",
}
ADMIN_USER_LIST_CURSOR_CONTEXT_KEYS = {
    "query",
    "account_status",
    "hosting_status",
    "role",
    "include_deleted",
    "sort",
}


def is_admin_user_deleted(user: User) -> bool:
    return user.deleted_at is not None or user.account_status == "deleted"


def normalize_optional_filter(value: str | None) -> str | None:
    normalized = " ".join((value or "").strip().lower().split())
    return normalized or None


def validate_admin_user_filter(
    value: str | None,
    *,
    allowed_values: tuple[str, ...],
    field_name: str,
) -> str | None:
    normalized = normalize_optional_filter(value)
    if normalized is not None and normalized not in allowed_values:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} is not supported.",
        )
    return normalized


def parse_user_id_query(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


def parse_exact_email_query(value: str) -> str | None:
    if any(character.isspace() for character in value):
        return None
    if value.count("@") != 1:
        return None

    local_part, domain_part = value.split("@", 1)
    if not local_part or not domain_part:
        return None
    return value.lower()


def escape_like_search(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def build_user_full_name_search_expression(user_model: type[User]):
    return func.concat(
        func.coalesce(user_model.first_name, ""),
        " ",
        func.coalesce(user_model.last_name, ""),
    )


def apply_admin_user_text_search(statement, normalized_query: str):
    text_match = f"%{escape_like_search(normalized_query)}%"
    return statement.where(
        User.deleted_at.is_(None),
        User.account_status != "deleted",
        or_(
            User.email.ilike(text_match, escape="\\"),
            User.first_name.ilike(text_match, escape="\\"),
            User.last_name.ilike(text_match, escape="\\"),
            build_user_full_name_search_expression(User).ilike(
                text_match,
                escape="\\",
            ),
        ),
    )


def encode_admin_user_list_cursor(
    *,
    user: User,
    query: str | None,
    account_status: str | None,
    hosting_status: str | None,
    role: str | None,
    include_deleted: bool,
) -> str:
    payload = {
        "query": query,
        "account_status": account_status,
        "hosting_status": hosting_status,
        "role": role,
        "include_deleted": include_deleted,
        "sort": ADMIN_USER_LIST_CURSOR_SORT,
        "created_at": user.created_at.isoformat(),
        "id": str(user.id),
    }
    serialized = dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return urlsafe_b64encode(serialized).decode("ascii")


def decode_admin_user_list_cursor(
    cursor: str | None,
) -> dict[str, object] | None:
    if cursor is None:
        return None

    try:
        decoded = urlsafe_b64decode(cursor.encode("ascii"))
        payload = loads(decoded.decode("utf-8"))
    except (BinasciiError, UnicodeDecodeError, ValueError, JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor is invalid.",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor is invalid.",
        )

    required_keys = {
        *ADMIN_USER_LIST_CURSOR_CONTEXT_KEYS,
        "created_at",
        "id",
    }
    if not required_keys.issubset(payload):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor is invalid.",
        )

    return payload


def validate_admin_user_list_cursor_context(
    cursor_payload: dict[str, object] | None,
    *,
    query: str | None,
    account_status: str | None,
    hosting_status: str | None,
    role: str | None,
    include_deleted: bool,
) -> None:
    if cursor_payload is None:
        return

    if (
        cursor_payload["query"] != query
        or cursor_payload["account_status"] != account_status
        or cursor_payload["hosting_status"] != hosting_status
        or cursor_payload["role"] != role
        or cursor_payload["include_deleted"] != include_deleted
        or cursor_payload["sort"] != ADMIN_USER_LIST_CURSOR_SORT
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor does not match the current query.",
        )


def parse_admin_user_list_cursor_datetime(
    cursor_payload: dict[str, object],
) -> datetime:
    value = cursor_payload["created_at"]
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


def parse_admin_user_list_cursor_uuid(
    cursor_payload: dict[str, object],
) -> uuid.UUID:
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


def build_admin_user_list_cursor_filter(cursor_payload: dict[str, object]):
    created_at = parse_admin_user_list_cursor_datetime(cursor_payload)
    user_id = parse_admin_user_list_cursor_uuid(cursor_payload)
    return or_(
        User.created_at < created_at,
        and_(User.created_at == created_at, User.id < user_id),
    )


def build_user_display_name(user: User) -> str:
    if is_admin_user_deleted(user):
        return "Deleted User"

    full_name = " ".join(
        value.strip()
        for value in (user.first_name or "", user.last_name or "")
        if value.strip()
    )
    return full_name or user.email or "Deleted User"


def serialize_admin_user_list_item(user: User) -> AdminUserListRead:
    is_deleted = is_admin_user_deleted(user)
    return AdminUserListRead(
        id=user.id,
        display_name=build_user_display_name(user),
        email=None if is_deleted else user.email,
        role=user.role,
        account_status="deleted" if is_deleted else user.account_status,
        hosting_status=user.hosting_status,
        email_verified=False if is_deleted else user.email_verified_at is not None,
        home_city=None if is_deleted else user.home_city,
        home_state=None if is_deleted else user.home_state,
        member_since=user.member_since,
        created_at=user.created_at,
        updated_at=user.updated_at,
        deleted_at=user.deleted_at,
    )


def get_admin_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    return user


def count_active_admins(db: Session) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(User)
            .where(
                User.role == ADMIN_ROLE,
                User.account_status == "active",
                User.deleted_at.is_(None),
            )
        )
        or 0
    )


def serialize_admin_user_profile(user: User) -> AdminUserProfileRead:
    return AdminUserProfileRead(
        **serialize_admin_user_list_item(user).model_dump()
    )


def serialize_admin_user_stats(
    stats: UserStats | None,
) -> AdminUserStatsSummaryRead | None:
    if stats is None:
        return None
    return AdminUserStatsSummaryRead.model_validate(stats, from_attributes=True)


def get_aware_datetime(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def get_activity_sort_timestamp(value: datetime) -> float:
    return get_aware_datetime(value).timestamp()


def slice_admin_user_activity_page(
    items: list,
    *,
    offset: int,
    limit: int,
) -> tuple[list, int, bool]:
    total_items = len(items)
    page_items = items[offset : offset + limit]
    return page_items, total_items, offset + limit < total_items


def get_admin_user_game_entry(
    entries: dict[uuid.UUID, dict[str, object]],
    game: Game,
) -> dict[str, object]:
    entry = entries.get(game.id)
    if entry is None:
        entry = {
            "game": game,
            "bookings": [],
            "participants": [],
            "hosted": False,
        }
        entries[game.id] = entry
    return entry


def is_admin_user_player_participant(participant: GameParticipant) -> bool:
    return participant.participant_type in ADMIN_USER_PLAYER_PARTICIPANT_TYPES


def determine_admin_user_game_outcome(
    *,
    game: Game,
    is_host: bool,
    participants: list[GameParticipant],
    now: datetime,
) -> str:
    starts_at = get_aware_datetime(game.starts_at)
    if is_host and game.game_status == "cancelled" and (
        game.cancelled_by_user_id is not None or game.cancellation_source == "host"
    ):
        return "host_cancel"

    if any(participant.attendance_status == "no_show" for participant in participants):
        return "no_show"
    if any(
        participant.participant_status == "late_cancelled"
        or participant.cancellation_type == "late"
        for participant in participants
    ):
        return "late_cancel"
    if any(
        participant.cancellation_type == "host_cancelled"
        for participant in participants
    ):
        return "host_cancel"
    if any(participant.attendance_status == "attended" for participant in participants):
        return "attended"

    if game.game_status == "active" and starts_at > now:
        return "upcoming"
    if any(
        participant.participant_status in ADMIN_USER_CANCELLED_PARTICIPANT_STATUSES
        or participant.cancellation_type in {
            "on_time",
            "admin_cancelled",
            "payment_failed",
        }
        for participant in participants
    ):
        return "cancelled"
    if is_host and game.game_status == "completed":
        return "attended"
    if game.game_status == "completed":
        return "completed"
    if game.game_status in {"cancelled", "expired", "removed"}:
        return game.game_status
    return "upcoming" if starts_at > now else game.game_status


def build_admin_user_game_activity_item(
    *,
    entry: dict[str, object],
    now: datetime,
) -> AdminUserGameActivityItemRead:
    game = entry["game"]
    assert isinstance(game, Game)
    participants = [
        participant
        for participant in entry["participants"]
        if isinstance(participant, GameParticipant)
        and is_admin_user_player_participant(participant)
    ]
    is_host = bool(entry["hosted"])
    return AdminUserGameActivityItemRead(
        game_id=game.id,
        game_type=game.game_type,
        game_title=game.title,
        game_status=game.game_status,
        venue_name_snapshot=game.venue_name_snapshot,
        city_snapshot=game.city_snapshot,
        state_snapshot=game.state_snapshot,
        scheduled_at=game.starts_at,
        role="host" if is_host else "player",
        outcome=determine_admin_user_game_outcome(
            game=game,
            is_host=is_host,
            participants=participants,
            now=now,
        ),
    )


def sort_admin_user_game_activity_items(
    items: list[AdminUserGameActivityItemRead],
    *,
    now: datetime,
) -> list[AdminUserGameActivityItemRead]:
    def sort_key(item: AdminUserGameActivityItemRead) -> tuple[int, float, str]:
        scheduled_at = get_aware_datetime(item.scheduled_at)
        is_upcoming = item.outcome == "upcoming" and scheduled_at > now
        timestamp = get_activity_sort_timestamp(item.scheduled_at)
        return (
            0 if is_upcoming else 1,
            timestamp if is_upcoming else -timestamp,
            str(item.game_id),
        )

    return sorted(items, key=sort_key)


def get_admin_user_game_activity(
    db: Session,
    *,
    user_id: uuid.UUID,
    limit: int,
    offset: int = 0,
) -> AdminUserGameActivityRead:
    entries: dict[uuid.UUID, dict[str, object]] = {}

    booking_rows = db.execute(
        select(Booking, Game)
        .join(Game, Booking.game_id == Game.id)
        .where(
            Booking.buyer_user_id == user_id,
            Game.deleted_at.is_(None),
        )
    ).all()
    for booking, game in booking_rows:
        entry = get_admin_user_game_entry(entries, game)
        entry["bookings"].append(booking)

    participant_rows = db.execute(
        select(GameParticipant, Game)
        .join(Game, GameParticipant.game_id == Game.id)
        .where(
            GameParticipant.user_id == user_id,
            Game.deleted_at.is_(None),
        )
    ).all()
    for participant, game in participant_rows:
        entry = get_admin_user_game_entry(entries, game)
        entry["participants"].append(participant)

    hosted_games = db.scalars(
        select(Game).where(
            Game.host_user_id == user_id,
            Game.deleted_at.is_(None),
        )
    ).all()
    for game in hosted_games:
        entry = get_admin_user_game_entry(entries, game)
        entry["hosted"] = True

    now = datetime.now(UTC)
    all_items = sort_admin_user_game_activity_items(
        [
            build_admin_user_game_activity_item(entry=entry, now=now)
            for entry in entries.values()
        ],
        now=now,
    )
    page_items, total_items, has_more = slice_admin_user_activity_page(
        all_items,
        offset=offset,
        limit=limit,
    )
    return AdminUserGameActivityRead(
        items=page_items,
        total_items=total_items,
        offset=offset,
        limit=limit,
        has_more=has_more,
    )


def sort_admin_user_need_a_sub_activity_items(
    items: list[AdminUserNeedASubActivityItemRead],
    *,
    now: datetime,
) -> list[AdminUserNeedASubActivityItemRead]:
    def sort_key(item: AdminUserNeedASubActivityItemRead) -> tuple[int, float, float, str]:
        scheduled_at = get_aware_datetime(item.scheduled_at)
        is_upcoming = item.post_status == "active" and scheduled_at > now
        scheduled_timestamp = get_activity_sort_timestamp(item.scheduled_at)
        activity_timestamp = get_activity_sort_timestamp(item.activity_created_at)
        item_id = item.request_id or item.post_id
        return (
            0 if is_upcoming else 1,
            scheduled_timestamp if is_upcoming else -scheduled_timestamp,
            -activity_timestamp,
            str(item_id),
        )

    return sorted(items, key=sort_key)


def get_admin_user_need_a_sub_activity(
    db: Session,
    *,
    user_id: uuid.UUID,
    limit: int,
    offset: int = 0,
) -> AdminUserNeedASubActivityRead:
    items: list[AdminUserNeedASubActivityItemRead] = []
    posts = db.scalars(
        select(SubPost).where(SubPost.owner_user_id == user_id)
    ).all()
    for post in posts:
        items.append(
            AdminUserNeedASubActivityItemRead(
                activity_type="created",
                post_id=post.id,
                request_id=None,
                location_name=post.location_name,
                city=post.city,
                state=post.state,
                scheduled_at=post.starts_at,
                status=post.post_status,
                post_status=post.post_status,
                request_status=None,
                subs_needed=post.subs_needed,
                activity_created_at=post.created_at,
            )
        )

    request_rows = db.execute(
        select(SubPostRequest, SubPost)
        .join(SubPost, SubPostRequest.sub_post_id == SubPost.id)
        .where(SubPostRequest.requester_user_id == user_id)
    ).all()
    for sub_request, post in request_rows:
        items.append(
            AdminUserNeedASubActivityItemRead(
                activity_type="requested",
                post_id=post.id,
                request_id=sub_request.id,
                location_name=post.location_name,
                city=post.city,
                state=post.state,
                scheduled_at=post.starts_at,
                status=sub_request.request_status,
                post_status=post.post_status,
                request_status=sub_request.request_status,
                subs_needed=None,
                activity_created_at=sub_request.created_at,
            )
        )

    all_items = sort_admin_user_need_a_sub_activity_items(
        items,
        now=datetime.now(UTC),
    )
    page_items, total_items, has_more = slice_admin_user_activity_page(
        all_items,
        offset=offset,
        limit=limit,
    )
    return AdminUserNeedASubActivityRead(
        items=page_items,
        total_items=total_items,
        offset=offset,
        limit=limit,
        has_more=has_more,
    )


def list_admin_user_audit_actions(
    db: Session,
    *,
    user_id: uuid.UUID,
    viewer_user: User,
    limit: int,
) -> list[AdminUserAuditActionSummaryRead]:
    actions = list_admin_actions(
        db,
        viewer_user=viewer_user,
        target_filters={"target_user_id": user_id},
        limit=limit,
    )
    return [
        AdminUserAuditActionSummaryRead(
            id=action.id,
            admin_user_id=action.admin_user_id,
            action_type=action.action_type,
            reason=action.reason,
            created_at=action.created_at,
        )
        for action in actions
    ]


def get_admin_user_detail(
    db: Session,
    *,
    user_id: uuid.UUID,
    viewer_user: User,
    limit: int = 50,
) -> AdminUserDetailRead:
    user = get_admin_user_or_404(db, user_id)
    return AdminUserDetailRead(
        user=serialize_admin_user_profile(user),
        stats=serialize_admin_user_stats(db.get(UserStats, user.id)),
        game_activity=get_admin_user_game_activity(
            db,
            user_id=user.id,
            limit=ADMIN_USER_DETAIL_ACTIVITY_LIMIT,
        ),
        need_a_sub_activity=get_admin_user_need_a_sub_activity(
            db,
            user_id=user.id,
            limit=ADMIN_USER_DETAIL_ACTIVITY_LIMIT,
        ),
        audit_actions=list_admin_user_audit_actions(
            db,
            user_id=user.id,
            viewer_user=viewer_user,
            limit=limit,
        ),
    )


def list_admin_users(
    db: Session,
    *,
    query: str | None = None,
    account_status: str | None = None,
    hosting_status: str | None = None,
    role: str | None = None,
    include_deleted: bool = False,
    limit: int = 50,
    cursor: str | None = None,
) -> AdminUserListPageRead:
    normalized_query = normalize_optional_filter(query)
    normalized_account_status = validate_admin_user_filter(
        account_status,
        allowed_values=ADMIN_USER_ACCOUNT_STATUSES,
        field_name="account_status",
    )
    normalized_hosting_status = validate_admin_user_filter(
        hosting_status,
        allowed_values=ADMIN_USER_HOSTING_STATUSES,
        field_name="hosting_status",
    )
    normalized_role = validate_admin_user_filter(
        role,
        allowed_values=ADMIN_USER_ROLES,
        field_name="role",
    )
    cursor_payload = decode_admin_user_list_cursor(cursor)
    validate_admin_user_list_cursor_context(
        cursor_payload,
        query=normalized_query,
        account_status=normalized_account_status,
        hosting_status=normalized_hosting_status,
        role=normalized_role,
        include_deleted=include_deleted,
    )

    statement = select(User)

    if not include_deleted and normalized_account_status != "deleted":
        statement = statement.where(
            User.deleted_at.is_(None),
            User.account_status != "deleted",
        )
    if normalized_account_status is not None:
        if normalized_account_status == "deleted":
            statement = statement.where(
                or_(
                    User.deleted_at.is_not(None),
                    User.account_status == "deleted",
                )
            )
        else:
            statement = statement.where(
                User.account_status == normalized_account_status,
                User.deleted_at.is_(None),
            )
    if normalized_hosting_status is not None:
        statement = statement.where(User.hosting_status == normalized_hosting_status)
    if normalized_role is not None:
        statement = statement.where(User.role == normalized_role)

    if normalized_query is not None:
        query_user_id = parse_user_id_query(normalized_query)
        if query_user_id is not None:
            statement = statement.where(User.id == query_user_id)
        else:
            exact_email = parse_exact_email_query(normalized_query)
            if exact_email is not None:
                exact_email_statement = statement.where(
                    User.deleted_at.is_(None),
                    User.account_status != "deleted",
                    func.lower(func.coalesce(User.email, "")) == exact_email,
                )
                exact_email_match = db.scalars(
                    exact_email_statement.limit(1),
                ).first()
                statement = (
                    exact_email_statement
                    if exact_email_match is not None
                    else apply_admin_user_text_search(statement, normalized_query)
                )
            else:
                statement = apply_admin_user_text_search(statement, normalized_query)

    if cursor_payload is not None:
        statement = statement.where(build_admin_user_list_cursor_filter(cursor_payload))

    users = db.scalars(
        statement.order_by(
            User.created_at.desc(),
            User.id.desc(),
        ).limit(limit + 1)
    ).all()
    page_users = users[:limit]
    has_more = len(users) > limit
    next_cursor = None
    if has_more and page_users:
        next_cursor = encode_admin_user_list_cursor(
            user=page_users[-1],
            query=normalized_query,
            account_status=normalized_account_status,
            hosting_status=normalized_hosting_status,
            role=normalized_role,
            include_deleted=include_deleted,
        )

    return AdminUserListPageRead(
        users=[serialize_admin_user_list_item(user) for user in page_users],
        limit=limit,
        next_cursor=next_cursor,
        has_more=has_more,
    )
