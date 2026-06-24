"""Account-deletion workflows, cleanup, recovery, and anonymization."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.firebase_admin_client import FirebaseAdminConfigError, delete_firebase_user
from backend.models import (
    Booking,
    Game,
    GameParticipant,
    SubPost,
    SubPostRequest,
    User,
    UserPaymentMethod,
    UserSettings,
    WaitlistEntry,
)
from backend.schemas.auth_schema import AuthDeleteAccountRequest
from backend.services.auth_service import get_authenticated_user_from_token
from backend.services.game_rules import (
    ACTIVE_BOOKING_STATUSES,
    ACTIVE_JOIN_STATUSES,
    OPEN_GAME_STATUSES,
)
from backend.services.need_a_sub_rules import (
    ACTIVE_REQUEST_STATUSES,
    ACTIVE_VISIBLE_POST_STATUSES,
)
from backend.services.status_history_service import (
    add_booking_status_history_if_changed,
    add_participant_status_history_if_changed,
)
from backend.services.stripe_service import StripeConfigError, detach_payment_method
from backend.services.user_service import build_user_conflict_detail

ACCOUNT_DELETION_REASON = "Account deleted."
ACTIVE_SAVED_PAYMENT_METHOD_STATUS = "active"
DELETE_WAITLIST_STATUSES = {"active", "promoted", "payment_processing", "accepted"}


@dataclass(frozen=True)
class SavedPaymentMethodCleanupFailure:
    payment_method_id: uuid.UUID
    method_status: str
    error_type: str


@dataclass(frozen=True)
class AccountDeletionCleanupResult:
    saved_payment_method_failures: tuple[SavedPaymentMethodCleanupFailure, ...] = ()
    detached_saved_payment_method_ids: tuple[uuid.UUID, ...] = ()

    @property
    def has_blocking_failures(self) -> bool:
        return bool(self.saved_payment_method_failures)

    def support_metadata(self, *, auth_identity_deleted: bool) -> dict[str, object]:
        return {
            "auth_identity_deleted": auth_identity_deleted,
            "app_cleanup_completed": False,
            "saved_payment_method_cleanup_failed": bool(
                self.saved_payment_method_failures
            ),
            "saved_payment_method_failure_count": len(
                self.saved_payment_method_failures
            ),
            "failed_saved_payment_method_ids": [
                str(failure.payment_method_id)
                for failure in self.saved_payment_method_failures
            ],
            "detached_saved_payment_method_ids": [
                str(payment_method_id)
                for payment_method_id in self.detached_saved_payment_method_ids
            ],
            "failure_types": sorted(
                {failure.error_type for failure in self.saved_payment_method_failures}
            ),
        }


def lock_user_and_active_admins_for_account_removal(
    db: Session,
    *,
    user_id: uuid.UUID,
) -> tuple[User, int]:
    users = list(
        db.scalars(
            select(User)
            .where(
                or_(
                    User.id == user_id,
                    (
                        (User.role == "admin")
                        & (User.account_status == "active")
                        & User.deleted_at.is_(None)
                    ),
                )
            )
            .order_by(User.id.asc())
            .with_for_update()
        ).all()
    )
    target_user = next((user for user in users if user.id == user_id), None)
    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    active_admin_count = sum(
        1
        for user in users
        if (
            user.role == "admin"
            and user.account_status == "active"
            and user.deleted_at is None
        )
    )
    return target_user, active_admin_count


def require_account_removal_preserves_active_admin(
    user: User,
    *,
    active_admin_count: int,
) -> None:
    if (
        user.role == "admin"
        and user.account_status == "active"
        and user.deleted_at is None
        and active_admin_count <= 1
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The last active admin cannot be deleted.",
        )


def record_account_delete_partial_failure(
    db: Session,
    *,
    user_id: uuid.UUID,
    created_by_user_id: uuid.UUID | None,
    metadata: dict[str, object] | None = None,
    clear_auth_link: bool = True,
    title: str = "Account deletion needs follow-up",
    summary: str = "Account deletion cleanup did not finish.",
    detached_payment_method_ids: tuple[uuid.UUID, ...] = (),
) -> None:
    from backend.services.support_flag_service import stage_support_flag

    user = db.get(User, user_id)
    if user is None:
        return

    now = datetime.now(timezone.utc)
    user.account_status = "pending_deletion"
    if clear_auth_link:
        user.auth_user_id = None
    user.updated_at = now
    db.add(user)
    if detached_payment_method_ids:
        payment_methods = db.scalars(
            select(UserPaymentMethod).where(
                UserPaymentMethod.user_id == user.id,
                UserPaymentMethod.id.in_(detached_payment_method_ids),
            )
        ).all()
        for payment_method in payment_methods:
            payment_method.method_status = "detached"
            payment_method.is_default = False
            payment_method.detached_at = payment_method.detached_at or now
            payment_method.updated_at = now
            db.add(payment_method)

    stage_support_flag(
        db,
        flag_type="account_delete_partial_failure",
        source="account",
        severity="critical",
        title=title,
        summary=summary,
        metadata=metadata
        or {
            "auth_identity_deleted": True,
            "app_cleanup_completed": False,
        },
        idempotency_key=f"account-delete-partial:{user.id}",
        created_by_user_id=created_by_user_id,
        target_user_id=user.id,
        reopen_resolved=True,
    )

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Account deletion recovery state could not be recorded.",
        ) from exc


def detach_account_saved_payment_methods(
    db: Session,
    *,
    user_id: uuid.UUID,
) -> AccountDeletionCleanupResult:
    payment_methods = list(
        db.scalars(
            select(UserPaymentMethod)
            .where(UserPaymentMethod.user_id == user_id)
            .order_by(UserPaymentMethod.created_at.asc(), UserPaymentMethod.id.asc())
            .with_for_update()
        ).all()
    )
    failures: list[SavedPaymentMethodCleanupFailure] = []
    detached_payment_method_ids: list[uuid.UUID] = []
    now = datetime.now(timezone.utc)

    for payment_method in payment_methods:
        if payment_method.method_status != ACTIVE_SAVED_PAYMENT_METHOD_STATUS:
            continue

        try:
            detach_payment_method(payment_method.stripe_payment_method_id)
            payment_method.method_status = "detached"
            payment_method.is_default = False
            payment_method.detached_at = payment_method.detached_at or now
            payment_method.updated_at = now
            db.add(payment_method)
            detached_payment_method_ids.append(payment_method.id)
        except StripeConfigError:
            failures.append(
                SavedPaymentMethodCleanupFailure(
                    payment_method_id=payment_method.id,
                    method_status=payment_method.method_status,
                    error_type="stripe_config_error",
                )
            )
        except Exception:
            failures.append(
                SavedPaymentMethodCleanupFailure(
                    payment_method_id=payment_method.id,
                    method_status=payment_method.method_status,
                    error_type="stripe_detach_error",
                )
            )

    return AccountDeletionCleanupResult(
        saved_payment_method_failures=tuple(failures),
        detached_saved_payment_method_ids=tuple(detached_payment_method_ids),
    )


def remove_account_saved_payment_method_rows(
    db: Session,
    *,
    user_id: uuid.UUID,
) -> None:
    payment_methods = db.scalars(
        select(UserPaymentMethod)
        .where(UserPaymentMethod.user_id == user_id)
        .with_for_update()
    ).all()
    for payment_method in payment_methods:
        db.delete(payment_method)


def mark_assigned_host_notifications_read(
    db: Session,
    *,
    user_id: uuid.UUID,
    game_id: uuid.UUID,
    now: datetime,
) -> None:
    from backend.models import Notification

    notifications = db.scalars(
        select(Notification).where(
            Notification.user_id == user_id,
            Notification.related_game_id == game_id,
            Notification.notification_type == "game_host_assigned",
            Notification.is_read.is_(False),
        )
    ).all()
    for notification in notifications:
        notification.is_read = True
        notification.read_at = notification.read_at or now
        notification.updated_at = now
        db.add(notification)


def clear_future_official_host_assignments(
    db: Session,
    *,
    user_id: uuid.UUID,
    now: datetime,
) -> None:
    games = db.scalars(
        select(Game)
        .where(
            Game.host_user_id == user_id,
            Game.game_type == "official",
            Game.starts_at > now,
            Game.game_status.in_(OPEN_GAME_STATUSES),
            Game.deleted_at.is_(None),
        )
        .with_for_update()
    ).all()

    for game in games:
        mark_assigned_host_notifications_read(
            db,
            user_id=user_id,
            game_id=game.id,
            now=now,
        )
        game.host_user_id = None
        game.updated_at = now
        db.add(game)


def active_future_buyer_bookings_for_user_deletion(
    db: Session,
    *,
    user_id: uuid.UUID,
    now: datetime,
) -> list[Booking]:
    return list(
        db.scalars(
            select(Booking)
            .join(Game, Booking.game_id == Game.id)
            .where(
                Booking.buyer_user_id == user_id,
                Booking.booking_status.in_(ACTIVE_BOOKING_STATUSES),
                Game.starts_at > now,
                Game.game_status.in_(OPEN_GAME_STATUSES),
                Game.deleted_at.is_(None),
            )
            .with_for_update()
        ).all()
    )


def active_booking_participants_for_user_deletion(
    db: Session,
    *,
    user_id: uuid.UUID,
    now: datetime,
    booking_keys: set[tuple[uuid.UUID, uuid.UUID]],
) -> list[GameParticipant]:
    participants = list(
        db.scalars(
            select(GameParticipant)
            .join(Game, GameParticipant.game_id == Game.id)
            .where(
                or_(
                    GameParticipant.user_id == user_id,
                    GameParticipant.guest_of_user_id == user_id,
                ),
                Game.starts_at > now,
                Game.game_status.in_(OPEN_GAME_STATUSES),
                Game.deleted_at.is_(None),
                GameParticipant.participant_status.in_(ACTIVE_JOIN_STATUSES),
            )
            .with_for_update()
        ).all()
    )
    participants_by_id = {participant.id: participant for participant in participants}

    booking_keys.update(
        (participant.game_id, participant.booking_id)
        for participant in participants
        if participant.booking_id is not None
    )
    for game_id, booking_id in booking_keys:
        booking_participants = db.scalars(
            select(GameParticipant)
            .where(
                GameParticipant.game_id == game_id,
                GameParticipant.booking_id == booking_id,
                GameParticipant.participant_status.in_(ACTIVE_JOIN_STATUSES),
            )
            .with_for_update()
        ).all()
        for participant in booking_participants:
            participants_by_id[participant.id] = participant

    return list(participants_by_id.values())


def cancel_participant_for_account_deletion(
    db: Session,
    *,
    participant: GameParticipant,
    deleted_user_id: uuid.UUID,
    changed_by_user_id: uuid.UUID | None,
    now: datetime,
) -> None:
    old_participant_status = participant.participant_status
    old_attendance_status = participant.attendance_status

    participant.participant_status = "cancelled"
    participant.cancellation_type = "on_time"
    participant.attendance_status = "not_applicable"
    participant.cancelled_at = participant.cancelled_at or now
    participant.updated_at = now

    if participant.user_id == deleted_user_id:
        participant.display_name_snapshot = "Deleted User"
    if participant.guest_of_user_id == deleted_user_id:
        participant.guest_name = "Deleted Guest"
        participant.guest_email = None
        participant.guest_phone = None
        participant.display_name_snapshot = "Deleted Guest"

    db.add(participant)
    add_participant_status_history_if_changed(
        db,
        participant,
        old_participant_status=old_participant_status,
        old_attendance_status=old_attendance_status,
        reason=ACCOUNT_DELETION_REASON,
        changed_by_user_id=changed_by_user_id,
        change_source="system",
    )


def reconcile_booking_after_account_deletion(
    db: Session,
    *,
    booking_id: uuid.UUID,
    game_id: uuid.UUID,
    deleted_user_id: uuid.UUID,
    changed_by_user_id: uuid.UUID | None,
    now: datetime,
) -> None:
    booking = db.scalar(
        select(Booking).where(Booking.id == booking_id).with_for_update()
    )
    if booking is None:
        return

    old_booking_status = booking.booking_status
    old_payment_status = booking.payment_status
    remaining_participants = list(
        db.scalars(
            select(GameParticipant).where(
                GameParticipant.game_id == game_id,
                GameParticipant.booking_id == booking.id,
                GameParticipant.participant_status.in_(ACTIVE_JOIN_STATUSES),
            )
        ).all()
    )

    if remaining_participants:
        booking.booking_status = "partially_cancelled"
        booking.participant_count = len(remaining_participants)
        booking.subtotal_cents = (
            booking.price_per_player_snapshot_cents * len(remaining_participants)
        )
        booking.discount_cents = min(booking.discount_cents, booking.subtotal_cents)
        booking.total_cents = (
            booking.subtotal_cents
            + booking.platform_fee_cents
            - booking.discount_cents
        )
    else:
        booking.booking_status = "cancelled"

    booking.cancelled_at = booking.cancelled_at or now
    booking.cancelled_by_user_id = (
        deleted_user_id if changed_by_user_id is None else changed_by_user_id
    )
    booking.cancel_reason = ACCOUNT_DELETION_REASON
    booking.updated_at = now
    db.add(booking)
    add_booking_status_history_if_changed(
        db,
        booking,
        old_booking_status=old_booking_status,
        old_payment_status=old_payment_status,
        reason=ACCOUNT_DELETION_REASON,
        changed_by_user_id=changed_by_user_id,
        change_source="system",
    )


def cancel_future_roster_activity(
    db: Session,
    *,
    user_id: uuid.UUID,
    changed_by_user_id: uuid.UUID | None,
    now: datetime,
) -> None:
    from backend.services.game_service import sync_game_capacity_status
    from backend.services.game_waitlist_service import promote_waitlist_entries

    buyer_bookings = active_future_buyer_bookings_for_user_deletion(
        db,
        user_id=user_id,
        now=now,
    )
    booking_keys = {
        (booking.game_id, booking.id)
        for booking in buyer_bookings
    }
    participants = active_booking_participants_for_user_deletion(
        db,
        user_id=user_id,
        now=now,
        booking_keys=booking_keys,
    )
    affected_game_ids = {
        *(participant.game_id for participant in participants),
        *(booking.game_id for booking in buyer_bookings),
    }

    for participant in participants:
        cancel_participant_for_account_deletion(
            db,
            participant=participant,
            deleted_user_id=user_id,
            changed_by_user_id=changed_by_user_id,
            now=now,
        )

    db.flush()
    for game_id, booking_id in booking_keys:
        reconcile_booking_after_account_deletion(
            db,
            booking_id=booking_id,
            game_id=game_id,
            deleted_user_id=user_id,
            changed_by_user_id=changed_by_user_id,
            now=now,
        )

    db.flush()
    for game_id in affected_game_ids:
        game = db.get(Game, game_id)
        if (
            game is not None
            and game.deleted_at is None
            and game.starts_at > now
            and game.game_status in OPEN_GAME_STATUSES
        ):
            promote_waitlist_entries(db, game, now)
            sync_game_capacity_status(db, game)
            game.updated_at = now
            db.add(game)


def anonymize_participant_snapshots(
    db: Session,
    *,
    user_id: uuid.UUID,
    now: datetime,
) -> None:
    participants = db.scalars(
        select(GameParticipant).where(
            or_(
                GameParticipant.user_id == user_id,
                GameParticipant.guest_of_user_id == user_id,
            )
        )
    ).all()

    for participant in participants:
        if participant.user_id == user_id:
            participant.display_name_snapshot = "Deleted User"
        if participant.guest_of_user_id == user_id:
            participant.guest_name = "Deleted Guest"
            participant.guest_email = None
            participant.guest_phone = None
            participant.display_name_snapshot = "Deleted Guest"
        participant.updated_at = now
        db.add(participant)


def cancel_waitlist_entries(
    db: Session,
    *,
    user_id: uuid.UUID,
    now: datetime,
) -> None:
    waitlist_entries = db.scalars(
        select(WaitlistEntry)
        .where(
            WaitlistEntry.user_id == user_id,
            WaitlistEntry.waitlist_status.in_(DELETE_WAITLIST_STATUSES),
        )
        .with_for_update()
    ).all()

    for waitlist_entry in waitlist_entries:
        waitlist_entry.waitlist_status = "cancelled"
        waitlist_entry.cancelled_at = waitlist_entry.cancelled_at or now
        waitlist_entry.updated_at = now
        db.add(waitlist_entry)


def cancel_future_community_hosted_games(
    db: Session,
    *,
    user: User,
    now: datetime,
) -> None:
    from backend.services.game_cancellation_service import (
        archive_game_chats,
        cancel_game_bookings,
        cancel_game_participants,
        cancel_game_waitlist_entries,
        create_game_cancelled_notifications,
        create_game_cancellation_history,
    )

    games = db.scalars(
        select(Game)
        .where(
            Game.host_user_id == user.id,
            Game.game_type == "community",
            Game.starts_at > now,
            Game.game_status.in_(OPEN_GAME_STATUSES),
            Game.deleted_at.is_(None),
        )
        .with_for_update()
    ).all()

    for game in games:
        old_game_status = game.game_status
        notified_user_ids = cancel_game_participants(
            db,
            game,
            now,
            "host_cancelled",
        )
        cancel_game_waitlist_entries(db, game, now)
        cancel_game_bookings(db, game, user, now, "host_cancelled")
        archive_game_chats(db, game, now)
        create_game_cancelled_notifications(
            db,
            game,
            notified_user_ids,
            now,
            actor_user_id=user.id,
        )
        create_game_cancellation_history(
            db,
            game,
            user,
            old_game_status,
            "Host account deleted.",
            "system",
            now,
        )
        game.game_status = "cancelled"
        game.cancelled_at = game.cancelled_at or now
        game.cancelled_by_user_id = user.id
        game.cancel_reason = "Host account deleted."
        game.completed_at = None
        game.completed_by_user_id = None
        game.updated_at = now
        db.add(game)


def cancel_owned_need_a_sub_posts(
    db: Session,
    *,
    user_id: uuid.UUID,
    changed_by_user_id: uuid.UUID | None,
    now: datetime,
) -> None:
    from backend.services.need_a_sub_lifecycle_service import (
        add_post_status_history,
        change_request_status,
    )
    from backend.services.need_a_sub_notification_service import (
        notify_requester_sub_status,
        resolve_owner_request_activity_notification,
    )
    from backend.services.sub_post_chat_service import (
        resolve_sub_chat_notifications_for_post,
    )

    posts = db.scalars(
        select(SubPost)
        .where(
            SubPost.owner_user_id == user_id,
            SubPost.post_status.in_(ACTIVE_VISIBLE_POST_STATUSES),
        )
        .with_for_update()
    ).all()

    for sub_post in posts:
        old_status = sub_post.post_status
        sub_post.post_status = "canceled"
        sub_post.canceled_at = sub_post.canceled_at or now
        sub_post.canceled_by_user_id = user_id
        sub_post.cancel_reason = "Owner account deleted."
        sub_post.updated_at = now
        db.add(sub_post)
        add_post_status_history(
            db,
            sub_post,
            old_status,
            "canceled",
            changed_by_user_id,
            "system",
            "Owner account deleted.",
        )
        resolve_sub_chat_notifications_for_post(
            db,
            sub_post_id=sub_post.id,
            read_at=now,
        )

        active_requests = db.scalars(
            select(SubPostRequest)
            .where(
                SubPostRequest.sub_post_id == sub_post.id,
                SubPostRequest.request_status.in_(ACTIVE_REQUEST_STATUSES),
            )
            .with_for_update()
        ).all()
        for sub_request in active_requests:
            previous_status = sub_request.request_status
            change_request_status(
                db,
                sub_request,
                "canceled_by_owner",
                changed_by_user_id,
                "system",
                "Owner account deleted.",
                now,
            )
            if previous_status == "pending":
                resolve_owner_request_activity_notification(
                    db,
                    sub_post=sub_post,
                    sub_request=sub_request,
                    read_at=now,
                )
            notify_requester_sub_status(
                db,
                sub_post=sub_post,
                sub_request=sub_request,
                notification_type="sub_post_canceled",
                title=None,
                body=None,
                actor_user_id=user_id,
                event_at=now,
            )


def cancel_need_a_sub_requests_made(
    db: Session,
    *,
    user_id: uuid.UUID,
    changed_by_user_id: uuid.UUID | None,
    now: datetime,
) -> None:
    from backend.services.need_a_sub_lifecycle_service import (
        change_request_status,
        recalculate_filled_status,
    )
    from backend.services.need_a_sub_notification_service import (
        add_need_a_sub_notification,
        notify_waitlist_promoted,
        resolve_owner_request_activity_notification,
    )
    from backend.services.need_a_sub_request_service import promote_next_waitlisted_request
    from backend.services.sub_post_chat_service import (
        resolve_sub_chat_notifications_for_user,
    )

    sub_requests = db.scalars(
        select(SubPostRequest)
        .where(
            SubPostRequest.requester_user_id == user_id,
            SubPostRequest.request_status.in_(ACTIVE_REQUEST_STATUSES),
        )
        .with_for_update()
    ).all()

    for sub_request in sub_requests:
        previous_status = sub_request.request_status
        position_id = sub_request.sub_post_position_id
        sub_post = db.scalar(
            select(SubPost)
            .where(SubPost.id == sub_request.sub_post_id)
            .with_for_update()
        )
        change_request_status(
            db,
            sub_request,
            "canceled_by_player",
            changed_by_user_id,
            "system",
            "Requester account deleted.",
            now,
        )

        if previous_status == "pending" and sub_post is not None:
            resolve_owner_request_activity_notification(
                db,
                sub_post=sub_post,
                sub_request=sub_request,
                resolution="canceled",
                read_at=now,
            )
        elif previous_status == "confirmed" and sub_post is not None:
            add_need_a_sub_notification(
                db,
                recipient_user_id=sub_post.owner_user_id,
                notification_type="sub_request_canceled_by_player",
                sub_post=sub_post,
                sub_request=sub_request,
                actor_user_id=user_id,
                event_at=now,
            )
            resolve_sub_chat_notifications_for_user(
                db,
                sub_post_id=sub_post.id,
                user_id=user_id,
                read_at=now,
            )
            recalculate_filled_status(db, sub_post, changed_by_user_id, "system")

        if previous_status in {"pending", "confirmed"}:
            promoted_request = promote_next_waitlisted_request(
                db,
                position_id,
                changed_by_user_id,
                "system",
            )
            if sub_post is not None:
                notify_waitlist_promoted(
                    db,
                    sub_post,
                    promoted_request,
                    user_id,
                )


def cleanup_need_a_sub_activity(
    db: Session,
    *,
    user_id: uuid.UUID,
    changed_by_user_id: uuid.UUID | None,
    now: datetime,
) -> None:
    cancel_owned_need_a_sub_posts(
        db,
        user_id=user_id,
        changed_by_user_id=changed_by_user_id,
        now=now,
    )
    cancel_need_a_sub_requests_made(
        db,
        user_id=user_id,
        changed_by_user_id=changed_by_user_id,
        now=now,
    )


def reset_user_settings_for_deletion(
    db: Session,
    *,
    user_id: uuid.UUID,
    now: datetime,
) -> None:
    settings = db.get(UserSettings, user_id)

    if settings is None:
        return

    settings.push_notifications_enabled = False
    settings.email_notifications_enabled = False
    settings.sms_notifications_enabled = False
    settings.marketing_opt_in = False
    settings.location_permission_status = "unknown"
    settings.selected_city = None
    settings.selected_state = None
    settings.updated_at = now
    db.add(settings)


def cancel_future_user_activity(
    user: User,
    db: Session,
    now: datetime,
    *,
    changed_by_user_id: uuid.UUID | None = None,
) -> AccountDeletionCleanupResult:
    clear_future_official_host_assignments(db, user_id=user.id, now=now)
    cancel_future_community_hosted_games(db, user=user, now=now)
    cancel_future_roster_activity(
        db,
        user_id=user.id,
        changed_by_user_id=changed_by_user_id,
        now=now,
    )
    anonymize_participant_snapshots(db, user_id=user.id, now=now)
    cancel_waitlist_entries(db, user_id=user.id, now=now)
    cleanup_need_a_sub_activity(
        db,
        user_id=user.id,
        changed_by_user_id=changed_by_user_id,
        now=now,
    )
    reset_user_settings_for_deletion(db, user_id=user.id, now=now)
    remove_account_saved_payment_method_rows(db, user_id=user.id)
    return AccountDeletionCleanupResult()


def anonymize_user(user: User, now: datetime) -> None:
    user.auth_user_id = None
    user.email = None
    user.phone = None
    user.first_name = "Deleted"
    user.last_name = "User"
    user.date_of_birth = None
    user.profile_photo_url = None
    user.home_city = None
    user.home_state = None
    user.account_status = "deleted"
    user.hosting_status = "not_eligible"
    user.hosting_suspended_until = None
    user.stripe_customer_id = None
    user.deleted_at = now
    user.updated_at = now


def restore_self_delete_staged_account_after_firebase_failure(
    db: Session,
    *,
    user: User,
    previous_account_status: str,
    response_status_code: int,
    response_detail: str,
) -> None:
    user.account_status = previous_account_status
    user.updated_at = datetime.now(timezone.utc)
    db.add(user)
    try:
        db.commit()
    except SQLAlchemyError as restore_exc:
        db.rollback()
        record_account_delete_partial_failure(
            db,
            user_id=user.id,
            created_by_user_id=user.id,
            clear_auth_link=False,
            metadata={
                "auth_identity_deleted": False,
                "app_cleanup_completed": False,
                "restore_failed": True,
                "previous_account_status": previous_account_status,
            },
            summary=(
                "Firebase deletion failed, and the staged app account status "
                "could not be restored."
            ),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Firebase deletion failed, and app account restoration requires "
                "support follow-up."
            ),
        ) from restore_exc

    raise HTTPException(
        status_code=response_status_code,
        detail=response_detail,
    )


def delete_account_workflow(
    payload: AuthDeleteAccountRequest,
    authorization: str | None,
    db: Session,
) -> User:
    if payload.confirmation.strip().upper() != "DELETE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Type "delete" to confirm account deletion.',
        )

    authenticated_user = get_authenticated_user_from_token(authorization, db)
    user, active_admin_count = lock_user_and_active_admins_for_account_removal(
        db,
        user_id=authenticated_user.id,
    )
    require_account_removal_preserves_active_admin(
        user,
        active_admin_count=active_admin_count,
    )
    now = datetime.now(timezone.utc)
    auth_user_id = user.auth_user_id
    previous_account_status = user.account_status

    if not auth_user_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This account cannot be deleted because it is already unlinked.",
        )

    user.account_status = "pending_deletion"
    user.updated_at = now
    db.add(user)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_user_conflict_detail(exc),
        ) from exc

    try:
        delete_firebase_user(auth_user_id)
    except FirebaseAdminConfigError as exc:
        restore_self_delete_staged_account_after_firebase_failure(
            db,
            user=user,
            previous_account_status=previous_account_status,
            response_status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            response_detail=str(exc),
        )
    except Exception as exc:
        restore_self_delete_staged_account_after_firebase_failure(
            db,
            user=user,
            previous_account_status=previous_account_status,
            response_status_code=status.HTTP_502_BAD_GATEWAY,
            response_detail="Firebase could not delete this account. Please try again.",
        )

    checkpoint_at = datetime.now(timezone.utc)
    user.auth_user_id = None
    user.updated_at = checkpoint_at
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except SQLAlchemyError as exc:
        db.rollback()
        record_account_delete_partial_failure(
            db,
            user_id=user.id,
            created_by_user_id=user.id,
            metadata={
                "auth_identity_deleted": True,
                "app_cleanup_completed": False,
                "failure_type": "auth_unlink_checkpoint_commit_error",
            },
            summary=(
                "Firebase deletion succeeded, but the app auth unlink did not "
                "commit."
            ),
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Firebase deletion succeeded, but app account cleanup requires "
                "support follow-up."
            ),
        ) from exc

    payment_method_result = detach_account_saved_payment_methods(
        db,
        user_id=user.id,
    )
    if payment_method_result.has_blocking_failures:
        record_account_delete_partial_failure(
            db,
            user_id=user.id,
            created_by_user_id=user.id,
            metadata=payment_method_result.support_metadata(
                auth_identity_deleted=True
            ),
            detached_payment_method_ids=(
                payment_method_result.detached_saved_payment_method_ids
            ),
            summary=(
                "Firebase deletion succeeded, but app account cleanup requires "
                "support follow-up."
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
        db.refresh(user)
    except SQLAlchemyError as exc:
        db.rollback()
        record_account_delete_partial_failure(
            db,
            user_id=user.id,
            created_by_user_id=user.id,
            metadata={
                **payment_method_result.support_metadata(
                    auth_identity_deleted=True
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
            user,
            db,
            now,
            changed_by_user_id=user.id,
        )
        anonymize_user(user, now)
        db.add(user)
    except Exception as exc:
        db.rollback()
        record_account_delete_partial_failure(
            db,
            user_id=user.id,
            created_by_user_id=user.id,
            metadata={
                "auth_identity_deleted": True,
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
    except SQLAlchemyError as exc:
        db.rollback()
        record_account_delete_partial_failure(
            db,
            user_id=user.id,
            created_by_user_id=user.id,
            metadata={
                "auth_identity_deleted": True,
                "app_cleanup_completed": False,
                "failure_type": "app_cleanup_commit_error",
            },
            summary=(
                "Firebase deletion succeeded, but final app account cleanup did "
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

    return user
