"""Game cancellation helper queries and readiness checks."""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    Booking,
    Game,
    GameChat,
    GameParticipant,
    GameStatusHistory,
    Notification,
    Payment,
    Refund,
    User,
    WaitlistEntry,
)
from backend.schemas import GameCancelCreate
from backend.services.admin_action_service import record_admin_action
from backend.services.admin_permission_service import (
    PERMISSION_COMMUNITY_GAMES_CANCEL,
    PERMISSION_OFFICIAL_GAMES_CANCEL,
    user_has_admin_permission,
)
from backend.services.game_service import (
    ACTIVE_BOOKING_STATUSES,
    ACTIVE_JOIN_STATUSES,
    ACTIVE_WAITLIST_STATUSES,
    CANCELLABLE_GAME_STATUSES,
    CANCELLATION_AUTO_REFUND_PAYMENT_STATUSES,
    CANCELLATION_REFUND_FOLLOWUP_BOOKING_PAYMENT_STATUSES,
    CANCELLATION_REFUND_FOLLOWUP_PAYMENT_STATUSES,
    CANCELLATION_UNCHARGED_PENDING_PAYMENT_STATUSES,
    MAX_CANCEL_REASON_LENGTH,
    build_game_conflict_detail,
    create_or_reopen_booking_refunded_notification,
    game_requires_app_player_payment,
    require_game_not_started,
)
from backend.services.game_credit_service import (
    release_reserved_game_credits,
    restore_redeemed_game_credits,
)
from backend.services.notification_service import (
    build_game_notification_fields,
    resolve_aggregated_notification,
)
from backend.services.stripe_service import (
    StripeConfigError,
    create_refund as create_stripe_refund,
)


def normalize_cancel_reason(cancel_reason: str | None) -> str | None:
    if cancel_reason is None:
        return None

    normalized_reason = " ".join(cancel_reason.strip().split())
    if not normalized_reason:
        return None

    if len(normalized_reason) > MAX_CANCEL_REASON_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"cancel_reason must be {MAX_CANCEL_REASON_LENGTH} characters or fewer.",
        )

    return normalized_reason


def require_cancel_permission(db_game: Game, current_user: User) -> str:
    if current_user.account_status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account cannot cancel games right now.",
        )

    if db_game.game_type == "community":
        if user_has_admin_permission(current_user, PERMISSION_COMMUNITY_GAMES_CANCEL):
            return "admin_cancelled"

        if db_game.host_user_id == current_user.id:
            return "host_cancelled"

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the community game host or an admin can cancel this game.",
        )

    if db_game.game_type == "official":
        if user_has_admin_permission(current_user, PERMISSION_OFFICIAL_GAMES_CANCEL):
            return "admin_cancelled"

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an admin can cancel official games.",
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="This game type cannot be cancelled.",
    )


def list_cancellable_game_participants(
    db: Session,
    db_game: Game,
) -> list[GameParticipant]:
    return list(
        db.scalars(
            select(GameParticipant).where(
                GameParticipant.game_id == db_game.id,
                GameParticipant.participant_status.in_(ACTIVE_JOIN_STATUSES),
            )
        ).all()
    )


def get_game_cancellation_participant_notification_user_id(
    db_game: Game,
    participant: GameParticipant,
) -> uuid.UUID | None:
    should_notify = (
        participant.user_id is not None
        and participant.user_id != db_game.host_user_id
        and participant.participant_type in {"registered_user", "admin_added"}
        and participant.participant_status in {"confirmed", "waitlisted"}
    )
    return participant.user_id if should_notify else None


def add_game_cancellation_host_recipient(
    db_game: Game,
    notified_user_ids: list[uuid.UUID],
    actor_user_id: uuid.UUID,
) -> list[uuid.UUID]:
    if db_game.host_user_id is None or db_game.host_user_id == actor_user_id:
        return notified_user_ids

    return [*notified_user_ids, db_game.host_user_id]


def list_cancellable_waitlist_entries(
    db: Session,
    db_game: Game,
) -> list[WaitlistEntry]:
    return list(
        db.scalars(
            select(WaitlistEntry).where(
                WaitlistEntry.game_id == db_game.id,
                WaitlistEntry.waitlist_status.in_(ACTIVE_WAITLIST_STATUSES),
            )
        ).all()
    )


def list_cancellable_bookings(db: Session, db_game: Game) -> list[Booking]:
    return list(
        db.scalars(
            select(Booking)
            .where(
                Booking.game_id == db_game.id,
                Booking.booking_status.in_(ACTIVE_BOOKING_STATUSES),
            )
            .order_by(Booking.created_at.asc(), Booking.id.asc())
        ).all()
    )


def list_booking_payments(db: Session, booking: Booking) -> list[Payment]:
    return list(
        db.scalars(
            select(Payment).where(
                Payment.booking_id == booking.id,
                Payment.payment_type == "booking",
            )
        ).all()
    )


def map_stripe_refund_status(stripe_status: str) -> str:
    normalized_status = stripe_status.strip().lower()
    if normalized_status == "succeeded":
        return "succeeded"

    if normalized_status == "failed":
        return "failed"

    if normalized_status in {"canceled", "cancelled"}:
        return "cancelled"

    return "processing"


def all_booking_refundable_payments_refunded(payments: list[Payment]) -> bool:
    refundable_payments = [
        payment
        for payment in payments
        if payment.payment_status
        in CANCELLATION_REFUND_FOLLOWUP_PAYMENT_STATUSES
    ]
    return bool(refundable_payments) and all(
        payment.payment_status == "refunded" for payment in refundable_payments
    )


def booking_has_refundable_payments(payments: list[Payment]) -> bool:
    return any(
        payment.payment_status in CANCELLATION_REFUND_FOLLOWUP_PAYMENT_STATUSES
        for payment in payments
    )


def build_cancellation_payment_summary() -> dict[str, object]:
    return {
        "cancelled_booking_count": 0,
        "paid_booking_count": 0,
        "processing_payment_booking_count": 0,
        "uncharged_pending_booking_count": 0,
        "refund_followup_required": False,
        "payment_followup_required": False,
        "payment_refund_created": False,
        "refund_created_count": 0,
        "refund_failed_count": 0,
        "refund_processing_count": 0,
        "refund_missing_charge_count": 0,
        "credit_restored_count": 0,
        "credit_restored_cents": 0,
        "credit_released_count": 0,
        "credit_released_cents": 0,
    }


def build_cancellation_refund_summary() -> dict[str, object]:
    return {
        "refund_created_count": 0,
        "refund_failed_count": 0,
        "refund_processing_count": 0,
        "refund_missing_charge_count": 0,
        "successful_refunds": [],
    }


def cancel_game_bookings(
    db: Session,
    db_game: Game,
    current_user: User,
    now: datetime,
    cancellation_type: str,
) -> dict[str, object]:
    bookings = list_cancellable_bookings(db, db_game)
    app_payment_required = game_requires_app_player_payment(db_game)
    payment_summary = build_cancellation_payment_summary()

    for booking in bookings:
        payments = list_booking_payments(db, booking)

        if app_payment_required:
            payment_statuses = {payment.payment_status for payment in payments}
            has_paid_payment = bool(
                payment_statuses
                & CANCELLATION_REFUND_FOLLOWUP_PAYMENT_STATUSES
            ) or (
                booking.payment_status
                in CANCELLATION_REFUND_FOLLOWUP_BOOKING_PAYMENT_STATUSES
            )
            has_processing_payment = "processing" in payment_statuses

            if has_paid_payment:
                payment_summary["paid_booking_count"] = (
                    int(payment_summary["paid_booking_count"]) + 1
                )
                restored_credit_usages = restore_redeemed_game_credits(
                    db,
                    booking.id,
                    now=now,
                    restore_reason="game_cancelled",
                    user_id=booking.buyer_user_id,
                )
                restored_credit_cents = sum(
                    usage.amount_cents for usage in restored_credit_usages
                )
                credit_restored = restored_credit_cents > 0
                payment_summary["credit_restored_count"] = (
                    int(payment_summary["credit_restored_count"])
                    + len(restored_credit_usages)
                )
                payment_summary["credit_restored_cents"] = (
                    int(payment_summary["credit_restored_cents"])
                    + restored_credit_cents
                )
                refund_summary = create_official_cancellation_refunds(
                    db,
                    db_game,
                    booking,
                    payments,
                    current_user,
                    now,
                )
                successful_refunds = refund_summary.pop("successful_refunds", [])
                for key, value in refund_summary.items():
                    payment_summary[key] = int(payment_summary[key]) + value
                if refund_summary["refund_created_count"] > 0:
                    payment_summary["payment_refund_created"] = True
                booking_refund_followup_required = True
                if (
                    refund_summary["refund_failed_count"] == 0
                    and refund_summary["refund_processing_count"] == 0
                    and refund_summary["refund_missing_charge_count"] == 0
                    and all_booking_refundable_payments_refunded(payments)
                ):
                    booking.payment_status = "refunded"
                    booking_refund_followup_required = False
                elif (
                    restored_credit_cents > 0
                    and refund_summary["refund_failed_count"] == 0
                    and refund_summary["refund_processing_count"] == 0
                    and refund_summary["refund_missing_charge_count"] == 0
                    and not booking_has_refundable_payments(payments)
                ):
                    booking.payment_status = "credit_restored"
                    booking_refund_followup_required = False
                if booking_refund_followup_required:
                    payment_summary["refund_followup_required"] = True
                if successful_refunds:
                    # Notifications store related_refund_id, so persist refund rows
                    # before the notification helper can create/update its row.
                    db.flush()
                for payment, refund in successful_refunds:
                    create_or_reopen_booking_refunded_notification(
                        db,
                        db_game=db_game,
                        booking=booking,
                        payment=payment,
                        refund=refund,
                        now=now,
                        stripe_refund_processed=True,
                        credit_restored=credit_restored,
                    )
                if credit_restored and not successful_refunds:
                    create_or_reopen_booking_refunded_notification(
                        db,
                        db_game=db_game,
                        booking=booking,
                        payment=None,
                        refund=None,
                        now=now,
                        stripe_refund_processed=False,
                        credit_restored=True,
                    )
            elif has_processing_payment:
                payment_summary["processing_payment_booking_count"] = (
                    int(payment_summary["processing_payment_booking_count"]) + 1
                )
                payment_summary["payment_followup_required"] = True
            elif booking.booking_status == "pending_payment":
                for payment in payments:
                    if (
                        payment.payment_status
                        in CANCELLATION_UNCHARGED_PENDING_PAYMENT_STATUSES
                    ):
                        payment.payment_status = "canceled"
                        payment.failure_code = "game_cancelled"
                        payment.failure_message = (
                            "Game was cancelled before payment completed."
                        )
                        payment.failure_reason = "game_cancelled"
                        payment.updated_at = now
                        db.add(payment)

                released_credit_usages = release_reserved_game_credits(
                    db,
                    booking.id,
                    now=now,
                    release_reason="game_cancelled",
                    user_id=booking.buyer_user_id,
                )
                payment_summary["credit_released_count"] = (
                    int(payment_summary["credit_released_count"])
                    + len(released_credit_usages)
                )
                payment_summary["credit_released_cents"] = (
                    int(payment_summary["credit_released_cents"])
                    + sum(usage.amount_cents for usage in released_credit_usages)
                )

                booking.payment_status = "failed"
                payment_summary["uncharged_pending_booking_count"] = (
                    int(payment_summary["uncharged_pending_booking_count"]) + 1
                )

        mark_booking_cancelled_for_game_cancellation(
            db,
            booking,
            current_user,
            now,
            cancellation_type,
        )
        payment_summary["cancelled_booking_count"] = (
            int(payment_summary["cancelled_booking_count"]) + 1
        )

    return payment_summary


def create_official_cancellation_refunds(
    db: Session,
    db_game: Game,
    booking: Booking,
    payments: list[Payment],
    current_user: User,
    now: datetime,
) -> dict[str, object]:
    summary = build_cancellation_refund_summary()

    for payment in payments:
        if payment.payment_status not in CANCELLATION_AUTO_REFUND_PAYMENT_STATUSES:
            continue

        existing_refund = db.scalars(
            select(Refund)
            .where(
                Refund.payment_id == payment.id,
                Refund.booking_id == booking.id,
                Refund.refund_reason == "game_cancelled",
                Refund.refund_status.in_(
                    {"pending", "approved", "processing", "succeeded"}
                ),
            )
            .limit(1)
        ).first()
        if existing_refund is not None:
            continue

        if not payment.provider_charge_id:
            create_cancellation_refund_record(
                db,
                payment,
                booking,
                current_user,
                now,
                provider_refund_id=None,
                refund_status="failed",
            )
            summary["refund_failed_count"] += 1
            summary["refund_missing_charge_count"] += 1
            continue

        refund_idempotency_key = (
            f"game_cancel:{db_game.id}:payment:{payment.id}:refund"
        )
        try:
            stripe_refund = create_stripe_refund(
                charge_id=payment.provider_charge_id,
                amount_cents=payment.amount_cents,
                currency=payment.currency,
                idempotency_key=refund_idempotency_key,
                metadata={
                    "source": "official_game_cancel",
                    "game_id": str(db_game.id),
                    "booking_id": str(booking.id),
                    "payment_id": str(payment.id),
                    "admin_user_id": str(current_user.id),
                },
            )
        except StripeConfigError:
            create_cancellation_refund_record(
                db,
                payment,
                booking,
                current_user,
                now,
                provider_refund_id=None,
                refund_status="failed",
            )
            summary["refund_failed_count"] += 1
            continue
        except Exception:
            create_cancellation_refund_record(
                db,
                payment,
                booking,
                current_user,
                now,
                provider_refund_id=None,
                refund_status="failed",
            )
            summary["refund_failed_count"] += 1
            continue

        refund_status = map_stripe_refund_status(stripe_refund.status)
        refund = create_cancellation_refund_record(
            db,
            payment,
            booking,
            current_user,
            now,
            provider_refund_id=stripe_refund.id,
            refund_status=refund_status,
        )
        summary["refund_created_count"] += 1

        if refund_status == "succeeded":
            payment.payment_status = "refunded"
            payment.updated_at = now
            db.add(payment)
            summary["successful_refunds"].append((payment, refund))
        elif refund_status == "failed":
            summary["refund_failed_count"] += 1
        else:
            summary["refund_processing_count"] += 1

    return summary


def create_cancellation_refund_record(
    db: Session,
    payment: Payment,
    booking: Booking,
    current_user: User,
    now: datetime,
    *,
    provider_refund_id: str | None,
    refund_status: str,
) -> Refund:
    refund = Refund(
        id=uuid.uuid4(),
        payment_id=payment.id,
        booking_id=booking.id,
        participant_id=None,
        provider_refund_id=provider_refund_id,
        amount_cents=payment.amount_cents,
        currency=payment.currency,
        refund_reason="game_cancelled",
        refund_status=refund_status,
        requested_by_user_id=current_user.id,
        approved_by_user_id=current_user.id,
        requested_at=now,
        approved_at=(
            now
            if refund_status in {"approved", "processing", "succeeded"}
            else None
        ),
        refunded_at=now if refund_status == "succeeded" else None,
        created_at=now,
        updated_at=now,
    )
    db.add(refund)
    return refund


def cancel_game_participants(
    db: Session,
    db_game: Game,
    now: datetime,
    cancellation_type: str,
) -> list[uuid.UUID]:
    notified_user_ids: set[uuid.UUID] = set()
    participants = list_cancellable_game_participants(db, db_game)

    for participant in participants:
        notification_user_id = get_game_cancellation_participant_notification_user_id(
            db_game,
            participant,
        )
        if notification_user_id is not None:
            notified_user_ids.add(notification_user_id)

        participant.participant_status = "cancelled"
        participant.cancellation_type = cancellation_type
        participant.cancelled_at = now
        participant.attendance_status = "not_applicable"
        participant.updated_at = now
        db.add(participant)

    return list(notified_user_ids)


def cancel_game_waitlist_entries(db: Session, db_game: Game, now: datetime) -> None:
    waitlist_entries = list_cancellable_waitlist_entries(db, db_game)

    for waitlist_entry in waitlist_entries:
        waitlist_entry.waitlist_status = "cancelled"
        waitlist_entry.cancelled_at = now
        waitlist_entry.updated_at = now
        db.add(waitlist_entry)


def mark_booking_cancelled_for_game_cancellation(
    db: Session,
    booking: Booking,
    current_user: User,
    now: datetime,
    cancellation_type: str,
) -> None:
    booking.booking_status = "cancelled"
    booking.cancelled_at = now
    booking.cancelled_by_user_id = current_user.id
    booking.cancel_reason = cancellation_type
    booking.updated_at = now
    db.add(booking)


def archive_game_chats(db: Session, db_game: Game, now: datetime) -> None:
    game_chats = db.scalars(
        select(GameChat).where(
            GameChat.game_id == db_game.id,
            GameChat.chat_status.in_({"active", "locked"}),
        )
    ).all()

    for game_chat in game_chats:
        game_chat.chat_status = "archived"
        game_chat.updated_at = now
        db.add(game_chat)


def game_updated_aggregation_key(
    game_id: uuid.UUID,
    recipient_user_id: uuid.UUID,
) -> str:
    return f"game:{game_id}:user:{recipient_user_id}:game_updated"


def resolve_unread_game_notification_rows(
    db: Session,
    *,
    db_game: Game,
    recipient_user_id: uuid.UUID,
    notification_type: str,
    read_at: datetime,
) -> None:
    notifications = db.scalars(
        select(Notification).where(
            Notification.user_id == recipient_user_id,
            Notification.related_game_id == db_game.id,
            Notification.notification_type == notification_type,
            Notification.is_read.is_(False),
        )
    ).all()

    for notification in notifications:
        notification.is_read = True
        if notification.read_at is None:
            notification.read_at = read_at
        notification.updated_at = read_at
        db.add(notification)


def create_game_cancelled_notifications(
    db: Session,
    db_game: Game,
    recipient_user_ids: list[uuid.UUID],
    now: datetime,
    actor_user_id: uuid.UUID | None = None,
) -> None:
    if not recipient_user_ids:
        return

    for recipient_user_id in sorted(set(recipient_user_ids), key=str):
        resolve_aggregated_notification(
            db,
            user_id=recipient_user_id,
            aggregation_key=game_updated_aggregation_key(db_game.id, recipient_user_id),
            read_at=now,
        )
        resolve_unread_game_notification_rows(
            db,
            db_game=db_game,
            recipient_user_id=recipient_user_id,
            notification_type="waitlist_promoted",
            read_at=now,
        )
        resolve_unread_game_notification_rows(
            db,
            db_game=db_game,
            recipient_user_id=recipient_user_id,
            notification_type="game_host_assigned",
            read_at=now,
        )
        resolve_unread_game_notification_rows(
            db,
            db_game=db_game,
            recipient_user_id=recipient_user_id,
            notification_type="game_player_added_by_admin",
            read_at=now,
        )
        db.add(
            Notification(
                id=uuid.uuid4(),
                user_id=recipient_user_id,
                notification_type="game_cancelled",
                notification_category="game_activity",
                notification_domain="game",
                **build_game_notification_fields(
                    db_game,
                    "game_cancelled",
                    event_at=now,
                    force_action_null=True,
                ),
                actor_user_id=actor_user_id,
                related_game_id=db_game.id,
                is_read=False,
                read_at=None,
                created_at=now,
                updated_at=now,
            )
        )


def create_game_cancellation_history(
    db: Session,
    db_game: Game,
    current_user: User,
    old_game_status: str,
    cancel_reason: str | None,
    change_source: str,
    now: datetime,
) -> None:
    db.add(
        GameStatusHistory(
            id=uuid.uuid4(),
            game_id=db_game.id,
            old_publish_status=db_game.publish_status,
            new_publish_status=db_game.publish_status,
            old_game_status=old_game_status,
            new_game_status="cancelled",
            changed_by_user_id=current_user.id,
            change_source=change_source,
            change_reason=cancel_reason,
            created_at=now,
        )
    )


def create_game_cancellation_admin_action(
    db: Session,
    db_game: Game,
    current_user: User,
    cancellation_type: str,
    old_game_status: str,
    cancel_reason: str | None,
    notified_user_ids: list[uuid.UUID],
    payment_summary: dict[str, object],
    now: datetime,
) -> None:
    if cancellation_type != "admin_cancelled":
        return

    record_admin_action(
        db,
        admin_user_id=current_user.id,
        action_type="cancel_game",
        target_game_id=db_game.id,
        reason=cancel_reason,
        metadata={
            "old_game_status": old_game_status,
            "new_game_status": "cancelled",
            "notified_user_count": len(set(notified_user_ids)),
            "cancelled_at": now,
            **payment_summary,
        },
        created_at=now,
    )


def cancel_game_state_workflow(
    db: Session,
    game_id: uuid.UUID,
    cancel_request: GameCancelCreate,
    current_user: User,
) -> Game:
    db_game = db.get(Game, game_id)

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    cancellation_type = require_cancel_permission(db_game, current_user)

    if db_game.publish_status != "published":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only published games can be cancelled.",
        )

    if db_game.game_status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This game is already cancelled.",
        )

    if db_game.game_status not in CANCELLABLE_GAME_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only scheduled or full games can be cancelled.",
        )

    now = datetime.now(timezone.utc)
    require_game_not_started(db_game, now, "Games cannot be cancelled after start time.")
    old_game_status = db_game.game_status
    cancel_reason = normalize_cancel_reason(cancel_request.cancel_reason)
    change_source = "admin" if cancellation_type == "admin_cancelled" else "host"
    notified_user_ids = cancel_game_participants(
        db,
        db_game,
        now,
        cancellation_type,
    )
    if cancellation_type == "admin_cancelled":
        notified_user_ids = add_game_cancellation_host_recipient(
            db_game,
            notified_user_ids,
            current_user.id,
        )
    cancel_game_waitlist_entries(db, db_game, now)
    payment_summary = cancel_game_bookings(
        db, db_game, current_user, now, cancellation_type
    )
    archive_game_chats(db, db_game, now)
    create_game_cancelled_notifications(
        db,
        db_game,
        notified_user_ids,
        now,
        actor_user_id=current_user.id,
    )
    create_game_cancellation_history(
        db,
        db_game,
        current_user,
        old_game_status,
        cancel_reason,
        change_source,
        now,
    )
    create_game_cancellation_admin_action(
        db,
        db_game,
        current_user,
        cancellation_type,
        old_game_status,
        cancel_reason,
        notified_user_ids,
        payment_summary,
        now,
    )

    db_game.game_status = "cancelled"
    db_game.cancelled_at = now
    db_game.cancelled_by_user_id = current_user.id
    db_game.cancel_reason = cancel_reason
    db_game.completed_at = None
    db_game.completed_by_user_id = None
    db_game.updated_at = now

    try:
        db.add(db_game)
        db.commit()
        db.refresh(db_game)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_conflict_detail(exc),
        ) from exc

    return db_game
