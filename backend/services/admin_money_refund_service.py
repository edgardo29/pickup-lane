"""Admin money refund mutation workflows."""

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import AdminAction, Booking, Game, Payment, Refund, User
from backend.schemas.admin_money_schema import (
    AdminMoneyRefundDetailRead,
    AdminMoneyRefundRetryCreate,
)
from backend.services.admin_action_service import (
    normalize_idempotency_key,
    normalize_optional_text,
    record_admin_action,
)
from backend.services.admin_money_service import get_admin_money_refund_detail
from backend.services.game_service import (
    create_or_reopen_booking_refunded_notification,
    game_allows_inbox_action,
)
from backend.services.refund_service import (
    build_refund_conflict_detail,
    refund_audit_metadata,
    refund_audit_snapshot,
    validate_refund_amount_available,
)
from backend.services.stripe_service import (
    StripeConfigError,
    StripeRefundResult,
    create_refund as create_stripe_refund,
)
from backend.services.support_flag_service import stage_support_flag

RETRYABLE_REFUND_STATUSES = {"failed", "cancelled"}
RETRYABLE_PAYMENT_STATUSES = {"succeeded", "partially_refunded"}


def map_admin_money_retry_refund_status(provider_status: str) -> str:
    normalized_status = provider_status.strip().lower()
    if normalized_status == "succeeded":
        return "succeeded"
    if normalized_status == "failed":
        return "failed"
    if normalized_status in {"canceled", "cancelled"}:
        return "cancelled"
    return "processing"


def normalize_retry_reason(value: str) -> str:
    reason = normalize_optional_text(value, "reason")
    if reason is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="reason is required.",
        )
    return reason


def normalize_retry_idempotency_key(value: str) -> str:
    idempotency_key = normalize_idempotency_key(value)
    if idempotency_key is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="idempotency_key is required.",
        )
    return idempotency_key


def get_existing_retry_action(
    db: Session,
    *,
    admin_user_id: uuid.UUID,
    refund_id: uuid.UUID,
    idempotency_key: str,
) -> AdminAction | None:
    actions = db.scalars(
        select(AdminAction)
        .where(
            AdminAction.admin_user_id == admin_user_id,
            AdminAction.action_type == "update_refund",
            AdminAction.target_refund_id == refund_id,
            AdminAction.idempotency_key == idempotency_key,
        )
        .order_by(AdminAction.created_at.desc(), AdminAction.id.desc())
        .limit(10)
    ).all()

    for action in actions:
        metadata = action.metadata_ or {}
        if metadata.get("source") == "admin_money_refund_retry":
            return action

    return None


def get_refund_for_retry_or_404(db: Session, refund_id: uuid.UUID) -> Refund:
    refund = db.scalars(
        select(Refund).where(Refund.id == refund_id).with_for_update()
    ).first()

    if refund is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found.",
        )

    return refund


def get_payment_for_retry_or_404(db: Session, payment_id: uuid.UUID) -> Payment:
    payment = db.scalars(
        select(Payment).where(Payment.id == payment_id).with_for_update()
    ).first()

    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        )

    return payment


def get_booking_for_retry(db: Session, booking_id: uuid.UUID | None) -> Booking | None:
    if booking_id is None:
        return None

    return db.scalars(
        select(Booking).where(Booking.id == booking_id).with_for_update()
    ).first()


def validate_refund_retry(
    db: Session,
    *,
    refund: Refund,
    payment: Payment,
) -> None:
    if refund.refund_status not in RETRYABLE_REFUND_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only failed or cancelled refunds can be retried.",
        )

    if payment.payment_status not in RETRYABLE_PAYMENT_STATUSES or payment.paid_at is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refund retry requires a succeeded payment.",
        )

    if not payment.provider_charge_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refund retry requires a Stripe charge id.",
        )

    if payment.booking_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refund retry requires a booking payment.",
        )

    if refund.booking_id is not None and refund.booking_id != payment.booking_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refund booking must match the payment booking.",
        )

    if refund.currency != payment.currency:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refund currency must match the payment currency.",
        )

    validate_refund_amount_available(
        db,
        payment.id,
        payment.amount_cents,
        refund.amount_cents,
        exclude_refund_id=refund.id,
    )


def sum_succeeded_refunds_for_payment(
    db: Session,
    *,
    payment_id: uuid.UUID,
    excluding_refund_id: uuid.UUID,
) -> int:
    return db.scalar(
        select(func.coalesce(func.sum(Refund.amount_cents), 0)).where(
            Refund.payment_id == payment_id,
            Refund.refund_status == "succeeded",
            Refund.id != excluding_refund_id,
        )
    ) or 0


def sync_refunded_payment_state(
    db: Session,
    *,
    payment: Payment,
    refund: Refund,
    booking: Booking | None,
    now: datetime,
) -> None:
    succeeded_total = (
        sum_succeeded_refunds_for_payment(
            db,
            payment_id=payment.id,
            excluding_refund_id=refund.id,
        )
        + refund.amount_cents
    )
    payment.payment_status = (
        "refunded"
        if succeeded_total >= payment.amount_cents
        else "partially_refunded"
    )
    payment.updated_at = now
    db.add(payment)

    if booking is None:
        return

    booking_payments = list(
        db.scalars(
            select(Payment)
            .where(Payment.booking_id == booking.id)
            .order_by(Payment.created_at.asc(), Payment.id.asc())
            .with_for_update()
        ).all()
    )
    refundable_booking_payments = [
        booking_payment
        for booking_payment in booking_payments
        if booking_payment.payment_status
        in {"succeeded", "partially_refunded", "refunded", "disputed"}
    ]

    if refundable_booking_payments and all(
        booking_payment.payment_status == "refunded"
        for booking_payment in refundable_booking_payments
    ):
        booking.payment_status = "refunded"
    else:
        booking.payment_status = "partially_refunded"

    booking.updated_at = now
    db.add(booking)


def maybe_notify_refund_processed(
    db: Session,
    *,
    refund: Refund,
    payment: Payment,
    booking: Booking | None,
    now: datetime,
) -> None:
    if booking is None:
        return

    game = db.get(Game, booking.game_id)
    if game is None or game.game_type != "official":
        return

    force_action_null = (
        refund.refund_reason == "game_cancelled"
        or not game_allows_inbox_action(game)
    )
    create_or_reopen_booking_refunded_notification(
        db,
        db_game=game,
        booking=booking,
        payment=payment,
        refund=refund,
        now=now,
        stripe_refund_processed=True,
        credit_restored=False,
        game_cancelled=refund.refund_reason == "game_cancelled",
        force_action_null=force_action_null,
    )


def build_retry_support_flag_metadata(refund_status: str) -> dict[str, Any]:
    return {
        "operation": "admin_money_refund_retry",
        "refund_status": refund_status,
    }


def stage_retry_follow_up_flag(
    db: Session,
    *,
    refund: Refund,
    payment: Payment,
    booking: Booking | None,
    admin_user: User,
    admin_action: AdminAction,
) -> None:
    if refund.refund_status == "processing":
        flag_type = "refund_follow_up_required"
        title = "Refund retry still processing"
        summary = (
            "A money-support refund retry was sent to Stripe, but the refund "
            "has not finalized yet."
        )
        severity = "attention"
        idempotency_status = "processing"
    elif refund.refund_status in {"failed", "cancelled"}:
        flag_type = "stripe_refund_failed"
        title = "Refund retry failed"
        summary = "A money-support refund retry did not complete in Stripe."
        severity = "urgent"
        idempotency_status = "failed"
    else:
        return

    stage_support_flag(
        db,
        flag_type=flag_type,
        source="stripe",
        title=title,
        summary=summary,
        severity=severity,
        metadata=build_retry_support_flag_metadata(refund.refund_status),
        idempotency_key=(
            f"admin_money_refund_retry:{refund.id}:{idempotency_status}"
        ),
        source_admin_action_id=admin_action.id,
        created_by_user_id=admin_user.id,
        reopen_resolved=True,
        target_user_id=payment.payer_user_id,
        target_game_id=payment.game_id or (booking.game_id if booking else None),
        target_booking_id=booking.id if booking else refund.booking_id,
        target_payment_id=payment.id,
        target_refund_id=refund.id,
        target_game_credit_id=None,
        target_venue_id=None,
        target_venue_image_id=None,
        target_notification_id=None,
    )


def apply_refund_retry_result(
    db: Session,
    *,
    refund: Refund,
    payment: Payment,
    booking: Booking | None,
    admin_user: User,
    reason: str,
    idempotency_key: str,
    provider_refund_id: str | None,
    refund_status: str,
    now: datetime,
) -> None:
    before_snapshot = refund_audit_snapshot(refund)

    if provider_refund_id is not None:
        refund.provider_refund_id = provider_refund_id
    refund.refund_status = refund_status
    if refund.requested_by_user_id is None:
        refund.requested_by_user_id = admin_user.id
    refund.approved_by_user_id = admin_user.id
    if refund_status in {"approved", "processing", "succeeded"}:
        refund.approved_at = refund.approved_at or now
    refund.refunded_at = now if refund_status == "succeeded" else None
    refund.updated_at = now
    db.add(refund)

    if refund_status == "succeeded":
        sync_refunded_payment_state(
            db,
            payment=payment,
            refund=refund,
            booking=booking,
            now=now,
        )
        maybe_notify_refund_processed(
            db,
            refund=refund,
            payment=payment,
            booking=booking,
            now=now,
        )

    admin_action = record_admin_action(
        db,
        admin_user_id=admin_user.id,
        action_type="update_refund",
        target_user_id=payment.payer_user_id,
        target_booking_id=refund.booking_id or payment.booking_id,
        target_participant_id=refund.participant_id,
        target_payment_id=payment.id,
        target_refund_id=refund.id,
        reason=reason,
        idempotency_key=idempotency_key,
        metadata=refund_audit_metadata(
            refund,
            source="admin_money_refund_retry",
            before=before_snapshot,
        ),
    )
    stage_retry_follow_up_flag(
        db,
        refund=refund,
        payment=payment,
        booking=booking,
        admin_user=admin_user,
        admin_action=admin_action,
    )


def call_stripe_refund_retry(
    *,
    refund: Refund,
    payment: Payment,
    admin_user: User,
    idempotency_key: str,
) -> StripeRefundResult:
    if payment.provider_charge_id is None:
        raise AssertionError("validated payment is missing provider_charge_id")

    return create_stripe_refund(
        charge_id=payment.provider_charge_id,
        amount_cents=refund.amount_cents,
        currency=refund.currency,
        idempotency_key=idempotency_key,
        metadata={
            "source": "admin_money_refund_retry",
            "payment_id": str(payment.id),
            "refund_id": str(refund.id),
            "admin_user_id": str(admin_user.id),
        },
    )


def retry_admin_money_refund(
    db: Session,
    *,
    admin_user: User,
    refund_id: uuid.UUID,
    payload: AdminMoneyRefundRetryCreate,
) -> AdminMoneyRefundDetailRead:
    reason = normalize_retry_reason(payload.reason)
    idempotency_key = normalize_retry_idempotency_key(payload.idempotency_key)

    existing_retry_action = get_existing_retry_action(
        db,
        admin_user_id=admin_user.id,
        refund_id=refund_id,
        idempotency_key=idempotency_key,
    )
    if existing_retry_action is not None:
        return get_admin_money_refund_detail(
            db,
            refund_id=refund_id,
            viewer_user=admin_user,
        )

    refund = get_refund_for_retry_or_404(db, refund_id)
    existing_retry_action = get_existing_retry_action(
        db,
        admin_user_id=admin_user.id,
        refund_id=refund_id,
        idempotency_key=idempotency_key,
    )
    if existing_retry_action is not None:
        return get_admin_money_refund_detail(
            db,
            refund_id=refund_id,
            viewer_user=admin_user,
        )

    payment = get_payment_for_retry_or_404(db, refund.payment_id)
    booking = get_booking_for_retry(
        db,
        refund.booking_id or payment.booking_id,
    )
    validate_refund_retry(db, refund=refund, payment=payment)

    try:
        provider_refund = call_stripe_refund_retry(
            refund=refund,
            payment=payment,
            admin_user=admin_user,
            idempotency_key=idempotency_key,
        )
        provider_refund_id = provider_refund.id
        refund_status = map_admin_money_retry_refund_status(provider_refund.status)
    except StripeConfigError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe refunds are not configured.",
        ) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Stripe refund retry could not be completed.",
        ) from exc

    now = datetime.now(timezone.utc)
    try:
        apply_refund_retry_result(
            db,
            refund=refund,
            payment=payment,
            booking=booking,
            admin_user=admin_user,
            reason=reason,
            idempotency_key=idempotency_key,
            provider_refund_id=provider_refund_id,
            refund_status=refund_status,
            now=now,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_refund_conflict_detail(exc),
        ) from exc

    return get_admin_money_refund_detail(
        db,
        refund_id=refund_id,
        viewer_user=admin_user,
    )
