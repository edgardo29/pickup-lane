"""Read-only admin support views for Need a Sub."""

import uuid
from base64 import urlsafe_b64decode, urlsafe_b64encode
from binascii import Error as BinasciiError
from datetime import datetime
from json import JSONDecodeError, dumps, loads

from fastapi import HTTPException, status
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from backend.models import (
    SubPost,
    SubPostPosition,
    SubPostRequest,
    SubPostRequestStatusHistory,
    SubPostStatusHistory,
    User,
)
from backend.schemas.admin_need_a_sub_schema import (
    AdminNeedASubAuditActionRead,
    AdminNeedASubPostDetailRead,
    AdminNeedASubPostListItemRead,
    AdminNeedASubPostRead,
    AdminNeedASubRequestCountsRead,
    AdminNeedASubRequestDetailRead,
    AdminNeedASubRequestRead,
    AdminNeedASubStatusHistoryRead,
    AdminNeedASubUserRead,
)
from backend.services.admin_action_service import list_admin_actions
from backend.services.need_a_sub_lifecycle_service import expire_due_posts_and_requests
from backend.services.need_a_sub_post_service import serialize_sub_post

NEED_A_SUB_LIST_ASCENDING_VIEWS = {"active", "full"}


def parse_uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


def normalize_search_query(value: str | None) -> str | None:
    normalized = " ".join((value or "").strip().lower().split())
    return normalized or None


def escape_like_search(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def build_user_full_name_search_expression(user_model: type[User]):
    return func.concat(
        func.coalesce(user_model.first_name, ""),
        " ",
        func.coalesce(user_model.last_name, ""),
    )


def build_need_a_sub_label_search_expressions(post_model: type[SubPost]):
    return (
        func.concat("need ", post_model.subs_needed, " sub"),
        func.concat("need ", post_model.subs_needed, " subs"),
    )


def encode_admin_need_a_sub_list_cursor(
    *,
    post: SubPost,
    query: str | None,
    view: str,
) -> str:
    payload = {
        "query": query,
        "view": view,
        "sort": get_admin_need_a_sub_list_sort(view),
        "starts_at": post.starts_at.isoformat(),
        "created_at": post.created_at.isoformat(),
        "id": str(post.id),
    }
    serialized = dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return urlsafe_b64encode(serialized).decode("ascii")


def decode_admin_need_a_sub_list_cursor(
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
        "query",
        "view",
        "sort",
        "starts_at",
        "created_at",
        "id",
    }
    if not required_keys.issubset(payload):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor is invalid.",
        )

    return payload


def validate_admin_need_a_sub_list_cursor_context(
    cursor_payload: dict[str, object] | None,
    *,
    query: str | None,
    view: str,
) -> None:
    if cursor_payload is None:
        return

    if (
        cursor_payload["query"] != query
        or cursor_payload["view"] != view
        or cursor_payload["sort"] != get_admin_need_a_sub_list_sort(view)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cursor does not match the current query.",
        )


def parse_admin_need_a_sub_list_cursor_datetime(
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


def parse_admin_need_a_sub_list_cursor_uuid(
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


def build_admin_need_a_sub_list_cursor_filter(
    cursor_payload: dict[str, object],
    *,
    view: str,
):
    starts_at = parse_admin_need_a_sub_list_cursor_datetime(
        cursor_payload,
        "starts_at",
    )
    created_at = parse_admin_need_a_sub_list_cursor_datetime(
        cursor_payload,
        "created_at",
    )
    post_id = parse_admin_need_a_sub_list_cursor_uuid(cursor_payload)

    if get_admin_need_a_sub_list_sort(view) == "starts_at_asc":
        return or_(
            SubPost.starts_at > starts_at,
            and_(SubPost.starts_at == starts_at, SubPost.created_at > created_at),
            and_(
                SubPost.starts_at == starts_at,
                SubPost.created_at == created_at,
                SubPost.id > post_id,
            ),
        )

    return or_(
        SubPost.starts_at < starts_at,
        and_(SubPost.starts_at == starts_at, SubPost.created_at < created_at),
        and_(
            SubPost.starts_at == starts_at,
            SubPost.created_at == created_at,
            SubPost.id < post_id,
        ),
    )


def get_admin_need_a_sub_list_sort(view: str) -> str:
    return "starts_at_asc" if view in NEED_A_SUB_LIST_ASCENDING_VIEWS else "starts_at_desc"


def build_need_a_sub_full_condition():
    position_exists = (
        select(SubPostPosition.id)
        .where(SubPostPosition.sub_post_id == SubPost.id)
        .exists()
    )
    unfilled_position_exists = (
        select(SubPostPosition.id)
        .outerjoin(
            SubPostRequest,
            and_(
                SubPostRequest.sub_post_position_id == SubPostPosition.id,
                SubPostRequest.request_status == "confirmed",
            ),
        )
        .where(SubPostPosition.sub_post_id == SubPost.id)
        .group_by(SubPostPosition.id, SubPostPosition.spots_needed)
        .having(func.count(SubPostRequest.id) < SubPostPosition.spots_needed)
        .exists()
    )
    return and_(
        SubPost.post_status == "active",
        position_exists,
        ~unfilled_position_exists,
    )


def apply_admin_need_a_sub_view_filter(statement, view: str):
    if view in {"active", "full"}:
        full_condition = build_need_a_sub_full_condition()
        if view == "full":
            return statement.where(full_condition)
        return statement.where(
            SubPost.post_status == "active",
            ~full_condition,
        )

    return statement.where(SubPost.post_status == view)


def build_display_name(user: User) -> str:
    if user.deleted_at is not None or user.account_status == "deleted":
        return "Deleted User"

    name = " ".join(
        value.strip()
        for value in (user.first_name or "", user.last_name or "")
        if value.strip()
    )
    return name or "Pickup Lane Player"


def serialize_user(user: User | None) -> AdminNeedASubUserRead | None:
    if user is None:
        return None
    return AdminNeedASubUserRead(
        id=user.id,
        display_name=build_display_name(user),
        account_status=(
            "deleted"
            if user.deleted_at is not None or user.account_status == "deleted"
            else user.account_status
        ),
    )


def build_request_counts(
    *,
    total_count: int = 0,
    pending_count: int = 0,
    confirmed_count: int = 0,
    waitlisted_count: int = 0,
) -> AdminNeedASubRequestCountsRead:
    active_count = pending_count + confirmed_count + waitlisted_count
    return AdminNeedASubRequestCountsRead(
        total_count=total_count,
        pending_count=pending_count,
        confirmed_count=confirmed_count,
        waitlisted_count=waitlisted_count,
        terminal_count=max(total_count - active_count, 0),
    )


def get_request_count_rows(
    db: Session,
    post_ids: list[uuid.UUID],
) -> dict[uuid.UUID, AdminNeedASubRequestCountsRead]:
    if not post_ids:
        return {}

    rows = db.execute(
        select(
            SubPostRequest.sub_post_id,
            func.count(SubPostRequest.id),
            func.sum(case((SubPostRequest.request_status == "pending", 1), else_=0)),
            func.sum(case((SubPostRequest.request_status == "confirmed", 1), else_=0)),
            func.sum(
                case((SubPostRequest.request_status == "sub_waitlist", 1), else_=0)
            ),
        )
        .where(SubPostRequest.sub_post_id.in_(post_ids))
        .group_by(SubPostRequest.sub_post_id)
    ).all()

    return {
        post_id: build_request_counts(
            total_count=total_count or 0,
            pending_count=pending_count or 0,
            confirmed_count=confirmed_count or 0,
            waitlisted_count=waitlisted_count or 0,
        )
        for (
            post_id,
            total_count,
            pending_count,
            confirmed_count,
            waitlisted_count,
        ) in rows
    }


def list_admin_need_a_sub_posts(
    db: Session,
    *,
    viewer_user: User,
    query: str | None = None,
    view: str = "active",
    offset: int = 0,
    limit: int = 50,
    cursor: str | None = None,
) -> tuple[list[AdminNeedASubPostListItemRead], int, str | None, bool]:
    expire_due_posts_and_requests(db)
    normalized_query = normalize_search_query(query)
    cursor_payload = decode_admin_need_a_sub_list_cursor(cursor)
    validate_admin_need_a_sub_list_cursor_context(
        cursor_payload,
        query=normalized_query,
        view=view,
    )

    statement = select(SubPost, User).join(User, SubPost.owner_user_id == User.id)
    statement = apply_admin_need_a_sub_view_filter(statement, view)

    if normalized_query is not None:
        query_uuid = parse_uuid(normalized_query)
        text_match = f"%{escape_like_search(normalized_query)}%"
        need_label_expression, need_label_plural_expression = (
            build_need_a_sub_label_search_expressions(SubPost)
        )
        search_conditions = [
            func.coalesce(SubPost.team_name, "").ilike(text_match, escape="\\"),
            need_label_expression.ilike(
                text_match,
                escape="\\",
            ),
            need_label_plural_expression.ilike(
                text_match,
                escape="\\",
            ),
            SubPost.location_name.ilike(text_match, escape="\\"),
            SubPost.city.ilike(text_match, escape="\\"),
            SubPost.state.ilike(text_match, escape="\\"),
            func.coalesce(User.first_name, "").ilike(text_match, escape="\\"),
            func.coalesce(User.last_name, "").ilike(text_match, escape="\\"),
            build_user_full_name_search_expression(User).ilike(
                text_match,
                escape="\\",
            ),
        ]
        search_conditions.append(
            func.coalesce(User.email, "").ilike(text_match, escape="\\")
        )
        if query_uuid is not None:
            search_conditions.extend(
                (SubPost.id == query_uuid, SubPost.owner_user_id == query_uuid)
            )
        statement = statement.where(or_(*search_conditions))

    count_statement = select(func.count()).select_from(
        statement.with_only_columns(SubPost.id).order_by(None).subquery()
    )
    total_count = int(db.scalar(count_statement) or 0)

    if cursor_payload is not None:
        statement = statement.where(
            build_admin_need_a_sub_list_cursor_filter(
                cursor_payload,
                view=view,
            )
        )

    if get_admin_need_a_sub_list_sort(view) == "starts_at_asc":
        statement = statement.order_by(
            SubPost.starts_at.asc(),
            SubPost.created_at.asc(),
            SubPost.id.asc(),
        )
    else:
        statement = statement.order_by(
            SubPost.starts_at.desc(),
            SubPost.created_at.desc(),
            SubPost.id.desc(),
        )
    if cursor_payload is None:
        statement = statement.offset(offset)

    rows = db.execute(
        statement.limit(limit + 1)
    ).all()
    page_rows = rows[:limit]
    has_more = len(rows) > limit
    counts_by_post = get_request_count_rows(db, [post.id for post, _ in page_rows])

    posts = [
        AdminNeedASubPostListItemRead(
            id=post.id,
            post_status=post.post_status,
            public_visibility_status=post.public_visibility_status,
            team_name=post.team_name,
            format_label=post.format_label,
            environment_type=post.environment_type,
            game_player_group=post.game_player_group,
            starts_at=post.starts_at,
            ends_at=post.ends_at,
            starts_on_local=post.starts_on_local,
            timezone=post.timezone,
            location_name=post.location_name,
            city=post.city,
            state=post.state,
            subs_needed=post.subs_needed,
            owner=serialize_user(owner),
            request_counts=counts_by_post.get(post.id, build_request_counts()),
            created_at=post.created_at,
            updated_at=post.updated_at,
        )
        for post, owner in page_rows
    ]
    next_cursor = None
    if has_more and page_rows:
        last_post = page_rows[-1][0]
        next_cursor = encode_admin_need_a_sub_list_cursor(
            post=last_post,
            query=normalized_query,
            view=view,
        )

    return posts, total_count, next_cursor, has_more


def get_admin_need_a_sub_post_or_404(db: Session, post_id: uuid.UUID) -> SubPost:
    post = db.get(SubPost, post_id)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub post not found.",
        )
    return post


def serialize_history(
    history: SubPostStatusHistory | SubPostRequestStatusHistory,
    users_by_id: dict[uuid.UUID, User],
) -> AdminNeedASubStatusHistoryRead:
    return AdminNeedASubStatusHistoryRead(
        id=history.id,
        old_status=history.old_status,
        new_status=history.new_status,
        change_source=history.change_source,
        change_reason=history.change_reason,
        changed_by=serialize_user(users_by_id.get(history.changed_by_user_id)),
        created_at=history.created_at,
    )


def serialize_request(
    *,
    request: SubPostRequest,
    position: SubPostPosition,
    requester: User,
    status_history: list[AdminNeedASubStatusHistoryRead],
) -> AdminNeedASubRequestRead:
    return AdminNeedASubRequestRead(
        id=request.id,
        sub_post_position_id=request.sub_post_position_id,
        position_label=position.position_label,
        player_group=position.player_group,
        requester=serialize_user(requester),
        request_status=request.request_status,
        confirmed_at=request.confirmed_at,
        declined_at=request.declined_at,
        sub_waitlisted_at=request.sub_waitlisted_at,
        canceled_at=request.canceled_at,
        expired_at=request.expired_at,
        no_show_reported_at=request.no_show_reported_at,
        created_at=request.created_at,
        updated_at=request.updated_at,
        status_history=status_history,
    )


def get_admin_need_a_sub_request_detail(
    db: Session,
    *,
    request_id: uuid.UUID,
    viewer_user: User,
) -> AdminNeedASubRequestDetailRead:
    expire_due_posts_and_requests(db)
    request = db.get(SubPostRequest, request_id)
    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub request not found.",
        )
    post = get_admin_need_a_sub_post_or_404(db, request.sub_post_id)
    owner = db.get(User, post.owner_user_id)
    position = db.get(SubPostPosition, request.sub_post_position_id)
    requester = db.get(User, request.requester_user_id)
    if owner is None or position is None or requester is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Need a Sub request context not found.",
        )

    request_histories = list(
        db.scalars(
            select(SubPostRequestStatusHistory)
            .where(SubPostRequestStatusHistory.sub_post_request_id == request.id)
            .order_by(
                SubPostRequestStatusHistory.created_at.asc(),
                SubPostRequestStatusHistory.id.asc(),
            )
        ).all()
    )
    user_ids = {
        history.changed_by_user_id
        for history in request_histories
        if history.changed_by_user_id is not None
    }
    users_by_id = (
        {
            user.id: user
            for user in db.scalars(select(User).where(User.id.in_(user_ids))).all()
        }
        if user_ids
        else {}
    )
    status_history = [
        serialize_history(history, users_by_id)
        for history in request_histories
    ]
    serialized_post = AdminNeedASubPostRead.model_validate(serialize_sub_post(db, post))
    return AdminNeedASubRequestDetailRead(
        post=serialized_post,
        owner=serialize_user(owner),
        request=serialize_request(
            request=request,
            position=position,
            requester=requester,
            status_history=status_history,
        ),
    )


def get_admin_need_a_sub_post_detail(
    db: Session,
    *,
    post_id: uuid.UUID,
    viewer_user: User,
    request_offset: int = 0,
    request_limit: int = 50,
    audit_offset: int = 0,
    audit_limit: int = 50,
) -> AdminNeedASubPostDetailRead:
    expire_due_posts_and_requests(db)
    post = get_admin_need_a_sub_post_or_404(db, post_id)
    owner = db.get(User, post.owner_user_id)
    if owner is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Need a Sub post owner is missing.",
        )

    positions = list(
        db.scalars(
            select(SubPostPosition)
            .where(SubPostPosition.sub_post_id == post.id)
            .order_by(SubPostPosition.sort_order.asc(), SubPostPosition.id.asc())
        ).all()
    )
    position_by_id = {position.id: position for position in positions}
    request_total_count = int(
        db.scalar(
            select(func.count())
            .select_from(SubPostRequest)
            .where(SubPostRequest.sub_post_id == post.id)
        )
        or 0
    )
    requests = list(
        db.scalars(
            select(SubPostRequest)
            .where(SubPostRequest.sub_post_id == post.id)
            .order_by(SubPostRequest.created_at.desc(), SubPostRequest.id.desc())
            .offset(request_offset)
            .limit(request_limit)
        ).all()
    )
    request_ids = [request.id for request in requests]
    request_histories = (
        list(
            db.scalars(
                select(SubPostRequestStatusHistory)
                .where(
                    SubPostRequestStatusHistory.sub_post_request_id.in_(request_ids)
                )
                .order_by(
                    SubPostRequestStatusHistory.created_at.asc(),
                    SubPostRequestStatusHistory.id.asc(),
                )
            ).all()
        )
        if request_ids
        else []
    )
    post_histories = list(
        db.scalars(
            select(SubPostStatusHistory)
            .where(SubPostStatusHistory.sub_post_id == post.id)
            .order_by(SubPostStatusHistory.created_at.asc(), SubPostStatusHistory.id.asc())
        ).all()
    )

    user_ids = {request.requester_user_id for request in requests}
    user_ids.update(
        history.changed_by_user_id
        for history in (*request_histories, *post_histories)
        if history.changed_by_user_id is not None
    )
    users_by_id = (
        {
            user.id: user
            for user in db.scalars(select(User).where(User.id.in_(user_ids))).all()
        }
        if user_ids
        else {}
    )

    histories_by_request: dict[uuid.UUID, list[AdminNeedASubStatusHistoryRead]] = {}
    for history in request_histories:
        histories_by_request.setdefault(history.sub_post_request_id, []).append(
            serialize_history(history, users_by_id)
        )

    serialized_requests: list[AdminNeedASubRequestRead] = []
    for request in requests:
        position = position_by_id.get(request.sub_post_position_id)
        requester = users_by_id.get(request.requester_user_id)
        if position is None or requester is None:
            continue
        serialized_requests.append(
            serialize_request(
                request=request,
                position=position,
                requester=requester,
                status_history=histories_by_request.get(request.id, []),
            )
        )

    serialized_post = AdminNeedASubPostRead.model_validate(serialize_sub_post(db, post))
    counts = get_request_count_rows(db, [post.id]).get(post.id, build_request_counts())
    all_audit_actions = list_admin_actions(
        db,
        viewer_user=viewer_user,
        target_filters={"target_sub_post_id": post.id},
        limit=None,
    )
    audit_total_count = len(all_audit_actions)
    audit_actions = all_audit_actions[audit_offset : audit_offset + audit_limit]

    return AdminNeedASubPostDetailRead(
        post=serialized_post,
        owner=serialize_user(owner),
        request_counts=counts,
        requests=serialized_requests,
        request_total_count=request_total_count,
        request_offset=request_offset,
        request_limit=request_limit,
        post_status_history=[
            serialize_history(history, users_by_id) for history in post_histories
        ],
        audit_actions=[
            AdminNeedASubAuditActionRead(
                id=action.id,
                admin_user_id=action.admin_user_id,
                action_type=action.action_type,
                reason=action.reason,
                created_at=action.created_at,
            )
            for action in audit_actions
        ],
        audit_total_count=audit_total_count,
        audit_offset=audit_offset,
        audit_limit=audit_limit,
    )
