"""Game cancellation helper queries and readiness checks."""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    AdminAction,
    Booking,
    Game,
    GameCredit,
    GameChat,
    GameCreditUsage,
    GameParticipant,
    MoneyIssue,
    Notification,
    Payment,
    Refund,
    User,
    WaitlistEntry,
)
from backend.schemas.admin_official_game_schema import (
    AdminOfficialGameCancelExecute,
    AdminOfficialGameCancellationBookingImpactRead,
    AdminOfficialGameCancellationBookingResultRead,
    AdminOfficialGameCancellationPreviewRead,
    AdminOfficialGameCancellationRefundRead,
    AdminOfficialGameCancellationResultRead,
)
from backend.schemas.game_schema import (
    GameCancelCreate,
)
from backend.services.admin_action_service import record_admin_action
from backend.services.admin_money_issue_service import (
    stage_credit_money_issue,
    stage_refund_money_issue,
)
from backend.services.admin_review_service import (
    close_open_content_moderation_case_for_game_lifecycle,
)
from backend.services.auth_service import user_is_active_admin
from backend.services.game_rules import (
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
    game_requires_app_player_payment,
    require_game_not_started,
)
from backend.services.game_notification_service import (
    create_or_reopen_booking_refunded_notification,
    game_updated_aggregation_key,
)
from backend.services.game_credit_service import (
    GameCreditLedgerError,
    release_reserved_game_credits,
    restore_redeemed_game_credits,
)
from backend.services.notification_event_service import (
    build_game_notification_fields,
    resolve_aggregated_notification,
)
from backend.services.status_history_service import (
    add_game_status_history_if_changed,
)
from backend.services.refund_event_service import record_refund_event
from backend.services.stripe_service import (
    StripeConfigError,
    create_refund as create_stripe_refund,
)


class OfficialCancellationCreditFailure(Exception):
    def __init__(
        self,
        *,
        booking_id: uuid.UUID,
        detail: str,
        operation: str,
    ) -> None:
        super().__init__(detail)
        self.booking_id = booking_id
        self.detail = detail
        self.operation = operation


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
        if user_is_active_admin(current_user):
            return "admin_cancelled"

        if db_game.host_user_id == current_user.id:
            return "host_cancelled"

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the community game host or an admin can cancel this game.",
        )

    if db_game.game_type == "official":
        if user_is_active_admin(current_user):
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


def list_booking_refunds(db: Session, booking: Booking) -> list[Refund]:
    return list(
        db.scalars(
            select(Refund)
            .where(Refund.booking_id == booking.id)
            .order_by(Refund.created_at.asc(), Refund.id.asc())
        ).all()
    )


def list_booking_credit_usages(
    db: Session,
    booking: Booking,
) -> list[GameCreditUsage]:
    return list(
        db.scalars(
            select(GameCreditUsage)
            .where(GameCreditUsage.booking_id == booking.id)
            .order_by(GameCreditUsage.created_at.asc(), GameCreditUsage.id.asc())
        ).all()
    )


def list_booking_participants(
    db: Session,
    booking: Booking,
) -> list[GameParticipant]:
    return list(
        db.scalars(
            select(GameParticipant).where(GameParticipant.booking_id == booking.id)
        ).all()
    )


def sum_credit_usage_cents(
    usages: list[GameCreditUsage],
    statuses: set[str],
) -> int:
    return sum(
        usage.amount_cents
        for usage in usages
        if usage.usage_status in statuses
    )


def normalize_preview_value(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [normalize_preview_value(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): normalize_preview_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    return value


def build_official_cancellation_preview_token(payload: dict[str, Any]) -> str:
    serialized_payload = json.dumps(
        normalize_preview_value(payload),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized_payload.encode("utf-8")).hexdigest()


def hash_sensitive_identifier(value: str | None) -> str | None:
    if not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def map_stripe_refund_status(stripe_status: str) -> str:
    normalized_status = stripe_status.strip().lower()
    if normalized_status == "succeeded":
        return "succeeded"

    if normalized_status == "failed":
        return "failed"

    if normalized_status in {"canceled", "cancelled"}:
        return "cancelled"

    return "processing"


def all_booking_refundable_payments_refunded(
    payments: list[Payment],
    successful_refunds: list[tuple[Payment, Refund]],
) -> bool:
    refundable_payments = [
        payment
        for payment in payments
        if payment.payment_status
        in CANCELLATION_REFUND_FOLLOWUP_PAYMENT_STATUSES
    ]
    successful_payment_ids = {payment.id for payment, _refund in successful_refunds}
    return bool(refundable_payments) and all(
        payment.id in successful_payment_ids for payment in refundable_payments
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


def prepare_official_cancellation_credit_outcomes(
    db: Session,
    *,
    bookings: list[Booking],
    now: datetime,
) -> dict[uuid.UUID, dict[str, list[GameCreditUsage]]]:
    credit_outcomes: dict[uuid.UUID, dict[str, list[GameCreditUsage]]] = {}

    for booking in bookings:
        payments = list_booking_payments(db, booking)
        payment_statuses = {payment.payment_status for payment in payments}
        has_paid_payment = bool(
            payment_statuses & CANCELLATION_REFUND_FOLLOWUP_PAYMENT_STATUSES
        ) or (
            booking.payment_status
            in CANCELLATION_REFUND_FOLLOWUP_BOOKING_PAYMENT_STATUSES
        )
        has_processing_payment = "processing" in payment_statuses
        restored_usages: list[GameCreditUsage] = []
        released_usages: list[GameCreditUsage] = []

        try:
            if has_paid_payment:
                restored_usages = restore_redeemed_game_credits(
                    db,
                    booking.id,
                    now=now,
                    restore_reason="game_cancelled",
                    user_id=booking.buyer_user_id,
                )
            elif not has_processing_payment and booking.booking_status == "pending_payment":
                released_usages = release_reserved_game_credits(
                    db,
                    booking.id,
                    now=now,
                    reason_code="game_cancelled",
                    user_id=booking.buyer_user_id,
                )
        except GameCreditLedgerError as exc:
            operation = "restore" if has_paid_payment else "release"
            raise OfficialCancellationCreditFailure(
                booking_id=booking.id,
                detail=str(exc),
                operation=operation,
            ) from exc

        credit_outcomes[booking.id] = {
            "restored": restored_usages,
            "released": released_usages,
        }

    # Surface local ledger constraint errors before any external refund call.
    db.flush()
    return credit_outcomes


def get_game_for_cancellation_or_404(db: Session, game_id: uuid.UUID) -> Game:
    db_game = db.get(Game, game_id)

    if db_game is None or db_game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    return db_game


def validate_game_cancellation_request(
    db_game: Game,
    current_user: User,
    *,
    now: datetime,
) -> str:
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
            detail="Only active games can be cancelled.",
        )

    require_game_not_started(db_game, now, "Games cannot be cancelled after start time.")
    return cancellation_type


def require_official_game_for_admin_cancellation(db_game: Game) -> None:
    if db_game.game_type != "official":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only official games use the admin cancellation workflow.",
        )


def build_official_cancellation_booking_impact(
    db: Session,
    booking: Booking,
) -> AdminOfficialGameCancellationBookingImpactRead:
    payments = list_booking_payments(db, booking)
    refunds = list_booking_refunds(db, booking)
    credit_usages = list_booking_credit_usages(db, booking)
    participants = list_booking_participants(db, booking)

    payment_statuses = sorted({payment.payment_status for payment in payments})
    refund_statuses = sorted({refund.refund_status for refund in refunds})
    succeeded_payments = [
        payment for payment in payments if payment.payment_status == "succeeded"
    ]
    missing_charge_payments = [
        payment for payment in succeeded_payments if not payment.provider_charge_id
    ]
    refundable_payments = [
        payment for payment in succeeded_payments if payment.provider_charge_id
    ]
    cash_refundable_cents = sum(payment.amount_cents for payment in refundable_payments)
    credit_restorable_cents = sum_credit_usage_cents(credit_usages, {"redeemed"})
    credit_releasable_cents = sum_credit_usage_cents(credit_usages, {"reserved"})

    follow_up_reason = None
    if "processing" in payment_statuses:
        follow_up_reason = "processing_payment"
    elif missing_charge_payments:
        follow_up_reason = "missing_stripe_charge_id"
    elif set(refund_statuses) & {"pending", "approved", "processing"}:
        follow_up_reason = "active_refund"

    follow_up_required = follow_up_reason is not None
    if follow_up_required:
        result_category = "follow_up_required"
    elif cash_refundable_cents > 0 and credit_restorable_cents > 0:
        result_category = "stripe_refund_and_credit_restore"
    elif cash_refundable_cents > 0:
        result_category = "stripe_refund"
    elif credit_restorable_cents > 0:
        result_category = "credit_restore"
    elif credit_releasable_cents > 0:
        result_category = "pending_hold_release"
    else:
        result_category = "cancel_only"

    return AdminOfficialGameCancellationBookingImpactRead(
        booking_id=booking.id,
        buyer_user_id=booking.buyer_user_id,
        booking_status=booking.booking_status,
        booking_payment_status=booking.payment_status,
        participant_count=len(participants),
        payment_statuses=payment_statuses,
        refund_statuses=refund_statuses,
        result_category=result_category,
        cash_refundable_cents=cash_refundable_cents,
        credit_restorable_cents=credit_restorable_cents,
        credit_releasable_cents=credit_releasable_cents,
        follow_up_required=follow_up_required,
        follow_up_reason=follow_up_reason,
    )


def build_official_cancellation_preview_payload(
    db: Session,
    db_game: Game,
    booking_impacts: list[AdminOfficialGameCancellationBookingImpactRead],
) -> dict[str, Any]:
    active_participants = list_cancellable_game_participants(db, db_game)
    active_waitlist_entries = list_cancellable_waitlist_entries(db, db_game)
    bookings = list_cancellable_bookings(db, db_game)
    payment_snapshots = []
    refund_snapshots = []
    credit_usage_snapshots = []

    for booking in bookings:
        for payment in list_booking_payments(db, booking):
            payment_snapshots.append(
                {
                    "id": payment.id,
                    "booking_id": payment.booking_id,
                    "payment_status": payment.payment_status,
                    "amount_cents": payment.amount_cents,
                    "provider_charge_id_present": bool(payment.provider_charge_id),
                    "provider_charge_id_hash": hash_sensitive_identifier(
                        payment.provider_charge_id
                    ),
                    "updated_at": payment.updated_at,
                }
            )
        for refund in list_booking_refunds(db, booking):
            refund_snapshots.append(
                {
                    "id": refund.id,
                    "booking_id": refund.booking_id,
                    "payment_id": refund.payment_id,
                    "refund_status": refund.refund_status,
                    "amount_cents": refund.amount_cents,
                    "updated_at": refund.updated_at,
                }
            )
        for usage in list_booking_credit_usages(db, booking):
            credit_usage_snapshots.append(
                {
                    "id": usage.id,
                    "booking_id": usage.booking_id,
                    "game_credit_id": usage.game_credit_id,
                    "usage_type": usage.usage_type,
                    "usage_status": usage.usage_status,
                    "amount_cents": usage.amount_cents,
                    "updated_at": usage.updated_at,
                }
            )

    return {
        "game": {
            "id": db_game.id,
            "game_status": db_game.game_status,
            "publish_status": db_game.publish_status,
            "starts_at": db_game.starts_at,
            "updated_at": db_game.updated_at,
        },
        "participants": [
            {
                "id": participant.id,
                "booking_id": participant.booking_id,
                "status": participant.participant_status,
                "type": participant.participant_type,
                "updated_at": participant.updated_at,
            }
            for participant in sorted(active_participants, key=lambda item: str(item.id))
        ],
        "waitlist_entries": [
            {
                "id": entry.id,
                "status": entry.waitlist_status,
                "party_size": entry.party_size,
                "updated_at": entry.updated_at,
            }
            for entry in sorted(active_waitlist_entries, key=lambda item: str(item.id))
        ],
        "bookings": [
            {
                "id": booking.id,
                "booking_status": booking.booking_status,
                "payment_status": booking.payment_status,
                "total_cents": booking.total_cents,
                "updated_at": booking.updated_at,
            }
            for booking in bookings
        ],
        "payments": sorted(payment_snapshots, key=lambda item: str(item["id"])),
        "refunds": sorted(refund_snapshots, key=lambda item: str(item["id"])),
        "credit_usages": sorted(
            credit_usage_snapshots,
            key=lambda item: str(item["id"]),
        ),
        "booking_impacts": [
            impact.model_dump(mode="json") for impact in booking_impacts
        ],
    }


def build_official_game_cancellation_preview(
    db: Session,
    *,
    game_id: uuid.UUID,
    admin_user: User,
) -> AdminOfficialGameCancellationPreviewRead:
    db_game = get_game_for_cancellation_or_404(db, game_id)
    require_official_game_for_admin_cancellation(db_game)
    validate_game_cancellation_request(
        db_game,
        admin_user,
        now=datetime.now(timezone.utc),
    )

    bookings = list_cancellable_bookings(db, db_game)
    booking_impacts = [
        build_official_cancellation_booking_impact(db, booking)
        for booking in bookings
    ]
    preview_payload = build_official_cancellation_preview_payload(
        db,
        db_game,
        booking_impacts,
    )
    preview_token = build_official_cancellation_preview_token(preview_payload)

    return AdminOfficialGameCancellationPreviewRead(
        game_id=db_game.id,
        game_status=db_game.game_status,
        preview_token=preview_token,
        booking_count=len(bookings),
        participant_count=len(list_cancellable_game_participants(db, db_game)),
        waitlist_entry_count=len(list_cancellable_waitlist_entries(db, db_game)),
        cash_refundable_cents=sum(
            impact.cash_refundable_cents for impact in booking_impacts
        ),
        credit_restorable_cents=sum(
            impact.credit_restorable_cents for impact in booking_impacts
        ),
        credit_releasable_cents=sum(
            impact.credit_releasable_cents for impact in booking_impacts
        ),
        refund_follow_up_required=any(
            impact.follow_up_required
            and impact.follow_up_reason != "processing_payment"
            for impact in booking_impacts
        ),
        payment_follow_up_required=any(
            impact.follow_up_reason == "processing_payment"
            for impact in booking_impacts
        ),
        booking_impacts=booking_impacts,
    )


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
    credit_outcomes = (
        prepare_official_cancellation_credit_outcomes(
            db,
            bookings=bookings,
            now=now,
        )
        if app_payment_required
        else {}
    )

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
                restored_credit_usages = credit_outcomes[booking.id]["restored"]
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
                    and all_booking_refundable_payments_refunded(
                        payments,
                        successful_refunds,
                    )
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
                        payment.updated_at = now
                        db.add(payment)

                released_credit_usages = credit_outcomes[booking.id]["released"]
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
                reason_code="provider_charge_id_missing",
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
                reason_code="stripe_refunds_not_configured",
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
                reason_code="stripe_refund_request_failed",
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
            reason_code=f"stripe_refund_{refund_status}",
        )
        summary["refund_created_count"] += 1

        if refund_status == "succeeded":
            summary["successful_refunds"].append((payment, refund))
        elif refund_status in {"failed", "cancelled"}:
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
    reason_code: str,
) -> Refund:
    refund = Refund(
        id=uuid.uuid4(),
        payment_id=payment.id,
        booking_id=booking.id,
        participant_id=None,
        origin_workflow="official_game_cancellation",
        provider="stripe",
        provider_refund_id=provider_refund_id,
        provider_charge_id=payment.provider_charge_id,
        provider_status=refund_status if provider_refund_id is not None else None,
        provider_status_observed_at=now if provider_refund_id is not None else None,
        last_refund_event_at=now,
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
    db.flush()
    refund_event = record_refund_event(
        db,
        refund=refund,
        event_type="provider_result_recorded",
        event_source="system",
        actor_user_id=current_user.id,
        provider="stripe",
        provider_refund_id=provider_refund_id,
        provider_charge_id=payment.provider_charge_id,
        provider_status=refund_status if provider_refund_id is not None else None,
        new_refund_status=refund_status,
        reason_code=reason_code,
        summary="Official-game cancellation refund result recorded.",
        occurred_at=now,
    )
    if refund_status in {"failed", "cancelled"}:
        stage_refund_money_issue(
            db,
            refund=refund,
            payment=payment,
            issue_type=(
                "refund_missing_provider_reference"
                if reason_code == "provider_charge_id_missing"
                else (
                    "refund_cancelled"
                    if refund_status == "cancelled"
                    else "refund_failed"
                )
            ),
            reason_code=reason_code,
            summary="Official-game cancellation refund could not complete.",
            refund_event=refund_event,
            now=now,
        )
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


def close_game_chats(db: Session, db_game: Game, now: datetime) -> None:
    game_chats = db.scalars(
        select(GameChat).where(
            GameChat.game_id == db_game.id,
            GameChat.chat_status == "active",
        )
    ).all()

    for game_chat in game_chats:
        game_chat.chat_status = "closed"
        game_chat.closed_at = now
        game_chat.updated_at = now
        db.add(game_chat)


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
    add_game_status_history_if_changed(
        db,
        db_game,
        old_publish_status=db_game.publish_status,
        old_game_status=old_game_status,
        new_game_status="cancelled",
        changed_by_user_id=current_user.id,
        change_source=change_source,
        reason=cancel_reason,
        changed_at=now,
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
    idempotency_key: str | None = None,
    action_type: str = "cancel_game",
) -> AdminAction | None:
    if cancellation_type != "admin_cancelled":
        return None

    cancellation_source = "admin" if cancellation_type == "admin_cancelled" else "host"
    return record_admin_action(
        db,
        admin_user_id=current_user.id,
        action_type=action_type,
        target_game_id=db_game.id,
        target_user_id=db_game.host_user_id,
        reason=cancel_reason,
        metadata={
            "old_game_status": old_game_status,
            "new_game_status": "cancelled",
            "cancellation_source": cancellation_source,
            "notified_user_count": len(set(notified_user_ids)),
            "cancelled_at": now,
            **payment_summary,
        },
        idempotency_key=idempotency_key,
        created_at=now,
    )


def build_community_game_review_case_closure(
    *,
    cancellation_type: str,
    admin_action_type: str,
) -> tuple[str, str, str, str]:
    if cancellation_type == "admin_cancelled":
        if admin_action_type == "admin_cancel_community_game":
            return (
                "enforcement_applied",
                "admin_moderation_cancelled",
                "admin",
                (
                    "Community Game was cancelled by an admin enforcement "
                    "action before moderation review was completed."
                ),
            )
        return (
            "no_action_needed",
            "admin_operational_cancelled",
            "admin",
            (
                "Community Game was cancelled by an admin operational action "
                "before moderation review was completed."
            ),
        )
    return (
        "no_action_needed",
        "host_cancelled",
        "host",
        (
            "Community Game was cancelled by its host before moderation review "
            "was completed."
        ),
    )


def list_official_cancellation_money_issue_ids(
    db: Session,
    *,
    db_game: Game,
    payment_summary: dict[str, object],
) -> list[uuid.UUID]:
    if not (
        payment_summary.get("refund_followup_required")
        or payment_summary.get("payment_followup_required")
    ):
        return []

    return list(
        db.scalars(
            select(MoneyIssue.id)
            .where(
                MoneyIssue.target_game_id == db_game.id,
                MoneyIssue.status == "open",
            )
            .order_by(MoneyIssue.first_detected_at.asc(), MoneyIssue.id.asc())
        ).all()
    )


def record_official_cancellation_credit_failure(
    db: Session,
    *,
    admin_user: User,
    failure: OfficialCancellationCreditFailure,
    game_id: uuid.UUID,
) -> uuid.UUID | None:
    usage_status = "reserved" if failure.operation == "release" else "redeemed"
    credit_usages = list(
        db.scalars(
            select(GameCreditUsage)
            .join(GameCredit, GameCreditUsage.game_credit_id == GameCredit.id)
            .where(
                GameCreditUsage.booking_id == failure.booking_id,
                GameCreditUsage.usage_type == "redeem",
                GameCreditUsage.usage_status == usage_status,
            )
            .order_by(GameCreditUsage.created_at.asc(), GameCreditUsage.id.asc())
            .with_for_update()
        ).all()
    )
    if not credit_usages:
        return None

    first_issue_id = None
    for credit_usage in credit_usages:
        money_issue = stage_credit_money_issue(
            db,
            credit_usage=credit_usage,
            game_credit=db.get(GameCredit, credit_usage.game_credit_id),
            issue_type=(
                "credit_release_failed"
                if failure.operation == "release"
                else "credit_restore_failed"
            ),
            origin_workflow="official_game_cancellation",
            reason_code=f"credit_{failure.operation}_failed",
            summary=(
                "Official-game cancellation could not complete an internal "
                "game-credit return."
            ),
        )
        first_issue_id = first_issue_id or money_issue.id
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_conflict_detail(exc),
        ) from exc

    return first_issue_id


def abort_official_cancellation_for_credit_failure(
    db: Session,
    *,
    admin_user: User,
    failure: OfficialCancellationCreditFailure,
    game_id: uuid.UUID,
) -> None:
    db.rollback()
    record_official_cancellation_credit_failure(
        db,
        admin_user=admin_user,
        failure=failure,
        game_id=game_id,
    )
    operation_label = "restored" if failure.operation == "restore" else "released"
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=(
            f"Game credit could not be {operation_label}. The game was not "
            "cancelled and a Money Issue was created."
        ),
    )


def apply_game_cancellation_state(
    db: Session,
    db_game: Game,
    cancel_request: GameCancelCreate,
    current_user: User,
    admin_action_idempotency_key: str | None = None,
    admin_action_type: str = "cancel_game",
) -> tuple[Game, dict[str, object], list[uuid.UUID], AdminAction | None, list[uuid.UUID]]:
    now = datetime.now(timezone.utc)
    cancellation_type = validate_game_cancellation_request(
        db_game,
        current_user,
        now=now,
    )
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
    close_game_chats(db, db_game, now)
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
    admin_action = create_game_cancellation_admin_action(
        db,
        db_game,
        current_user,
        cancellation_type,
        old_game_status,
        cancel_reason,
        notified_user_ids,
        payment_summary,
        now,
        admin_action_idempotency_key,
        admin_action_type,
    )
    money_issue_ids = list_official_cancellation_money_issue_ids(
        db,
        db_game=db_game,
        payment_summary=payment_summary,
    )

    db_game.game_status = "cancelled"
    db_game.cancelled_at = now
    db_game.cancelled_by_user_id = current_user.id
    db_game.cancellation_source = (
        "admin" if cancellation_type == "admin_cancelled" else "host"
    )
    db_game.cancel_reason = cancel_reason
    db_game.completed_at = None
    db_game.completed_by_user_id = None
    db_game.updated_at = now

    db.add(db_game)
    if db_game.game_type == "community":
        (
            closure_outcome,
            lifecycle_action,
            trigger_actor_type,
            closure_reason,
        ) = build_community_game_review_case_closure(
            cancellation_type=cancellation_type,
            admin_action_type=admin_action_type,
        )
        close_open_content_moderation_case_for_game_lifecycle(
            db,
            game_id=db_game.id,
            closure_outcome=closure_outcome,
            closure_reason=closure_reason,
            lifecycle_action=lifecycle_action,
            trigger_actor_type=trigger_actor_type,
            trigger_actor_user_id=current_user.id,
            closed_by_user_id=(
                current_user.id if trigger_actor_type == "admin" else None
            ),
            admin_action=admin_action,
            previous_game_status=old_game_status,
            new_game_status="cancelled",
            closed_at=now,
        )
    return db_game, payment_summary, notified_user_ids, admin_action, money_issue_ids


def lock_official_cancellation_state(db: Session, game_id: uuid.UUID) -> Game:
    db_game = db.scalars(
        select(Game)
        .where(Game.id == game_id, Game.deleted_at.is_(None))
        .with_for_update()
    ).first()
    if db_game is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    bookings = list_cancellable_bookings(db, db_game)
    booking_ids = [booking.id for booking in bookings]

    db.scalars(
        select(GameParticipant)
        .where(GameParticipant.game_id == db_game.id)
        .with_for_update()
    ).all()
    db.scalars(
        select(WaitlistEntry)
        .where(WaitlistEntry.game_id == db_game.id)
        .with_for_update()
    ).all()

    if booking_ids:
        db.scalars(
            select(Booking)
            .where(Booking.id.in_(booking_ids))
            .with_for_update()
        ).all()
        db.scalars(
            select(Payment)
            .where(Payment.booking_id.in_(booking_ids))
            .with_for_update()
        ).all()
        db.scalars(
            select(Refund)
            .where(Refund.booking_id.in_(booking_ids))
            .with_for_update()
        ).all()
        db.scalars(
            select(GameCreditUsage)
            .where(GameCreditUsage.booking_id.in_(booking_ids))
            .with_for_update()
        ).all()

    return db_game


def build_official_cancellation_booking_result(
    db: Session,
    booking_id: uuid.UUID,
) -> AdminOfficialGameCancellationBookingResultRead:
    booking = db.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found.",
        )

    payments = list_booking_payments(db, booking)
    payment_by_id = {payment.id: payment for payment in payments}
    refunds = [
        refund
        for refund in list_booking_refunds(db, booking)
        if refund.refund_reason == "game_cancelled"
    ]
    credit_usages = list_booking_credit_usages(db, booking)
    credit_restored_cents = sum_credit_usage_cents(credit_usages, {"restored"})
    credit_released_cents = sum_credit_usage_cents(credit_usages, {"released"})
    succeeded_refunds = [
        refund for refund in refunds if refund.refund_status == "succeeded"
    ]
    processing_refunds = [
        refund
        for refund in refunds
        if refund.refund_status in {"pending", "approved", "processing"}
    ]
    failed_refunds = [
        refund
        for refund in refunds
        if refund.refund_status in {"failed", "cancelled"}
    ]
    has_processing_payment = any(
        payment.payment_status == "processing" for payment in payments
    )
    missing_charge_failure = any(
        payment_by_id.get(refund.payment_id) is not None
        and not payment_by_id[refund.payment_id].provider_charge_id
        for refund in failed_refunds
    )

    follow_up_reason = None
    if missing_charge_failure:
        follow_up_reason = "missing_stripe_charge_id"
    elif failed_refunds:
        follow_up_reason = "stripe_refund_failed"
    elif processing_refunds:
        follow_up_reason = "stripe_refund_processing"
    elif has_processing_payment:
        follow_up_reason = "processing_payment"
    elif booking.payment_status in {"paid", "partially_refunded", "disputed"}:
        follow_up_reason = "payment_state_follow_up"

    follow_up_required = follow_up_reason is not None
    if follow_up_required:
        result_category = "follow_up_required"
    elif succeeded_refunds and credit_restored_cents > 0:
        result_category = "stripe_refunded_and_credit_restored"
    elif succeeded_refunds:
        result_category = "stripe_refunded"
    elif credit_restored_cents > 0:
        result_category = "credit_restored"
    elif credit_released_cents > 0:
        result_category = "pending_hold_released"
    else:
        result_category = "cancelled"

    return AdminOfficialGameCancellationBookingResultRead(
        booking_id=booking.id,
        buyer_user_id=booking.buyer_user_id,
        booking_status=booking.booking_status,
        booking_payment_status=booking.payment_status,
        result_category=result_category,
        refunds=[
            AdminOfficialGameCancellationRefundRead(
                id=refund.id,
                payment_id=refund.payment_id,
                amount_cents=refund.amount_cents,
                currency=refund.currency,
                refund_status=refund.refund_status,
            )
            for refund in refunds
        ],
        cash_refunded_cents=sum(
            refund.amount_cents for refund in succeeded_refunds
        ),
        credit_restored_cents=credit_restored_cents,
        credit_released_cents=credit_released_cents,
        follow_up_required=follow_up_required,
        follow_up_reason=follow_up_reason,
    )


def execute_official_game_cancellation(
    db: Session,
    *,
    game_id: uuid.UUID,
    admin_user: User,
    cancel_request: AdminOfficialGameCancelExecute,
) -> AdminOfficialGameCancellationResultRead:
    cancel_reason = normalize_cancel_reason(cancel_request.reason)
    if cancel_reason is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="reason is required.",
        )

    db_game = lock_official_cancellation_state(db, game_id)
    preview = build_official_game_cancellation_preview(
        db,
        game_id=game_id,
        admin_user=admin_user,
    )
    if preview.preview_token != cancel_request.preview_token:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cancellation impact changed. Refresh the preview before cancelling.",
        )

    booking_ids = [impact.booking_id for impact in preview.booking_impacts]
    try:
        (
            db_game,
            payment_summary,
            notified_user_ids,
            _admin_action,
            money_issue_ids,
        ) = apply_game_cancellation_state(
            db,
            db_game,
            GameCancelCreate(cancel_reason=cancel_reason),
            admin_user,
        )
    except OfficialCancellationCreditFailure as exc:
        abort_official_cancellation_for_credit_failure(
            db,
            admin_user=admin_user,
            failure=exc,
            game_id=game_id,
        )
    db.flush()

    booking_results = [
        build_official_cancellation_booking_result(db, booking_id)
        for booking_id in booking_ids
    ]
    result = AdminOfficialGameCancellationResultRead(
        game=db_game,
        preview_token=preview.preview_token,
        cancelled_booking_count=int(payment_summary["cancelled_booking_count"]),
        cancelled_participant_count=preview.participant_count,
        cancelled_waitlist_entry_count=preview.waitlist_entry_count,
        notified_user_count=len(set(notified_user_ids)),
        refund_created_count=int(payment_summary["refund_created_count"]),
        refund_failed_count=int(payment_summary["refund_failed_count"]),
        refund_processing_count=int(payment_summary["refund_processing_count"]),
        refund_missing_charge_count=int(
            payment_summary["refund_missing_charge_count"]
        ),
        credit_restored_count=int(payment_summary["credit_restored_count"]),
        credit_restored_cents=int(payment_summary["credit_restored_cents"]),
        credit_released_count=int(payment_summary["credit_released_count"]),
        credit_released_cents=int(payment_summary["credit_released_cents"]),
        refund_follow_up_required=bool(
            payment_summary["refund_followup_required"]
        ),
        payment_follow_up_required=bool(
            payment_summary["payment_followup_required"]
        ),
        money_issue_ids=money_issue_ids,
        booking_results=booking_results,
    )

    try:
        db.commit()
        db.refresh(db_game)
        result.game = db_game
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_conflict_detail(exc),
        ) from exc

    return result


def cancel_game_state_workflow(
    db: Session,
    game_id: uuid.UUID,
    cancel_request: GameCancelCreate,
    current_user: User,
) -> Game:
    db_game = get_game_for_cancellation_or_404(db, game_id)
    try:
        apply_game_cancellation_state(db, db_game, cancel_request, current_user)
    except OfficialCancellationCreditFailure as exc:
        abort_official_cancellation_for_credit_failure(
            db,
            admin_user=current_user,
            failure=exc,
            game_id=game_id,
        )

    try:
        db.commit()
        db.refresh(db_game)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_game_conflict_detail(exc),
        ) from exc

    return db_game
