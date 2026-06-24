"""Admin money refund reads and retry workflows."""

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    AdminAction,
    Booking,
    Game,
    GameCredit,
    Payment,
    Refund,
    SupportFlag,
    User,
)
from backend.schemas.admin_money_schema import (
    AdminMoneyRefundDetailRead,
    AdminMoneyRefundRetryCreate,
)
from backend.services.admin_action_service import (
    record_admin_action,
    user_can_read_admin_action,
)
from backend.services.admin_money_payment_service import (
    get_payment_game,
    list_payment_credit_grants,
    list_payment_credit_usages,
)
from backend.services.admin_money_support_flag_read_service import (
    MONEY_SUPPORT_FLAG_TYPES,
)
from backend.services.admin_permission_service import (
    PERMISSION_AUDIT_READ,
    user_has_admin_permission,
)
from backend.services.admin_record_rules import (
    normalize_idempotency_key,
    normalize_optional_text,
)
from backend.services.game_notification_service import (
    create_or_reopen_booking_refunded_notification,
    game_allows_inbox_action,
)
from backend.services.refund_service import (
    VALID_REFUND_STATUSES,
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
from backend.services.support_flag_service import (
    stage_support_flag,
    user_can_read_support_flag,
)

ADMIN_MONEY_DETAIL_RELATED_LIMIT = 100
ADMIN_MONEY_REFUND_STATUSES = VALID_REFUND_STATUSES | {"all"}
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


def get_refund_or_404(db: Session, refund_id: uuid.UUID) -> Refund:
    refund = db.get(Refund, refund_id)
    if refund is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found.",
        )
    return refund


def validate_admin_money_refund_status(refund_status: str) -> None:
    if refund_status not in ADMIN_MONEY_REFUND_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="refund_status is not supported.",
        )


def list_admin_money_refunds(
    db: Session,
    *,
    user_id: uuid.UUID | None = None,
    refund_status: str = "all",
    payment_id: uuid.UUID | None = None,
    booking_id: uuid.UUID | None = None,
    game_id: uuid.UUID | None = None,
    limit: int = 100,
) -> list[Refund]:
    validate_admin_money_refund_status(refund_status)

    query = select(Refund).join(Payment, Refund.payment_id == Payment.id)
    if user_id is not None:
        query = query.where(Payment.payer_user_id == user_id)
    if refund_status != "all":
        query = query.where(Refund.refund_status == refund_status)
    if payment_id is not None:
        query = query.where(Refund.payment_id == payment_id)
    if booking_id is not None:
        query = query.where(
            or_(Refund.booking_id == booking_id, Payment.booking_id == booking_id)
        )
    if game_id is not None:
        query = query.outerjoin(
            Booking,
            or_(Refund.booking_id == Booking.id, Payment.booking_id == Booking.id),
        ).where(or_(Payment.game_id == game_id, Booking.game_id == game_id))

    return list(
        db.scalars(
            query.order_by(Refund.created_at.desc(), Refund.id.desc()).limit(limit)
        ).all()
    )


def get_refund_payment(db: Session, refund: Refund) -> Payment | None:
    return db.get(Payment, refund.payment_id)


def get_refund_booking(
    db: Session,
    *,
    refund: Refund,
    payment: Payment | None,
) -> Booking | None:
    booking_id = refund.booking_id or (
        payment.booking_id if payment is not None else None
    )
    if booking_id is None:
        return None
    return db.get(Booking, booking_id)


def list_refund_support_flags(
    db: Session,
    *,
    viewer_user: User,
    refund: Refund,
    payment: Payment | None,
    booking_id: uuid.UUID | None,
    credit_grants: list[GameCredit],
) -> list[SupportFlag]:
    filters = [SupportFlag.target_refund_id == refund.id]

    if payment is not None:
        filters.append(SupportFlag.target_payment_id == payment.id)

    if booking_id is not None:
        filters.append(SupportFlag.target_booking_id == booking_id)

    credit_ids = [credit.id for credit in credit_grants]
    if credit_ids:
        filters.append(SupportFlag.target_game_credit_id.in_(credit_ids))

    support_flags = db.scalars(
        select(SupportFlag)
        .where(
            SupportFlag.flag_type.in_(MONEY_SUPPORT_FLAG_TYPES),
            or_(*filters),
        )
        .order_by(SupportFlag.created_at.desc(), SupportFlag.id.desc())
        .limit(ADMIN_MONEY_DETAIL_RELATED_LIMIT)
    ).all()

    return [
        support_flag
        for support_flag in support_flags
        if user_can_read_support_flag(viewer_user, support_flag)
    ]


def list_refund_audit_actions(
    db: Session,
    *,
    viewer_user: User,
    refund: Refund,
    payment: Payment | None,
    booking_id: uuid.UUID | None,
    credit_grants: list[GameCredit],
    support_flags: list[SupportFlag],
) -> list[AdminAction]:
    if not user_has_admin_permission(viewer_user, PERMISSION_AUDIT_READ):
        return []

    filters = [AdminAction.target_refund_id == refund.id]

    if payment is not None:
        filters.append(AdminAction.target_payment_id == payment.id)

    if booking_id is not None:
        filters.append(AdminAction.target_booking_id == booking_id)

    credit_ids = [credit.id for credit in credit_grants]
    if credit_ids:
        filters.append(AdminAction.target_game_credit_id.in_(credit_ids))

    support_flag_ids = [support_flag.id for support_flag in support_flags]
    if support_flag_ids:
        filters.append(AdminAction.target_support_flag_id.in_(support_flag_ids))

    audit_actions = db.scalars(
        select(AdminAction)
        .where(or_(*filters))
        .order_by(AdminAction.created_at.desc(), AdminAction.id.desc())
        .limit(ADMIN_MONEY_DETAIL_RELATED_LIMIT)
    ).all()

    return [
        audit_action
        for audit_action in audit_actions
        if user_can_read_admin_action(viewer_user, audit_action)
    ]


def get_admin_money_refund_detail(
    db: Session,
    *,
    refund_id: uuid.UUID,
    viewer_user: User,
) -> AdminMoneyRefundDetailRead:
    refund = get_refund_or_404(db, refund_id)
    payment = get_refund_payment(db, refund)
    booking = get_refund_booking(db, refund=refund, payment=payment)
    game = (
        get_payment_game(db, payment=payment, booking=booking)
        if payment is not None
        else None
    )
    payment_id = payment.id if payment is not None else refund.payment_id
    booking_id = booking.id if booking is not None else refund.booking_id
    credit_usages = list_payment_credit_usages(
        db,
        payment_id=payment_id,
        booking_id=booking_id,
    )
    credit_grants = list_payment_credit_grants(
        db,
        payment_id=payment_id,
        booking_id=booking_id,
        credit_usages=credit_usages,
    )
    support_flags = list_refund_support_flags(
        db,
        viewer_user=viewer_user,
        refund=refund,
        payment=payment,
        booking_id=booking_id,
        credit_grants=credit_grants,
    )
    audit_actions = list_refund_audit_actions(
        db,
        viewer_user=viewer_user,
        refund=refund,
        payment=payment,
        booking_id=booking_id,
        credit_grants=credit_grants,
        support_flags=support_flags,
    )

    return AdminMoneyRefundDetailRead(
        refund=refund,
        payment=payment,
        booking=booking,
        game=game,
        credit_grants=credit_grants,
        credit_usages=credit_usages,
        support_flags=support_flags,
        audit_actions=audit_actions,
    )
