"""Admin community game support workflows."""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    AdminAction,
    CommunityGameDetail,
    Game,
    GameParticipant,
    HostPublishFee,
    Payment,
    SupportFlag,
    User,
)
from backend.schemas.admin_community_schema import (
    AdminCommunityGameAuditActionSummaryRead,
    AdminCommunityGameCapabilitiesRead,
    AdminCommunityGameDetailRead,
    AdminCommunityGameHidePaymentTextCreate,
    AdminCommunityGameHidePaymentTextResultRead,
    AdminCommunityGameHostRead,
    AdminCommunityGameListItemRead,
    AdminCommunityGameModerationStateRead,
    AdminCommunityGameParticipantSummaryRead,
    AdminCommunityGamePaymentSnapshotRead,
    AdminCommunityGamePublishFeeRead,
    AdminCommunityGameReviewFlagCreate,
    AdminCommunityGameReviewFlagResultRead,
    AdminCommunityGameSupportFlagSummaryRead,
)
from backend.services.admin_action_service import (
    list_admin_actions,
    normalize_idempotency_key,
    normalize_optional_text,
    record_admin_action,
)
from backend.services.admin_permission_service import (
    PERMISSION_AUDIT_READ,
    PERMISSION_AUDIT_SUPPORT_READ,
    PERMISSION_COMMUNITY_GAMES_CANCEL,
    PERMISSION_COMMUNITY_GAMES_FLAG,
    PERMISSION_COMMUNITY_GAMES_HIDE_UNSAFE_CONTENT,
    PERMISSION_COMMUNITY_GAMES_WRITE,
    PERMISSION_MONEY_READ,
    PERMISSION_USERS_READ,
    require_user_admin_permission,
    user_has_admin_permission,
)
from backend.services.support_flag_service import (
    create_support_flag,
    get_existing_support_flag_by_idempotency_key,
    readable_support_flag_types,
)

PARTICIPANT_INACTIVE_STATUSES = {
    "cancelled",
    "late_cancelled",
    "removed",
    "refunded",
}
CONFIRMED_ROSTER_USER_TYPES = {"registered_user", "host", "admin_added"}
PAYMENT_TEXT_STATUS_HIDDEN = "hidden"
PAYMENT_TEXT_STATUS_VISIBLE = "visible"
HIDE_PAYMENT_TEXT_ACTION_TYPE = "hide_unsafe_community_payment_text"
COMMUNITY_REVIEW_FLAG_TYPE = "community_game_review_required"


def parse_uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


def normalize_search_query(value: str | None) -> str | None:
    normalized = " ".join((value or "").strip().lower().split())
    return normalized or None


def build_user_display_name(user: User) -> str:
    if user.deleted_at is not None or user.account_status == "deleted":
        return "Deleted User"

    full_name = " ".join(
        value.strip()
        for value in (user.first_name or "", user.last_name or "")
        if value.strip()
    )
    return full_name or "Pickup Lane Player"


def serialize_host(user: User | None) -> AdminCommunityGameHostRead | None:
    if user is None:
        return None

    return AdminCommunityGameHostRead(
        id=user.id,
        display_name=build_user_display_name(user),
        account_status=(
            "deleted"
            if user.deleted_at is not None or user.account_status == "deleted"
            else user.account_status
        ),
        hosting_status=user.hosting_status,
    )


def get_community_game_or_404(db: Session, game_id: uuid.UUID) -> Game:
    game = db.get(Game, game_id)
    if game is None or game.deleted_at is not None or game.game_type != "community":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Community game not found.",
        )
    return game


def get_community_payment_snapshot(
    db: Session,
    game_id: uuid.UUID,
) -> CommunityGameDetail | None:
    return db.scalar(
        select(CommunityGameDetail).where(CommunityGameDetail.game_id == game_id)
    )


def payment_snapshot_present(snapshot: CommunityGameDetail | None) -> bool:
    if snapshot is None:
        return False
    return bool(
        snapshot.payment_methods_snapshot
        or (snapshot.payment_instructions_snapshot or "").strip()
    )


def build_moderation_state(
    snapshot: CommunityGameDetail | None,
    *,
    review_flag_status: str = "not_flagged",
) -> AdminCommunityGameModerationStateRead:
    is_hidden = (
        snapshot is not None
        and snapshot.payment_text_moderation_status == PAYMENT_TEXT_STATUS_HIDDEN
    )
    return AdminCommunityGameModerationStateRead(
        host_payment_snapshot_present=payment_snapshot_present(snapshot),
        unsafe_payment_text_hidden=is_hidden,
        payment_text_hidden_at=snapshot.payment_text_hidden_at if is_hidden else None,
        payment_text_hidden_by_user_id=(
            snapshot.payment_text_hidden_by_user_id if is_hidden else None
        ),
        payment_text_hidden_reason=(
            snapshot.payment_text_hidden_reason if is_hidden else None
        ),
        review_flag_status=review_flag_status,
    )


def get_community_review_flag_statuses(
    db: Session,
    game_ids: list[uuid.UUID],
) -> dict[uuid.UUID, str]:
    if not game_ids:
        return {}

    rows = db.execute(
        select(SupportFlag.target_game_id, SupportFlag.flag_status).where(
            SupportFlag.flag_type == COMMUNITY_REVIEW_FLAG_TYPE,
            SupportFlag.target_game_id.in_(game_ids),
        )
    ).all()

    statuses: dict[uuid.UUID, str] = {}
    for target_game_id, flag_status in rows:
        if target_game_id is None:
            continue
        if flag_status == "open" or target_game_id not in statuses:
            statuses[target_game_id] = flag_status
    return statuses


def get_community_review_flag_status(
    db: Session,
    game_id: uuid.UUID,
) -> str:
    return get_community_review_flag_statuses(db, [game_id]).get(
        game_id,
        "not_flagged",
    )


def empty_participant_summary() -> AdminCommunityGameParticipantSummaryRead:
    return AdminCommunityGameParticipantSummaryRead()


def summarize_game_participants_by_game(
    db: Session,
    game_ids: list[uuid.UUID],
) -> dict[uuid.UUID, AdminCommunityGameParticipantSummaryRead]:
    unique_game_ids = list(dict.fromkeys(game_ids))
    if not unique_game_ids:
        return {}

    confirmed_participant = GameParticipant.participant_status == "confirmed"
    rows = db.execute(
        select(
            GameParticipant.game_id.label("game_id"),
            func.count(GameParticipant.id).label("total_count"),
            func.sum(
                case((confirmed_participant, 1), else_=0)
            ).label("confirmed_count"),
            func.sum(
                case(
                    (GameParticipant.participant_status == "waitlisted", 1),
                    else_=0,
                )
            ).label("waitlisted_count"),
            func.sum(
                case(
                    (GameParticipant.participant_status == "pending_payment", 1),
                    else_=0,
                )
            ).label("pending_payment_count"),
            func.sum(
                case(
                    (
                        GameParticipant.participant_status.in_(
                            tuple(PARTICIPANT_INACTIVE_STATUSES)
                        ),
                        1,
                    ),
                    else_=0,
                )
            ).label("inactive_count"),
            func.sum(
                case(
                    (
                        and_(
                            confirmed_participant,
                            GameParticipant.participant_type.in_(
                                tuple(CONFIRMED_ROSTER_USER_TYPES)
                            ),
                        ),
                        1,
                    ),
                    else_=0,
                )
            ).label("registered_user_count"),
            func.sum(
                case(
                    (
                        and_(
                            confirmed_participant,
                            GameParticipant.participant_type == "guest",
                        ),
                        1,
                    ),
                    else_=0,
                )
            ).label("guest_count"),
        )
        .where(GameParticipant.game_id.in_(unique_game_ids))
        .group_by(GameParticipant.game_id)
    ).all()

    return {
        row.game_id: AdminCommunityGameParticipantSummaryRead(
            total_count=int(row.total_count or 0),
            confirmed_count=int(row.confirmed_count or 0),
            waitlisted_count=int(row.waitlisted_count or 0),
            pending_payment_count=int(row.pending_payment_count or 0),
            inactive_count=int(row.inactive_count or 0),
            registered_user_count=int(row.registered_user_count or 0),
            guest_count=int(row.guest_count or 0),
        )
        for row in rows
    }


def summarize_game_participants(
    db: Session,
    game_id: uuid.UUID,
) -> AdminCommunityGameParticipantSummaryRead:
    return summarize_game_participants_by_game(db, [game_id]).get(
        game_id,
        empty_participant_summary(),
    )


def serialize_payment_snapshot(
    snapshot: CommunityGameDetail | None,
) -> AdminCommunityGamePaymentSnapshotRead | None:
    if snapshot is None:
        return None

    return AdminCommunityGamePaymentSnapshotRead(
        id=snapshot.id,
        payment_methods_snapshot=snapshot.payment_methods_snapshot,
        payment_instructions_snapshot=snapshot.payment_instructions_snapshot,
        payment_text_moderation_status=snapshot.payment_text_moderation_status,
        payment_text_hidden_at=snapshot.payment_text_hidden_at,
        payment_text_hidden_by_user_id=snapshot.payment_text_hidden_by_user_id,
        payment_text_hidden_reason=snapshot.payment_text_hidden_reason,
        created_at=snapshot.created_at,
        updated_at=snapshot.updated_at,
    )


def serialize_support_flag(
    support_flag: SupportFlag,
) -> AdminCommunityGameSupportFlagSummaryRead:
    return AdminCommunityGameSupportFlagSummaryRead(
        id=support_flag.id,
        flag_type=support_flag.flag_type,
        flag_status=support_flag.flag_status,
        severity=support_flag.severity,
        source=support_flag.source,
        title=support_flag.title,
        summary=support_flag.summary,
        resolution_outcome=support_flag.resolution_outcome,
        resolution_reason=support_flag.resolution_reason,
        resolved_at=support_flag.resolved_at,
        created_at=support_flag.created_at,
        updated_at=support_flag.updated_at,
    )


def normalize_review_flag_request(
    payload: AdminCommunityGameReviewFlagCreate,
) -> tuple[str, str]:
    reason = normalize_optional_text(payload.reason, "reason")
    if reason is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="reason is required.",
        )

    idempotency_key = normalize_idempotency_key(payload.idempotency_key)
    if idempotency_key is None or len(idempotency_key) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="idempotency_key must be at least 8 characters.",
        )

    return reason, idempotency_key


def validate_existing_review_flag(
    support_flag: SupportFlag,
    *,
    game_id: uuid.UUID,
    creator_user_id: uuid.UUID,
    expected_reason: str,
) -> None:
    if (
        support_flag.target_game_id != game_id
        or support_flag.created_by_user_id != creator_user_id
        or support_flag.summary != expected_reason
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "idempotency_key was already used for a different "
                "community game review request."
            ),
        )


def build_review_flag_result(
    db: Session,
    *,
    game: Game,
    support_flag: SupportFlag,
    idempotent_replay: bool,
) -> AdminCommunityGameReviewFlagResultRead:
    return AdminCommunityGameReviewFlagResultRead(
        game_id=game.id,
        support_flag=serialize_support_flag(support_flag),
        moderation_state=build_moderation_state(
            get_community_payment_snapshot(db, game.id),
            review_flag_status=get_community_review_flag_status(db, game.id),
        ),
        idempotent_replay=idempotent_replay,
    )


def flag_admin_community_game_for_review(
    db: Session,
    *,
    game_id: uuid.UUID,
    admin_user: User,
    payload: AdminCommunityGameReviewFlagCreate,
) -> AdminCommunityGameReviewFlagResultRead:
    require_user_admin_permission(admin_user, PERMISSION_COMMUNITY_GAMES_FLAG)
    reason, idempotency_key = normalize_review_flag_request(payload)
    game = get_community_game_or_404(db, game_id)
    db.execute(
        select(Game.id).where(Game.id == game.id).with_for_update()
    ).scalar_one()

    existing_flag = get_existing_support_flag_by_idempotency_key(
        db,
        flag_type=COMMUNITY_REVIEW_FLAG_TYPE,
        idempotency_key=idempotency_key,
    )
    if existing_flag is not None:
        validate_existing_review_flag(
            existing_flag,
            game_id=game.id,
            creator_user_id=admin_user.id,
            expected_reason=reason,
        )
        return build_review_flag_result(
            db,
            game=game,
            support_flag=existing_flag,
            idempotent_replay=True,
        )

    open_flag = db.scalar(
        select(SupportFlag)
        .where(
            SupportFlag.flag_type == COMMUNITY_REVIEW_FLAG_TYPE,
            SupportFlag.target_game_id == game.id,
            SupportFlag.flag_status == "open",
        )
        .order_by(SupportFlag.created_at.desc(), SupportFlag.id.desc())
        .limit(1)
    )
    if open_flag is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Community game is already flagged for review.",
        )

    try:
        support_flag = create_support_flag(
            db,
            flag_type=COMMUNITY_REVIEW_FLAG_TYPE,
            source="admin",
            title="Community game review required",
            summary=reason,
            severity="attention",
            metadata={
                "source": "admin_community_game_detail",
                "game_status": game.game_status,
                "publish_status": game.publish_status,
            },
            idempotency_key=idempotency_key,
            created_by_user_id=admin_user.id,
            target_game_id=game.id,
        )
    except HTTPException as exc:
        if exc.status_code != status.HTTP_409_CONFLICT:
            raise
        existing_flag = get_existing_support_flag_by_idempotency_key(
            db,
            flag_type=COMMUNITY_REVIEW_FLAG_TYPE,
            idempotency_key=idempotency_key,
        )
        if existing_flag is None:
            raise
        validate_existing_review_flag(
            existing_flag,
            game_id=game.id,
            creator_user_id=admin_user.id,
            expected_reason=reason,
        )
        return build_review_flag_result(
            db,
            game=game,
            support_flag=existing_flag,
            idempotent_replay=True,
        )

    return build_review_flag_result(
        db,
        game=game,
        support_flag=support_flag,
        idempotent_replay=False,
    )


def normalize_hide_payment_text_request(
    payload: AdminCommunityGameHidePaymentTextCreate,
) -> tuple[str, str]:
    reason = normalize_optional_text(payload.reason, "reason")
    if reason is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="reason is required.",
        )

    idempotency_key = normalize_idempotency_key(payload.idempotency_key)
    if idempotency_key is None or len(idempotency_key) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="idempotency_key must be at least 8 characters.",
        )

    return reason, idempotency_key


def get_existing_hide_payment_text_action(
    db: Session,
    *,
    admin_user_id: uuid.UUID,
    game_id: uuid.UUID,
    idempotency_key: str,
) -> AdminAction | None:
    return db.scalar(
        select(AdminAction)
        .where(
            AdminAction.action_type == HIDE_PAYMENT_TEXT_ACTION_TYPE,
            AdminAction.admin_user_id == admin_user_id,
            AdminAction.target_game_id == game_id,
            AdminAction.idempotency_key == idempotency_key,
        )
        .order_by(AdminAction.created_at.desc(), AdminAction.id.desc())
        .limit(1)
    )


def validate_existing_hide_payment_text_action(
    action: AdminAction,
    *,
    expected_reason: str,
) -> None:
    if action.reason != expected_reason:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "idempotency_key was already used for a different "
                "payment text moderation request."
            ),
        )


def build_hide_payment_text_metadata(
    snapshot: CommunityGameDetail,
    *,
    old_status: str,
    new_status: str,
) -> dict[str, object]:
    method_count = (
        len(snapshot.payment_methods_snapshot)
        if isinstance(snapshot.payment_methods_snapshot, list)
        else 0
    )
    had_payment_instructions = bool(
        (snapshot.payment_instructions_snapshot or "").strip()
    )
    return {
        "source": "admin_community_game_detail",
        "before": {
            "payment_text_moderation_status": old_status,
            "payment_method_count": method_count,
            "had_payment_instructions": had_payment_instructions,
        },
        "after": {
            "payment_text_moderation_status": new_status,
            "payment_method_count": method_count,
            "had_payment_instructions": had_payment_instructions,
        },
    }


def build_hide_payment_text_result(
    db: Session,
    *,
    game_id: uuid.UUID,
    snapshot: CommunityGameDetail,
    audit_action: AdminAction,
    idempotent_replay: bool,
) -> AdminCommunityGameHidePaymentTextResultRead:
    payment_snapshot = serialize_payment_snapshot(snapshot)
    if payment_snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No host payment text is available to hide.",
        )

    return AdminCommunityGameHidePaymentTextResultRead(
        game_id=game_id,
        payment_snapshot=payment_snapshot,
        moderation_state=build_moderation_state(
            snapshot,
            review_flag_status=get_community_review_flag_status(db, game_id),
        ),
        audit_action_id=audit_action.id,
        idempotent_replay=idempotent_replay,
    )


def hide_admin_community_game_payment_text(
    db: Session,
    *,
    game_id: uuid.UUID,
    admin_user: User,
    payload: AdminCommunityGameHidePaymentTextCreate,
) -> AdminCommunityGameHidePaymentTextResultRead:
    require_user_admin_permission(
        admin_user,
        PERMISSION_COMMUNITY_GAMES_HIDE_UNSAFE_CONTENT,
    )
    reason, idempotency_key = normalize_hide_payment_text_request(payload)
    game = get_community_game_or_404(db, game_id)

    existing_action = get_existing_hide_payment_text_action(
        db,
        admin_user_id=admin_user.id,
        game_id=game.id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        validate_existing_hide_payment_text_action(
            existing_action,
            expected_reason=reason,
        )
        snapshot = get_community_payment_snapshot(db, game.id)
        if snapshot is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Moderation audit exists but payment snapshot is missing.",
            )
        return build_hide_payment_text_result(
            db,
            game_id=game.id,
            snapshot=snapshot,
            audit_action=existing_action,
            idempotent_replay=True,
        )

    snapshot = db.scalar(
        select(CommunityGameDetail)
        .where(CommunityGameDetail.game_id == game.id)
        .with_for_update()
    )

    existing_action = get_existing_hide_payment_text_action(
        db,
        admin_user_id=admin_user.id,
        game_id=game.id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        validate_existing_hide_payment_text_action(
            existing_action,
            expected_reason=reason,
        )
        if snapshot is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Moderation audit exists but payment snapshot is missing.",
            )
        return build_hide_payment_text_result(
            db,
            game_id=game.id,
            snapshot=snapshot,
            audit_action=existing_action,
            idempotent_replay=True,
        )

    if snapshot is None or not payment_snapshot_present(snapshot):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No host payment text is available to hide.",
        )

    if snapshot.payment_text_moderation_status == PAYMENT_TEXT_STATUS_HIDDEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Host payment text is already hidden.",
        )

    now = datetime.now(timezone.utc)
    old_status = snapshot.payment_text_moderation_status or PAYMENT_TEXT_STATUS_VISIBLE
    snapshot.payment_text_moderation_status = PAYMENT_TEXT_STATUS_HIDDEN
    snapshot.payment_text_hidden_at = now
    snapshot.payment_text_hidden_by_user_id = admin_user.id
    snapshot.payment_text_hidden_reason = reason
    snapshot.updated_at = now
    audit_action = record_admin_action(
        db,
        admin_user_id=admin_user.id,
        action_type=HIDE_PAYMENT_TEXT_ACTION_TYPE,
        target_game_id=game.id,
        target_user_id=game.host_user_id,
        reason=reason,
        metadata=build_hide_payment_text_metadata(
            snapshot,
            old_status=old_status,
            new_status=PAYMENT_TEXT_STATUS_HIDDEN,
        ),
        idempotency_key=idempotency_key,
        created_at=now,
    )

    try:
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        db.refresh(audit_action)
    except IntegrityError as exc:
        db.rollback()
        existing_action = get_existing_hide_payment_text_action(
            db,
            admin_user_id=admin_user.id,
            game_id=game.id,
            idempotency_key=idempotency_key,
        )
        if existing_action is not None:
            validate_existing_hide_payment_text_action(
                existing_action,
                expected_reason=reason,
            )
            snapshot = get_community_payment_snapshot(db, game.id)
            if snapshot is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Moderation audit exists but payment snapshot is missing.",
                ) from exc
            return build_hide_payment_text_result(
                db,
                game_id=game.id,
                snapshot=snapshot,
                audit_action=existing_action,
                idempotent_replay=True,
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Host payment text could not be hidden.",
        ) from exc

    return build_hide_payment_text_result(
        db,
        game_id=game.id,
        snapshot=snapshot,
        audit_action=audit_action,
        idempotent_replay=False,
    )


def get_publish_fee_row(
    db: Session,
    game_id: uuid.UUID,
) -> tuple[HostPublishFee, str | None] | None:
    row = db.execute(
        select(HostPublishFee, Payment.payment_status)
        .outerjoin(Payment, HostPublishFee.payment_id == Payment.id)
        .where(HostPublishFee.game_id == game_id)
    ).first()

    if row is None:
        return None

    return row[0], row[1]


def serialize_publish_fee(
    fee_row: tuple[HostPublishFee, str | None] | None,
) -> AdminCommunityGamePublishFeeRead | None:
    if fee_row is None:
        return None

    fee, payment_status = fee_row
    return AdminCommunityGamePublishFeeRead(
        id=fee.id,
        amount_cents=fee.amount_cents,
        currency=fee.currency,
        fee_status=fee.fee_status,
        waiver_reason=fee.waiver_reason,
        paid_at=fee.paid_at,
        payment_status=payment_status,
        created_at=fee.created_at,
        updated_at=fee.updated_at,
    )


def list_community_game_support_flags(
    db: Session,
    *,
    game_id: uuid.UUID,
    viewer_user: User,
    offset: int,
    limit: int,
) -> tuple[list[AdminCommunityGameSupportFlagSummaryRead], int]:
    readable_flag_types = readable_support_flag_types(viewer_user)
    if not readable_flag_types:
        return [], 0

    statement = (
        select(SupportFlag)
        .where(
            SupportFlag.target_game_id == game_id,
            SupportFlag.flag_type.in_(readable_flag_types),
        )
        .order_by(SupportFlag.created_at.desc(), SupportFlag.id.desc())
    )
    count_statement = select(func.count()).select_from(
        statement.with_only_columns(SupportFlag.id).order_by(None).subquery()
    )
    total_count = int(db.scalar(count_statement) or 0)
    flags = db.scalars(statement.offset(offset).limit(limit)).all()

    return [serialize_support_flag(flag) for flag in flags], total_count


def list_community_game_audit_actions(
    db: Session,
    *,
    game_id: uuid.UUID,
    viewer_user: User,
    offset: int,
    limit: int,
) -> tuple[list[AdminCommunityGameAuditActionSummaryRead], int]:
    can_read_audit = user_has_admin_permission(
        viewer_user,
        PERMISSION_AUDIT_READ,
    ) or user_has_admin_permission(viewer_user, PERMISSION_AUDIT_SUPPORT_READ)
    if not can_read_audit:
        return [], 0

    all_actions = list_admin_actions(
        db,
        viewer_user=viewer_user,
        target_filters={"target_game_id": game_id},
        limit=None,
    )
    total_count = len(all_actions)
    actions = all_actions[offset : offset + limit]
    return [
        AdminCommunityGameAuditActionSummaryRead(
            id=action.id,
            admin_user_id=action.admin_user_id,
            action_type=action.action_type,
            reason=action.reason,
            created_at=action.created_at,
        )
        for action in actions
    ], total_count


def build_capabilities(viewer_user: User) -> AdminCommunityGameCapabilitiesRead:
    return AdminCommunityGameCapabilitiesRead(
        can_read_audit=(
            user_has_admin_permission(viewer_user, PERMISSION_AUDIT_READ)
            or user_has_admin_permission(viewer_user, PERMISSION_AUDIT_SUPPORT_READ)
        ),
        can_read_publish_fee=user_has_admin_permission(
            viewer_user,
            PERMISSION_MONEY_READ,
        ),
        can_flag_game=user_has_admin_permission(
            viewer_user,
            PERMISSION_COMMUNITY_GAMES_FLAG,
        ),
        can_resolve_review_flags=user_has_admin_permission(
            viewer_user,
            PERMISSION_COMMUNITY_GAMES_WRITE,
        ),
        can_hide_unsafe_payment_text=user_has_admin_permission(
            viewer_user,
            PERMISSION_COMMUNITY_GAMES_HIDE_UNSAFE_CONTENT,
        ),
        can_cancel_game=user_has_admin_permission(
            viewer_user,
            PERMISSION_COMMUNITY_GAMES_CANCEL,
        ),
    )


def serialize_list_item(
    *,
    game: Game,
    host: User | None,
    participant_summary: AdminCommunityGameParticipantSummaryRead,
    review_flag_status: str,
    snapshot: CommunityGameDetail | None,
) -> AdminCommunityGameListItemRead:
    return AdminCommunityGameListItemRead(
        id=game.id,
        title=game.title,
        publish_status=game.publish_status,
        game_status=game.game_status,
        payment_collection_type=game.payment_collection_type,
        starts_at=game.starts_at,
        ends_at=game.ends_at,
        timezone=game.timezone,
        city=game.city_snapshot,
        state=game.state_snapshot,
        price_per_player_cents=game.price_per_player_cents,
        total_spots=game.total_spots,
        host=serialize_host(host),
        participant_summary=participant_summary,
        moderation_state=build_moderation_state(
            snapshot,
            review_flag_status=review_flag_status,
        ),
        created_at=game.created_at,
        updated_at=game.updated_at,
    )


def list_admin_community_games(
    db: Session,
    *,
    viewer_user: User,
    query: str | None = None,
    game_status: str | None = None,
    publish_status: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[AdminCommunityGameListItemRead], int]:
    statement = (
        select(Game, User, CommunityGameDetail)
        .outerjoin(User, Game.host_user_id == User.id)
        .outerjoin(CommunityGameDetail, CommunityGameDetail.game_id == Game.id)
        .where(Game.game_type == "community", Game.deleted_at.is_(None))
    )

    if game_status is not None:
        statement = statement.where(Game.game_status == game_status)

    if publish_status is not None:
        statement = statement.where(Game.publish_status == publish_status)

    normalized_query = normalize_search_query(query)
    if normalized_query is not None:
        query_uuid = parse_uuid(normalized_query)
        text_match = f"%{normalized_query}%"
        search_conditions = [
            func.lower(Game.title).like(text_match),
            func.lower(Game.city_snapshot).like(text_match),
            func.lower(Game.state_snapshot).like(text_match),
            func.lower(func.coalesce(User.first_name, "")).like(text_match),
            func.lower(func.coalesce(User.last_name, "")).like(text_match),
        ]
        if user_has_admin_permission(viewer_user, PERMISSION_USERS_READ):
            search_conditions.append(
                func.lower(func.coalesce(User.email, "")).like(text_match)
            )
        if query_uuid is not None:
            search_conditions.append(Game.id == query_uuid)
            search_conditions.append(Game.host_user_id == query_uuid)
        statement = statement.where(or_(*search_conditions))

    count_statement = select(func.count()).select_from(
        statement.with_only_columns(Game.id).order_by(None).subquery()
    )
    total_count = int(db.scalar(count_statement) or 0)
    rows = db.execute(
        statement.order_by(Game.starts_at.desc(), Game.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    review_statuses = get_community_review_flag_statuses(
        db,
        [game.id for game, _, _ in rows],
    )
    participant_summaries = summarize_game_participants_by_game(
        db,
        [game.id for game, _, _ in rows],
    )

    return (
        [
            serialize_list_item(
                game=game,
                host=host,
                participant_summary=participant_summaries.get(
                    game.id,
                    empty_participant_summary(),
                ),
                review_flag_status=review_statuses.get(game.id, "not_flagged"),
                snapshot=snapshot,
            )
            for game, host, snapshot in rows
        ],
        total_count,
    )


def get_admin_community_game_detail(
    db: Session,
    *,
    game_id: uuid.UUID,
    viewer_user: User,
    support_flag_offset: int = 0,
    support_flag_limit: int = 50,
    audit_offset: int = 0,
    audit_limit: int = 50,
) -> AdminCommunityGameDetailRead:
    game = get_community_game_or_404(db, game_id)
    host = db.get(User, game.host_user_id) if game.host_user_id is not None else None
    payment_snapshot = get_community_payment_snapshot(db, game.id)
    capabilities = build_capabilities(viewer_user)

    support_flags, support_flag_total_count = list_community_game_support_flags(
        db,
        game_id=game.id,
        viewer_user=viewer_user,
        offset=support_flag_offset,
        limit=support_flag_limit,
    )
    audit_actions, audit_total_count = list_community_game_audit_actions(
        db,
        game_id=game.id,
        viewer_user=viewer_user,
        offset=audit_offset,
        limit=audit_limit,
    )

    return AdminCommunityGameDetailRead(
        game=game,
        host=serialize_host(host),
        participant_summary=summarize_game_participants(db, game.id),
        payment_snapshot=serialize_payment_snapshot(payment_snapshot),
        publish_fee=(
            serialize_publish_fee(get_publish_fee_row(db, game.id))
            if capabilities.can_read_publish_fee
            else None
        ),
        support_flags=support_flags,
        support_flag_total_count=support_flag_total_count,
        support_flag_offset=support_flag_offset,
        support_flag_limit=support_flag_limit,
        audit_actions=audit_actions,
        audit_total_count=audit_total_count,
        audit_offset=audit_offset,
        audit_limit=audit_limit,
        moderation_state=build_moderation_state(
            payment_snapshot,
            review_flag_status=get_community_review_flag_status(db, game.id),
        ),
        capabilities=capabilities,
    )
