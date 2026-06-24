"""Admin account-deletion impact preview workflows."""

import hashlib
import json
import uuid
from dataclasses import dataclass, fields
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.firebase_admin_client import FirebaseAdminConfigError, delete_firebase_user
from backend.models import (
    AdminAction,
    Booking,
    Game,
    GameCredit,
    GameParticipant,
    Payment,
    Refund,
    SubPost,
    SubPostRequest,
    SupportFlag,
    User,
    UserPaymentMethod,
    WaitlistEntry,
)
from backend.schemas.admin_user_schema import (
    AdminUserDeleteCreate,
    AdminUserDeleteImpactGameRead,
    AdminUserDeleteImpactPreviewRead,
    AdminUserDeleteResultRead,
)
from backend.services.admin_action_service import record_admin_action
from backend.services.admin_rejected_attempt_policy import (
    ATTEMPT_TYPE_DELETE_USER_REJECTED,
    REJECTION_DOMAIN_REJECTED_POSTLOAD,
)
from backend.services.admin_rejected_attempt_service import (
    record_admin_rejected_attempt,
)
from backend.services.admin_user_service import (
    count_active_admins,
    get_admin_user_or_404,
)
from backend.services.account_deletion_service import (
    anonymize_user,
    cancel_future_user_activity,
    detach_account_saved_payment_methods,
    lock_user_and_active_admins_for_account_removal,
    record_account_delete_partial_failure,
)
from backend.services.game_rules import (
    ACTIVE_BOOKING_STATUSES,
    ACTIVE_JOIN_STATUSES,
    OPEN_GAME_STATUSES,
)
from backend.services.need_a_sub_rules import (
    ACTIVE_REQUEST_STATUSES,
    ACTIVE_VISIBLE_POST_STATUSES,
)
from backend.services.user_service import build_user_conflict_detail

DELETE_PREVIEW_WAITLIST_STATUSES = (
    "active",
    "promoted",
    "payment_processing",
    "accepted",
)
DELETE_PREVIEW_GAME_LIMIT = 100
DELETE_PREVIEW_BLOCKING_MESSAGES = {
    "deleted": "Deleted accounts cannot be deleted again.",
    "pending_deletion": "Accounts pending deletion cannot be deleted by admin.",
    "last_active_admin": "The last active admin cannot be deleted.",
    "future_official_host": (
        "Remove the user from all future official host assignments before deletion."
    ),
}
DELETE_USER_ROUTE_PATH = "/admin/users/{user_id}/delete"


@dataclass(frozen=True)
class DeleteImpactMetric:
    count: int
    max_updated_at: datetime | None


@dataclass(frozen=True)
class DeleteImpactSnapshot:
    future_official_host_assignments: DeleteImpactMetric
    future_community_hosted_games: DeleteImpactMetric
    active_future_bookings: DeleteImpactMetric
    active_future_official_bookings: DeleteImpactMetric
    active_future_participations: DeleteImpactMetric
    active_future_guests: DeleteImpactMetric
    active_waitlist_entries: DeleteImpactMetric
    active_owned_sub_posts: DeleteImpactMetric
    active_sub_requests: DeleteImpactMetric
    payment_records: DeleteImpactMetric
    refund_records: DeleteImpactMetric
    game_credits: DeleteImpactMetric
    saved_payment_methods: DeleteImpactMetric
    active_saved_payment_methods: DeleteImpactMetric
    active_support_flags: DeleteImpactMetric


def isoformat_optional(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def metric_from_row(
    count: int | None,
    max_updated_at: datetime | None,
) -> DeleteImpactMetric:
    return DeleteImpactMetric(
        count=int(count or 0),
        max_updated_at=max_updated_at,
    )


def fetch_metric(db: Session, statement) -> DeleteImpactMetric:
    count, max_updated_at = db.execute(statement).one()
    return metric_from_row(count, max_updated_at)


def future_hosted_game_filters(
    *,
    user_id: uuid.UUID,
    game_type: str,
    now: datetime,
):
    filters = [
        Game.host_user_id == user_id,
        Game.game_type == game_type,
        Game.game_status.in_(OPEN_GAME_STATUSES),
        Game.starts_at > now,
        Game.deleted_at.is_(None),
    ]
    return filters


def list_future_hosted_games(
    db: Session,
    *,
    user_id: uuid.UUID,
    game_type: str,
    now: datetime,
) -> list[Game]:
    return list(
        db.scalars(
            select(Game)
            .where(
                *future_hosted_game_filters(
                    user_id=user_id,
                    game_type=game_type,
                    now=now,
                )
            )
            .order_by(Game.starts_at.asc(), Game.id.asc())
            .limit(DELETE_PREVIEW_GAME_LIMIT)
        ).all()
    )


def future_hosted_game_metric(
    db: Session,
    *,
    user_id: uuid.UUID,
    game_type: str,
    now: datetime,
) -> DeleteImpactMetric:
    return fetch_metric(
        db,
        select(func.count(), func.max(Game.updated_at))
        .select_from(Game)
        .where(
            *future_hosted_game_filters(
                user_id=user_id,
                game_type=game_type,
                now=now,
            )
        ),
    )


def active_future_booking_metric(
    db: Session,
    *,
    user_id: uuid.UUID,
    now: datetime,
    game_type: str | None = None,
) -> DeleteImpactMetric:
    filters = [
        Booking.buyer_user_id == user_id,
        Booking.booking_status.in_(ACTIVE_BOOKING_STATUSES),
        Game.game_status.in_(OPEN_GAME_STATUSES),
        Game.starts_at > now,
        Game.deleted_at.is_(None),
    ]
    if game_type is not None:
        filters.append(Game.game_type == game_type)

    return fetch_metric(
        db,
        select(func.count(), func.max(Booking.updated_at))
        .select_from(Booking)
        .join(Game, Booking.game_id == Game.id)
        .where(*filters),
    )


def active_future_participant_metric(
    db: Session,
    *,
    user_id: uuid.UUID,
    now: datetime,
    participant_user_field,
) -> DeleteImpactMetric:
    return fetch_metric(
        db,
        select(func.count(), func.max(GameParticipant.updated_at))
        .select_from(GameParticipant)
        .join(Game, GameParticipant.game_id == Game.id)
        .where(
            participant_user_field == user_id,
            GameParticipant.participant_status.in_(ACTIVE_JOIN_STATUSES),
            Game.game_status.in_(OPEN_GAME_STATUSES),
            Game.starts_at > now,
            Game.deleted_at.is_(None),
        ),
    )


def active_waitlist_entry_metric(
    db: Session,
    *,
    user_id: uuid.UUID,
) -> DeleteImpactMetric:
    return fetch_metric(
        db,
        select(func.count(), func.max(WaitlistEntry.updated_at))
        .select_from(WaitlistEntry)
        .where(
            WaitlistEntry.user_id == user_id,
            WaitlistEntry.waitlist_status.in_(DELETE_PREVIEW_WAITLIST_STATUSES),
        ),
    )


def active_owned_sub_post_metric(
    db: Session,
    *,
    user_id: uuid.UUID,
) -> DeleteImpactMetric:
    return fetch_metric(
        db,
        select(func.count(), func.max(SubPost.updated_at))
        .select_from(SubPost)
        .where(
            SubPost.owner_user_id == user_id,
            SubPost.post_status.in_(ACTIVE_VISIBLE_POST_STATUSES),
        ),
    )


def active_sub_request_metric(
    db: Session,
    *,
    user_id: uuid.UUID,
) -> DeleteImpactMetric:
    return fetch_metric(
        db,
        select(func.count(), func.max(SubPostRequest.updated_at))
        .select_from(SubPostRequest)
        .where(
            SubPostRequest.requester_user_id == user_id,
            SubPostRequest.request_status.in_(ACTIVE_REQUEST_STATUSES),
        ),
    )


def payment_record_metric(
    db: Session,
    *,
    user_id: uuid.UUID,
) -> DeleteImpactMetric:
    return fetch_metric(
        db,
        select(func.count(), func.max(Payment.updated_at))
        .select_from(Payment)
        .where(Payment.payer_user_id == user_id),
    )


def refund_record_metric(
    db: Session,
    *,
    user_id: uuid.UUID,
) -> DeleteImpactMetric:
    user_payment_ids = select(Payment.id).where(Payment.payer_user_id == user_id)
    user_booking_ids = select(Booking.id).where(Booking.buyer_user_id == user_id)
    user_participant_ids = select(GameParticipant.id).where(
        GameParticipant.user_id == user_id
    )

    return fetch_metric(
        db,
        select(func.count(func.distinct(Refund.id)), func.max(Refund.updated_at))
        .select_from(Refund)
        .where(
            or_(
                Refund.payment_id.in_(user_payment_ids),
                Refund.booking_id.in_(user_booking_ids),
                Refund.participant_id.in_(user_participant_ids),
                Refund.requested_by_user_id == user_id,
                Refund.approved_by_user_id == user_id,
            )
        ),
    )


def game_credit_metric(
    db: Session,
    *,
    user_id: uuid.UUID,
) -> DeleteImpactMetric:
    return fetch_metric(
        db,
        select(func.count(), func.max(GameCredit.updated_at))
        .select_from(GameCredit)
        .where(GameCredit.user_id == user_id),
    )


def saved_payment_method_metric(
    db: Session,
    *,
    user_id: uuid.UUID,
    method_status: str | None = None,
) -> DeleteImpactMetric:
    filters = [UserPaymentMethod.user_id == user_id]
    if method_status is not None:
        filters.append(UserPaymentMethod.method_status == method_status)

    return fetch_metric(
        db,
        select(func.count(), func.max(UserPaymentMethod.updated_at))
        .select_from(UserPaymentMethod)
        .where(*filters),
    )


def active_support_flag_metric(
    db: Session,
    *,
    user_id: uuid.UUID,
) -> DeleteImpactMetric:
    return fetch_metric(
        db,
        select(func.count(), func.max(SupportFlag.updated_at))
        .select_from(SupportFlag)
        .where(
            SupportFlag.target_user_id == user_id,
            SupportFlag.flag_status == "open",
        ),
    )


def build_delete_impact_snapshot(
    db: Session,
    *,
    user_id: uuid.UUID,
    now: datetime,
) -> DeleteImpactSnapshot:
    return DeleteImpactSnapshot(
        future_official_host_assignments=future_hosted_game_metric(
            db,
            user_id=user_id,
            game_type="official",
            now=now,
        ),
        future_community_hosted_games=future_hosted_game_metric(
            db,
            user_id=user_id,
            game_type="community",
            now=now,
        ),
        active_future_bookings=active_future_booking_metric(
            db,
            user_id=user_id,
            now=now,
        ),
        active_future_official_bookings=active_future_booking_metric(
            db,
            user_id=user_id,
            now=now,
            game_type="official",
        ),
        active_future_participations=active_future_participant_metric(
            db,
            user_id=user_id,
            now=now,
            participant_user_field=GameParticipant.user_id,
        ),
        active_future_guests=active_future_participant_metric(
            db,
            user_id=user_id,
            now=now,
            participant_user_field=GameParticipant.guest_of_user_id,
        ),
        active_waitlist_entries=active_waitlist_entry_metric(db, user_id=user_id),
        active_owned_sub_posts=active_owned_sub_post_metric(db, user_id=user_id),
        active_sub_requests=active_sub_request_metric(db, user_id=user_id),
        payment_records=payment_record_metric(db, user_id=user_id),
        refund_records=refund_record_metric(db, user_id=user_id),
        game_credits=game_credit_metric(db, user_id=user_id),
        saved_payment_methods=saved_payment_method_metric(db, user_id=user_id),
        active_saved_payment_methods=saved_payment_method_metric(
            db,
            user_id=user_id,
            method_status="active",
        ),
        active_support_flags=active_support_flag_metric(db, user_id=user_id),
    )


def serialize_delete_impact_game(game: Game) -> AdminUserDeleteImpactGameRead:
    return AdminUserDeleteImpactGameRead(
        id=game.id,
        title=game.title,
        game_type=game.game_type,
        game_status=game.game_status,
        starts_at=game.starts_at,
        city=game.city_snapshot,
        state=game.state_snapshot,
    )


def delete_preview_blocking_reason_codes(
    *,
    user: User,
    active_admin_count: int,
    snapshot: DeleteImpactSnapshot,
) -> list[str]:
    reason_codes: list[str] = []

    if user.deleted_at is not None or user.account_status == "deleted":
        reason_codes.append("deleted")
    elif user.account_status == "pending_deletion":
        reason_codes.append("pending_deletion")

    if (
        user.role == "admin"
        and user.account_status == "active"
        and user.deleted_at is None
        and active_admin_count <= 1
    ):
        reason_codes.append("last_active_admin")

    if snapshot.future_official_host_assignments.count:
        reason_codes.append("future_official_host")

    return reason_codes


def metric_snapshot(metric: DeleteImpactMetric) -> dict:
    return {
        "count": metric.count,
        "max_updated_at": isoformat_optional(metric.max_updated_at),
    }


def delete_impact_preview_snapshot_token(
    *,
    user: User,
    active_admin_count: int,
    snapshot: DeleteImpactSnapshot,
    future_official_host_assignments: list[Game],
    future_community_hosted_games: list[Game],
) -> str:
    token_snapshot = {
        "user": {
            "id": str(user.id),
            "role": user.role,
            "account_status": user.account_status,
            "hosting_status": user.hosting_status,
            "deleted_at": isoformat_optional(user.deleted_at),
            "updated_at": user.updated_at.isoformat(),
        },
        "active_admin_count": active_admin_count,
        "metrics": {
            snapshot_field.name: metric_snapshot(
                getattr(snapshot, snapshot_field.name)
            )
            for snapshot_field in fields(snapshot)
        },
        "future_official_host_assignments": [
            {
                "id": str(game.id),
                "game_status": game.game_status,
                "starts_at": game.starts_at.isoformat(),
                "host_user_id": (
                    str(game.host_user_id) if game.host_user_id is not None else None
                ),
                "deleted_at": isoformat_optional(game.deleted_at),
                "updated_at": game.updated_at.isoformat(),
            }
            for game in future_official_host_assignments
        ],
        "future_community_hosted_games": [
            {
                "id": str(game.id),
                "game_status": game.game_status,
                "publish_status": game.publish_status,
                "starts_at": game.starts_at.isoformat(),
                "host_user_id": (
                    str(game.host_user_id) if game.host_user_id is not None else None
                ),
                "deleted_at": isoformat_optional(game.deleted_at),
                "updated_at": game.updated_at.isoformat(),
            }
            for game in future_community_hosted_games
        ],
    }
    encoded_snapshot = json.dumps(
        token_snapshot,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded_snapshot).hexdigest()


def build_admin_user_delete_impact_preview(
    *,
    user: User,
    active_admin_count: int,
    snapshot: DeleteImpactSnapshot,
    future_official_host_assignments: list[Game],
    future_community_hosted_games: list[Game],
) -> AdminUserDeleteImpactPreviewRead:
    blocking_reason_codes = delete_preview_blocking_reason_codes(
        user=user,
        active_admin_count=active_admin_count,
        snapshot=snapshot,
    )

    return AdminUserDeleteImpactPreviewRead(
        user_id=user.id,
        account_status=user.account_status,
        role=user.role,
        hosting_status=user.hosting_status,
        can_delete=not blocking_reason_codes,
        preview_token=delete_impact_preview_snapshot_token(
            user=user,
            active_admin_count=active_admin_count,
            snapshot=snapshot,
            future_official_host_assignments=future_official_host_assignments,
            future_community_hosted_games=future_community_hosted_games,
        ),
        blocking_reasons=[
            DELETE_PREVIEW_BLOCKING_MESSAGES[reason_code]
            for reason_code in blocking_reason_codes
        ],
        future_official_host_assignment_count=(
            snapshot.future_official_host_assignments.count
        ),
        future_official_host_assignments=[
            serialize_delete_impact_game(game)
            for game in future_official_host_assignments
        ],
        future_community_hosted_game_count=snapshot.future_community_hosted_games.count,
        future_community_hosted_games=[
            serialize_delete_impact_game(game)
            for game in future_community_hosted_games
        ],
        active_future_booking_count=snapshot.active_future_bookings.count,
        active_future_official_booking_count=(
            snapshot.active_future_official_bookings.count
        ),
        active_future_participation_count=(
            snapshot.active_future_participations.count
        ),
        active_future_guest_count=snapshot.active_future_guests.count,
        active_waitlist_entry_count=snapshot.active_waitlist_entries.count,
        active_owned_sub_post_count=snapshot.active_owned_sub_posts.count,
        active_sub_request_count=snapshot.active_sub_requests.count,
        payment_record_count=snapshot.payment_records.count,
        refund_record_count=snapshot.refund_records.count,
        game_credit_count=snapshot.game_credits.count,
        saved_payment_method_count=snapshot.saved_payment_methods.count,
        active_saved_payment_method_count=snapshot.active_saved_payment_methods.count,
        active_support_flag_count=snapshot.active_support_flags.count,
    )


def preview_admin_user_delete_impact(
    db: Session,
    *,
    user_id: uuid.UUID,
) -> AdminUserDeleteImpactPreviewRead:
    user = get_admin_user_or_404(db, user_id)
    now = datetime.now(timezone.utc)
    snapshot = build_delete_impact_snapshot(db, user_id=user.id, now=now)
    future_official_host_assignments = list_future_hosted_games(
        db,
        user_id=user.id,
        game_type="official",
        now=now,
    )
    future_community_hosted_games = list_future_hosted_games(
        db,
        user_id=user.id,
        game_type="community",
        now=now,
    )
    return build_admin_user_delete_impact_preview(
        user=user,
        active_admin_count=count_active_admins(db),
        snapshot=snapshot,
        future_official_host_assignments=future_official_host_assignments,
        future_community_hosted_games=future_community_hosted_games,
    )


def normalize_delete_request(payload: AdminUserDeleteCreate) -> tuple[str, str]:
    reason = " ".join(payload.reason.strip().split())
    if not reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="reason is required.",
        )

    idempotency_key = payload.idempotency_key.strip()
    if len(idempotency_key) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="idempotency_key must be at least 8 characters.",
        )

    return reason, idempotency_key


def get_existing_delete_action(
    db: Session,
    *,
    admin_user_id: uuid.UUID,
    user_id: uuid.UUID,
    idempotency_key: str,
) -> AdminAction | None:
    return db.scalar(
        select(AdminAction).where(
            AdminAction.admin_user_id == admin_user_id,
            AdminAction.action_type == "delete_user",
            AdminAction.target_user_id == user_id,
            AdminAction.idempotency_key == idempotency_key,
        )
    )


def build_delete_result(
    db: Session,
    *,
    action: AdminAction,
    expected_preview_snapshot_hash: str,
    expected_reason: str,
) -> AdminUserDeleteResultRead:
    if action.target_user_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The prior account deletion result is incomplete.",
        )

    user = db.get(User, action.target_user_id)
    metadata = action.metadata_ or {}
    after = metadata.get("after") or {}
    reviewed = metadata.get("reviewed") or {}
    deleted_at_value = after.get("deleted_at")
    preview_snapshot_hash = reviewed.get("preview_snapshot_hash")
    if user is None or not deleted_at_value or not preview_snapshot_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The prior account deletion result is incomplete.",
        )
    if (
        action.reason != expected_reason
        or preview_snapshot_hash != expected_preview_snapshot_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "idempotency_key was already used for a different "
                "account deletion request."
            ),
        )

    deleted_at = (
        datetime.fromisoformat(deleted_at_value)
        if isinstance(deleted_at_value, str)
        else deleted_at_value
    )
    return AdminUserDeleteResultRead(
        user_id=user.id,
        account_status=user.account_status,
        deleted_at=deleted_at,
        admin_action_id=action.id,
    )


def lock_delete_users(
    db: Session,
    *,
    user_id: uuid.UUID,
) -> tuple[User, int]:
    return lock_user_and_active_admins_for_account_removal(
        db,
        user_id=user_id,
    )


def reject_guarded_delete(
    db: Session,
    *,
    admin_user: User,
    target_user: User,
    reason_codes: list[str],
    preview: AdminUserDeleteImpactPreviewRead,
    route_method: str,
    route_path: str,
) -> None:
    record_admin_rejected_attempt(
        db,
        admin_user_id=admin_user.id,
        attempt_type=ATTEMPT_TYPE_DELETE_USER_REJECTED,
        rejection_mode=REJECTION_DOMAIN_REJECTED_POSTLOAD,
        response_status_code=status.HTTP_409_CONFLICT,
        route_method=route_method,
        route_path=route_path,
        target_user_id=target_user.id,
        metadata={
            "reason_codes": reason_codes,
            "role": target_user.role,
            "account_status": target_user.account_status,
            "future_official_host_assignment_count": (
                preview.future_official_host_assignment_count
            ),
        },
    )
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=DELETE_PREVIEW_BLOCKING_MESSAGES[reason_codes[0]],
    )


def record_admin_delete_partial_failure(
    db: Session,
    *,
    admin_user_id: uuid.UUID,
    user_id: uuid.UUID,
    metadata: dict[str, object] | None = None,
    clear_auth_link: bool = True,
    summary: str = (
        "Firebase deletion succeeded, but app account cleanup did not commit."
    ),
    detached_payment_method_ids: tuple[uuid.UUID, ...] = (),
) -> None:
    record_account_delete_partial_failure(
        db,
        user_id=user_id,
        created_by_user_id=admin_user_id,
        metadata=metadata
        or {"auth_identity_deleted": True, "app_cleanup_completed": False},
        clear_auth_link=clear_auth_link,
        title="Admin account deletion needs follow-up",
        summary=summary,
        detached_payment_method_ids=detached_payment_method_ids,
    )


def delete_admin_user(
    db: Session,
    *,
    admin_user: User,
    user_id: uuid.UUID,
    payload: AdminUserDeleteCreate,
    route_method: str = "POST",
    route_path: str = DELETE_USER_ROUTE_PATH,
) -> AdminUserDeleteResultRead:
    reason, idempotency_key = normalize_delete_request(payload)
    existing_action = get_existing_delete_action(
        db,
        admin_user_id=admin_user.id,
        user_id=user_id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        return build_delete_result(
            db,
            action=existing_action,
            expected_preview_snapshot_hash=payload.preview_token,
            expected_reason=reason,
        )

    target_user, active_admin_count = lock_delete_users(db, user_id=user_id)
    existing_action = get_existing_delete_action(
        db,
        admin_user_id=admin_user.id,
        user_id=user_id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        return build_delete_result(
            db,
            action=existing_action,
            expected_preview_snapshot_hash=payload.preview_token,
            expected_reason=reason,
        )

    now = datetime.now(timezone.utc)
    snapshot = build_delete_impact_snapshot(db, user_id=target_user.id, now=now)
    future_official_host_assignments = list_future_hosted_games(
        db,
        user_id=target_user.id,
        game_type="official",
        now=now,
    )
    future_community_hosted_games = list_future_hosted_games(
        db,
        user_id=target_user.id,
        game_type="community",
        now=now,
    )
    preview = build_admin_user_delete_impact_preview(
        user=target_user,
        active_admin_count=active_admin_count,
        snapshot=snapshot,
        future_official_host_assignments=future_official_host_assignments,
        future_community_hosted_games=future_community_hosted_games,
    )
    reason_codes = delete_preview_blocking_reason_codes(
        user=target_user,
        active_admin_count=active_admin_count,
        snapshot=snapshot,
    )
    guarded_reason_codes = [
        reason_code
        for reason_code in reason_codes
        if reason_code in {"last_active_admin", "future_official_host"}
    ]
    if target_user.account_status == "deleted" or target_user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=DELETE_PREVIEW_BLOCKING_MESSAGES["deleted"],
        )
    if target_user.account_status == "pending_deletion":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=DELETE_PREVIEW_BLOCKING_MESSAGES["pending_deletion"],
        )
    if guarded_reason_codes:
        reject_guarded_delete(
            db,
            admin_user=admin_user,
            target_user=target_user,
            reason_codes=guarded_reason_codes,
            preview=preview,
            route_method=route_method,
            route_path=route_path,
        )
    if payload.preview_token != preview.preview_token:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Delete preview is stale. Refresh the impact before continuing.",
        )

    auth_user_id = target_user.auth_user_id
    previous_account_status = target_user.account_status
    before_metadata = {
        "account_status": target_user.account_status,
        "hosting_status": target_user.hosting_status,
        "role": target_user.role,
        "had_auth_link": bool(target_user.auth_user_id),
    }
    target_user.account_status = "pending_deletion"
    target_user.updated_at = datetime.now(timezone.utc)
    db.add(target_user)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_user_conflict_detail(exc),
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Account deletion could not be staged. Please try again.",
        ) from exc

    if auth_user_id is not None:
        try:
            delete_firebase_user(auth_user_id)
        except FirebaseAdminConfigError as exc:
            target_user.account_status = previous_account_status
            target_user.updated_at = datetime.now(timezone.utc)
            db.add(target_user)
            try:
                db.commit()
            except SQLAlchemyError as restore_exc:
                db.rollback()
                record_admin_delete_partial_failure(
                    db,
                    admin_user_id=admin_user.id,
                    user_id=user_id,
                    clear_auth_link=False,
                    metadata={
                        "auth_identity_deleted": False,
                        "app_cleanup_completed": False,
                        "restore_failed": True,
                        "previous_account_status": previous_account_status,
                    },
                    summary=(
                        "Firebase deletion failed, and the staged app account "
                        "status could not be restored."
                    ),
                )
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=(
                        "Firebase deletion failed, and app account restoration "
                        "requires support follow-up."
                    ),
                ) from restore_exc
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            target_user.account_status = previous_account_status
            target_user.updated_at = datetime.now(timezone.utc)
            db.add(target_user)
            try:
                db.commit()
            except SQLAlchemyError as restore_exc:
                db.rollback()
                record_admin_delete_partial_failure(
                    db,
                    admin_user_id=admin_user.id,
                    user_id=user_id,
                    clear_auth_link=False,
                    metadata={
                        "auth_identity_deleted": False,
                        "app_cleanup_completed": False,
                        "restore_failed": True,
                        "previous_account_status": previous_account_status,
                    },
                    summary=(
                        "Firebase deletion failed, and the staged app account "
                        "status could not be restored."
                    ),
                )
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=(
                        "Firebase deletion failed, and app account restoration "
                        "requires support follow-up."
                    ),
                ) from restore_exc
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Firebase could not delete this account. Please try again.",
            ) from exc

        target_user.auth_user_id = None
        target_user.updated_at = datetime.now(timezone.utc)
        db.add(target_user)
        try:
            db.commit()
            db.refresh(target_user)
        except SQLAlchemyError as exc:
            db.rollback()
            record_admin_delete_partial_failure(
                db,
                admin_user_id=admin_user.id,
                user_id=user_id,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Firebase deletion succeeded, but app account cleanup "
                    "requires support follow-up."
                ),
            ) from exc

    now = datetime.now(timezone.utc)
    reviewed = {
        "preview_snapshot_hash": preview.preview_token,
        "future_official_host_assignment_count": (
            preview.future_official_host_assignment_count
        ),
        "future_community_hosted_game_count": (
            preview.future_community_hosted_game_count
        ),
        "active_future_booking_count": preview.active_future_booking_count,
        "active_future_official_booking_count": (
            preview.active_future_official_booking_count
        ),
        "active_future_participation_count": (
            preview.active_future_participation_count
        ),
        "active_future_guest_count": preview.active_future_guest_count,
        "active_waitlist_entry_count": preview.active_waitlist_entry_count,
        "active_owned_sub_post_count": preview.active_owned_sub_post_count,
        "active_sub_request_count": preview.active_sub_request_count,
        "payment_record_count": preview.payment_record_count,
        "refund_record_count": preview.refund_record_count,
        "game_credit_count": preview.game_credit_count,
        "saved_payment_method_count": preview.saved_payment_method_count,
        "active_saved_payment_method_count": (
            preview.active_saved_payment_method_count
        ),
        "active_support_flag_count": preview.active_support_flag_count,
    }
    payment_method_result = detach_account_saved_payment_methods(
        db,
        user_id=target_user.id,
    )
    if payment_method_result.has_blocking_failures:
        record_admin_delete_partial_failure(
            db,
            admin_user_id=admin_user.id,
            user_id=user_id,
            metadata=payment_method_result.support_metadata(
                auth_identity_deleted=auth_user_id is not None
            ),
            detached_payment_method_ids=(
                payment_method_result.detached_saved_payment_method_ids
            ),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Firebase deletion succeeded, but app account cleanup requires "
                "support follow-up."
            ),
        )

    try:
        db.commit()
        db.refresh(target_user)
    except SQLAlchemyError as exc:
        db.rollback()
        record_admin_delete_partial_failure(
            db,
            admin_user_id=admin_user.id,
            user_id=user_id,
            metadata={
                **payment_method_result.support_metadata(
                    auth_identity_deleted=auth_user_id is not None
                ),
                "failure_type": "saved_payment_method_checkpoint_commit_error",
            },
            detached_payment_method_ids=(
                payment_method_result.detached_saved_payment_method_ids
            ),
            summary=(
                "Firebase deletion succeeded, but saved-card cleanup state did "
                "not commit."
            ),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Firebase deletion succeeded, but app account cleanup requires "
                "support follow-up."
            ),
        ) from exc

    now = datetime.now(timezone.utc)
    try:
        cancel_future_user_activity(
            target_user,
            db,
            now,
            changed_by_user_id=admin_user.id,
        )
        audit_action = record_admin_action(
            db,
            admin_user_id=admin_user.id,
            action_type="delete_user",
            target_user_id=target_user.id,
            reason=reason,
            metadata={
                "before": before_metadata,
                "after": {
                    "account_status": "deleted",
                    "hosting_status": "not_eligible",
                    "deleted_at": now.isoformat(),
                    "auth_unlinked": True,
                },
                "reviewed": reviewed,
            },
            idempotency_key=idempotency_key,
            created_at=now,
        )
        anonymize_user(target_user, now)
        db.add(target_user)
    except Exception as exc:
        db.rollback()
        record_admin_delete_partial_failure(
            db,
            admin_user_id=admin_user.id,
            user_id=user_id,
            metadata={
                "auth_identity_deleted": auth_user_id is not None,
                "app_cleanup_completed": False,
                "failure_type": "app_cleanup_execution_error",
            },
            summary=(
                "Firebase deletion succeeded, but app account cleanup failed "
                "before the final commit."
            ),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Firebase deletion succeeded, but app account cleanup requires "
                "support follow-up."
            ),
        ) from exc

    try:
        db.commit()
        db.refresh(target_user)
        return AdminUserDeleteResultRead(
            user_id=target_user.id,
            account_status=target_user.account_status,
            deleted_at=now,
            admin_action_id=audit_action.id,
        )
    except SQLAlchemyError as exc:
        db.rollback()
        existing_action = get_existing_delete_action(
            db,
            admin_user_id=admin_user.id,
            user_id=user_id,
            idempotency_key=idempotency_key,
        )
        if existing_action is not None:
            return build_delete_result(
                db,
                action=existing_action,
                expected_preview_snapshot_hash=payload.preview_token,
                expected_reason=reason,
            )
        record_admin_delete_partial_failure(
            db,
            admin_user_id=admin_user.id,
            user_id=user_id,
            metadata={
                "auth_identity_deleted": auth_user_id is not None,
                "app_cleanup_completed": False,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Firebase deletion succeeded, but app account cleanup "
                "requires support follow-up."
            ),
        ) from exc
