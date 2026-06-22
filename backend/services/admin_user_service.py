"""Read-only Admin Users search, list, and detail workflows."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from backend.models import (
    Booking,
    Game,
    GameParticipant,
    SubPost,
    SubPostRequest,
    SupportFlag,
    User,
    UserStats,
)
from backend.schemas.admin_user_schema import (
    AdminUserAuditActionSummaryRead,
    AdminUserBookingSummaryRead,
    AdminUserCapabilitiesRead,
    AdminUserDetailRead,
    AdminUserHostedGameSummaryRead,
    AdminUserListRead,
    AdminUserParticipationSummaryRead,
    AdminUserProfileRead,
    AdminUserStaffRead,
    AdminUserStatsSummaryRead,
    AdminUserSubPostSummaryRead,
    AdminUserSubRequestSummaryRead,
    AdminUserSupportFlagSummaryRead,
)
from backend.services.admin_action_service import list_admin_actions
from backend.services.admin_permission_service import (
    ADMIN_ROLE,
    MODERATOR_ROLE,
    PERMISSION_AUDIT_READ,
    PERMISSION_MONEY_READ,
    get_admin_data_scopes_for_user,
    get_admin_permissions_for_role,
    user_has_admin_permission,
)
from backend.services.support_flag_service import user_can_read_support_flag

ADMIN_USER_ACCOUNT_STATUSES = (
    "active",
    "suspended",
    "pending_deletion",
    "deleted",
)
ADMIN_USER_HOSTING_STATUSES = (
    "not_eligible",
    "pending_review",
    "eligible",
    "restricted",
    "suspended",
    "banned_from_hosting",
)
ADMIN_USER_ROLES = ("player", "admin", "moderator")
ADMIN_USER_STAFF_ROLES = (ADMIN_ROLE, MODERATOR_ROLE)


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
        phone=None if is_deleted else user.phone,
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


def serialize_admin_user_staff_item(user: User) -> AdminUserStaffRead:
    return AdminUserStaffRead(
        **serialize_admin_user_list_item(user).model_dump(),
        permissions=list(get_admin_permissions_for_role(user.role)),
        data_scopes=list(get_admin_data_scopes_for_user(user)),
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
        **serialize_admin_user_list_item(user).model_dump(),
        hosting_suspended_until=user.hosting_suspended_until,
    )


def serialize_admin_user_stats(
    stats: UserStats | None,
) -> AdminUserStatsSummaryRead | None:
    if stats is None:
        return None
    return AdminUserStatsSummaryRead.model_validate(stats, from_attributes=True)


def list_admin_user_bookings(
    db: Session,
    *,
    user_id: uuid.UUID,
    limit: int,
) -> list[AdminUserBookingSummaryRead]:
    rows = db.execute(
        select(Booking, Game)
        .join(Game, Booking.game_id == Game.id)
        .where(
            Booking.buyer_user_id == user_id,
            Game.deleted_at.is_(None),
        )
        .order_by(Game.starts_at.desc(), Booking.id.desc())
        .limit(limit)
    ).all()
    return [
        AdminUserBookingSummaryRead(
            id=booking.id,
            game_id=game.id,
            game_type=game.game_type,
            game_title=game.title,
            game_status=game.game_status,
            starts_at=game.starts_at,
            booking_status=booking.booking_status,
            participant_count=booking.participant_count,
            created_at=booking.created_at,
        )
        for booking, game in rows
    ]


def list_admin_user_participations(
    db: Session,
    *,
    user_id: uuid.UUID,
    limit: int,
) -> list[AdminUserParticipationSummaryRead]:
    rows = db.execute(
        select(GameParticipant, Game)
        .join(Game, GameParticipant.game_id == Game.id)
        .where(
            GameParticipant.user_id == user_id,
            Game.deleted_at.is_(None),
        )
        .order_by(Game.starts_at.desc(), GameParticipant.id.desc())
        .limit(limit)
    ).all()
    return [
        AdminUserParticipationSummaryRead(
            id=participant.id,
            game_id=game.id,
            booking_id=participant.booking_id,
            game_type=game.game_type,
            game_title=game.title,
            game_status=game.game_status,
            starts_at=game.starts_at,
            participant_type=participant.participant_type,
            participant_status=participant.participant_status,
            attendance_status=participant.attendance_status,
            joined_at=participant.joined_at,
        )
        for participant, game in rows
    ]


def list_admin_user_hosted_games(
    db: Session,
    *,
    user_id: uuid.UUID,
    game_type: str,
    limit: int,
) -> list[AdminUserHostedGameSummaryRead]:
    games = db.scalars(
        select(Game)
        .where(
            Game.host_user_id == user_id,
            Game.game_type == game_type,
            Game.deleted_at.is_(None),
        )
        .order_by(Game.starts_at.desc(), Game.id.desc())
        .limit(limit)
    ).all()
    return [
        AdminUserHostedGameSummaryRead(
            id=game.id,
            game_type=game.game_type,
            title=game.title,
            game_status=game.game_status,
            starts_at=game.starts_at,
            city=game.city_snapshot,
            state=game.state_snapshot,
        )
        for game in games
    ]


def list_admin_user_sub_posts(
    db: Session,
    *,
    user_id: uuid.UUID,
    limit: int,
) -> list[AdminUserSubPostSummaryRead]:
    posts = db.scalars(
        select(SubPost)
        .where(SubPost.owner_user_id == user_id)
        .order_by(SubPost.starts_at.desc(), SubPost.id.desc())
        .limit(limit)
    ).all()
    return [
        AdminUserSubPostSummaryRead(
            id=post.id,
            post_status=post.post_status,
            team_name=post.team_name,
            starts_at=post.starts_at,
            city=post.city,
            state=post.state,
            subs_needed=post.subs_needed,
            created_at=post.created_at,
        )
        for post in posts
    ]


def list_admin_user_sub_requests(
    db: Session,
    *,
    user_id: uuid.UUID,
    limit: int,
) -> list[AdminUserSubRequestSummaryRead]:
    rows = db.execute(
        select(SubPostRequest, SubPost)
        .join(SubPost, SubPostRequest.sub_post_id == SubPost.id)
        .where(SubPostRequest.requester_user_id == user_id)
        .order_by(SubPost.starts_at.desc(), SubPostRequest.id.desc())
        .limit(limit)
    ).all()
    return [
        AdminUserSubRequestSummaryRead(
            id=sub_request.id,
            sub_post_id=post.id,
            sub_post_position_id=sub_request.sub_post_position_id,
            request_status=sub_request.request_status,
            post_status=post.post_status,
            team_name=post.team_name,
            starts_at=post.starts_at,
            city=post.city,
            state=post.state,
            created_at=sub_request.created_at,
        )
        for sub_request, post in rows
    ]


def list_admin_user_audit_actions(
    db: Session,
    *,
    user_id: uuid.UUID,
    viewer_user: User,
    limit: int,
) -> list[AdminUserAuditActionSummaryRead]:
    if not user_has_admin_permission(viewer_user, PERMISSION_AUDIT_READ):
        return []

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


def list_admin_user_support_flags(
    db: Session,
    *,
    user_id: uuid.UUID,
    viewer_user: User,
    limit: int,
) -> list[AdminUserSupportFlagSummaryRead]:
    flags = db.scalars(
        select(SupportFlag)
        .where(SupportFlag.target_user_id == user_id)
        .order_by(SupportFlag.created_at.desc(), SupportFlag.id.desc())
        .limit(limit)
    ).all()

    visible_flags: list[AdminUserSupportFlagSummaryRead] = []
    for flag in flags:
        if not user_can_read_support_flag(viewer_user, flag):
            continue
        visible_flags.append(
            AdminUserSupportFlagSummaryRead(
                id=flag.id,
                flag_type=flag.flag_type,
                flag_status=flag.flag_status,
                severity=flag.severity,
                source=flag.source,
                title=flag.title,
                summary=flag.summary,
                resolution_outcome=flag.resolution_outcome,
                resolved_at=flag.resolved_at,
                created_at=flag.created_at,
                updated_at=flag.updated_at,
            )
        )
        if len(visible_flags) >= limit:
            break

    return visible_flags


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
        bookings=list_admin_user_bookings(db, user_id=user.id, limit=limit),
        participations=list_admin_user_participations(
            db,
            user_id=user.id,
            limit=limit,
        ),
        community_games_hosted=list_admin_user_hosted_games(
            db,
            user_id=user.id,
            game_type="community",
            limit=limit,
        ),
        official_host_assignments=list_admin_user_hosted_games(
            db,
            user_id=user.id,
            game_type="official",
            limit=limit,
        ),
        sub_posts_owned=list_admin_user_sub_posts(
            db,
            user_id=user.id,
            limit=limit,
        ),
        sub_requests_made=list_admin_user_sub_requests(
            db,
            user_id=user.id,
            limit=limit,
        ),
        audit_actions=list_admin_user_audit_actions(
            db,
            user_id=user.id,
            viewer_user=viewer_user,
            limit=limit,
        ),
        support_flags=list_admin_user_support_flags(
            db,
            user_id=user.id,
            viewer_user=viewer_user,
            limit=limit,
        ),
        capabilities=AdminUserCapabilitiesRead(
            can_view_audit=user_has_admin_permission(
                viewer_user,
                PERMISSION_AUDIT_READ,
            ),
            can_view_money=user_has_admin_permission(
                viewer_user,
                PERMISSION_MONEY_READ,
            ),
        ),
    )


def list_admin_staff_users(
    db: Session,
    *,
    include_deleted: bool = False,
    limit: int = 100,
) -> list[AdminUserStaffRead]:
    statement = select(User).where(User.role.in_(ADMIN_USER_STAFF_ROLES))
    if not include_deleted:
        statement = statement.where(
            User.deleted_at.is_(None),
            User.account_status != "deleted",
        )

    users = db.scalars(
        statement.order_by(
            User.role.asc(),
            User.account_status.asc(),
            User.created_at.desc(),
            User.id.desc(),
        ).limit(limit)
    ).all()
    return [serialize_admin_user_staff_item(user) for user in users]


def list_admin_users(
    db: Session,
    *,
    query: str | None = None,
    account_status: str | None = None,
    hosting_status: str | None = None,
    role: str | None = None,
    include_deleted: bool = False,
    limit: int = 100,
) -> list[AdminUserListRead]:
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
        search_conditions = []
        query_user_id = parse_user_id_query(normalized_query)
        if query_user_id is not None:
            search_conditions.append(User.id == query_user_id)

        contact_search_conditions = []
        full_name = func.lower(
            func.concat(
                func.coalesce(User.first_name, ""),
                " ",
                func.coalesce(User.last_name, ""),
            )
        )
        contact_search_conditions.extend(
            [
                func.lower(func.coalesce(User.email, "")).contains(
                    normalized_query,
                    autoescape=True,
                ),
                full_name.contains(normalized_query, autoescape=True),
            ]
        )

        phone_digits = "".join(
            character for character in normalized_query if character.isdigit()
        )
        if phone_digits:
            normalized_phone = func.regexp_replace(
                func.coalesce(User.phone, ""),
                "[^0-9]",
                "",
                "g",
            )
            contact_search_conditions.append(
                normalized_phone.contains(phone_digits)
            )

        search_conditions.append(
            and_(
                User.deleted_at.is_(None),
                User.account_status != "deleted",
                or_(*contact_search_conditions),
            )
        )

        statement = statement.where(or_(*search_conditions))

    users = db.scalars(
        statement.order_by(User.created_at.desc(), User.id.desc()).limit(limit)
    ).all()
    return [serialize_admin_user_list_item(user) for user in users]
