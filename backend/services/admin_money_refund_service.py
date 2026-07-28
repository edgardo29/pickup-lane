"""Admin money refund retry and reconciliation workflows."""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    AdminAction,
    Booking,
    Game,
    HostPublishFee,
    MoneyIssue,
    Payment,
    Refund,
    RefundEvent,
    User,
)
from backend.schemas.admin_money_refund_schema import (
    AdminMoneyRefundDetailRead,
    AdminMoneyRefundReconcileCreate,
    AdminMoneyRefundRetryCreate,
)
from backend.services.admin_action_service import (
    build_admin_action_conflict_detail,
    record_admin_action,
)
from backend.services.admin_money_issue_service import (
    append_money_issue_event,
    stage_refund_money_issue,
)
from backend.services.admin_money_issue_query_service import list_related_money_issues
from backend.services.admin_money_refund_query_service import (
    get_admin_money_refund_detail,
)
from backend.services.admin_money_refund_rules import (
    REFUND_PROCESSING_OVERDUE_AFTER,
    RETRYABLE_PAYMENT_STATUSES,
    RETRYABLE_REFUND_STATUSES,
    UNCERTAIN_PROVIDER_REFUND_STATUSES,
    map_admin_money_retry_refund_status,
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
    build_refund_conflict_detail,
    refund_audit_metadata,
    refund_audit_snapshot,
    validate_refund_amount_available,
)
from backend.services.refund_event_service import record_refund_event
from backend.services.stripe_service import (
    StripeConfigError,
    StripeRefundResult,
    create_refund as create_stripe_refund,
    retrieve_refund as retrieve_stripe_refund,
)


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


def get_existing_reconcile_action(
    db: Session,
    *,
    admin_user_id: uuid.UUID,
    refund_id: uuid.UUID,
    idempotency_key: str,
) -> AdminAction | None:
    return db.scalars(
        select(AdminAction)
        .where(
            AdminAction.admin_user_id == admin_user_id,
            AdminAction.action_type == "reconcile_refund",
            AdminAction.target_refund_id == refund_id,
            AdminAction.idempotency_key == idempotency_key,
        )
        .order_by(AdminAction.created_at.desc(), AdminAction.id.desc())
    ).first()


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


def get_host_publish_fee_for_retry(
    db: Session,
    host_publish_fee_id: uuid.UUID | None,
) -> HostPublishFee | None:
    if host_publish_fee_id is None:
        return None

    return db.scalars(
        select(HostPublishFee)
        .where(HostPublishFee.id == host_publish_fee_id)
        .with_for_update()
    ).first()


def get_refund_processing_started_at(db: Session, refund: Refund) -> datetime:
    first_processing_event_at = db.scalar(
        select(func.min(RefundEvent.occurred_at)).where(
            RefundEvent.refund_id == refund.id,
            or_(
                RefundEvent.provider_status == "processing",
                RefundEvent.new_refund_status == "processing",
            ),
        )
    )
    return (
        first_processing_event_at
        or refund.approved_at
        or refund.requested_at
        or refund.created_at
    )


def refund_processing_threshold_reached(
    db: Session,
    *,
    refund: Refund,
    now: datetime,
) -> bool:
    processing_started_at = get_refund_processing_started_at(db, refund)
    return processing_started_at <= now - REFUND_PROCESSING_OVERDUE_AFTER


def validate_refund_retry(
    db: Session,
    *,
    refund: Refund,
    payment: Payment,
    host_publish_fee: HostPublishFee | None,
) -> None:
    if refund.refund_status not in RETRYABLE_REFUND_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only failed or cancelled refunds can be retried.",
        )

    if refund.provider_status in UNCERTAIN_PROVIDER_REFUND_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Refund provider outcome is still uncertain. "
                "Check provider status before retrying."
            ),
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

    if refund.host_publish_fee_id is not None:
        if host_publish_fee is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refund retry requires a host publish fee.",
            )

        if payment.payment_type != "community_publish_fee":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refund retry requires a community publish fee payment.",
            )

        if host_publish_fee.payment_id != payment.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Host publish fee payment must match the refund payment.",
            )

        if host_publish_fee.host_user_id != payment.payer_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Host publish fee payment must use the host as payer.",
            )
    elif payment.booking_id is None:
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
    excluding_refund_id: uuid.UUID | None = None,
) -> int:
    statement = select(func.coalesce(func.sum(Refund.amount_cents), 0)).where(
        Refund.payment_id == payment_id,
        Refund.refund_status == "succeeded",
    )
    if excluding_refund_id is not None:
        statement = statement.where(Refund.id != excluding_refund_id)

    return db.scalar(statement) or 0


def sync_refunded_payment_state(
    db: Session,
    *,
    payment: Payment,
    refund: Refund,
    booking: Booking | None,
    host_publish_fee: HostPublishFee | None = None,
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
    if host_publish_fee is not None and succeeded_total >= payment.amount_cents:
        host_publish_fee.fee_status = "refunded"
        host_publish_fee.updated_at = now
        db.add(host_publish_fee)

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
        if booking_payment.payment_status == "succeeded"
    ]

    if refundable_booking_payments and all(
        sum_succeeded_refunds_for_payment(db, payment_id=booking_payment.id)
        >= booking_payment.amount_cents
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


def apply_refund_retry_result(
    db: Session,
    *,
    refund: Refund,
    payment: Payment,
    booking: Booking | None,
    host_publish_fee: HostPublishFee | None,
    admin_action: AdminAction,
    before_snapshot: dict,
    admin_user: User,
    reason: str,
    provider_refund_id: str | None,
    refund_status: str,
    now: datetime,
) -> None:
    if refund.requested_by_user_id is None:
        refund.requested_by_user_id = admin_user.id
    refund.approved_by_user_id = admin_user.id
    db.add(refund)

    existing_open_issues = list_related_money_issues(
        db,
        refund_id=refund.id,
        status_filter="open",
        limit=5,
    )
    for money_issue in existing_open_issues:
        append_money_issue_event(
            db,
            money_issue=money_issue,
            event_type="admin_retry_initiated",
            event_source="admin",
            actor_user_id=admin_user.id,
            admin_action_id=admin_action.id,
            reason_code="admin_retry_initiated",
            summary=reason,
        )

    refund_event = record_refund_event(
        db,
        refund=refund,
        event_type="provider_result_recorded",
        event_source="admin",
        actor_user_id=admin_user.id,
        admin_action_id=admin_action.id,
        provider=refund.provider,
        provider_refund_id=provider_refund_id,
        provider_charge_id=payment.provider_charge_id,
        provider_status=refund_status,
        new_refund_status=refund_status,
        reason_code=f"admin_retry_{refund_status}",
        summary="Admin refund retry provider result recorded.",
        occurred_at=now,
    )
    admin_action.metadata_ = refund_audit_metadata(
        refund,
        source="admin_money_refund_retry",
        before=before_snapshot,
    )
    db.add(admin_action)

    if refund_status == "succeeded":
        for money_issue in existing_open_issues:
            previous_action = money_issue.recommended_action_code
            money_issue.latest_reason_code = "admin_retry_succeeded"
            money_issue.latest_summary = "Admin refund retry succeeded."
            money_issue.recommended_action_code = "review_and_resolve_no_action"
            money_issue.updated_at = now
            append_money_issue_event(
                db,
                money_issue=money_issue,
                event_type="refund_outcome_linked",
                event_source="admin",
                actor_user_id=admin_user.id,
                admin_action_id=admin_action.id,
                refund_event_id=refund_event.id,
                reason_code="admin_retry_succeeded",
                summary="Admin refund retry succeeded.",
                previous_recommended_action_code=previous_action,
                new_recommended_action_code=money_issue.recommended_action_code,
            )
        sync_refunded_payment_state(
            db,
            payment=payment,
            refund=refund,
            booking=booking,
            host_publish_fee=host_publish_fee,
            now=now,
        )
        maybe_notify_refund_processed(
            db,
            refund=refund,
            payment=payment,
            booking=booking,
            now=now,
        )
    elif refund_status in {"failed", "cancelled"}:
        stage_refund_money_issue(
            db,
            refund=refund,
            payment=payment,
            issue_type="refund_failed"
            if refund_status == "failed"
            else "refund_cancelled",
            reason_code=f"admin_retry_{refund_status}",
            summary="A refund retry did not complete with the provider.",
            refund_event=refund_event,
            admin_action=admin_action,
            now=now,
        )
    else:
        for money_issue in existing_open_issues:
            previous_action = money_issue.recommended_action_code
            money_issue.latest_reason_code = "admin_retry_processing"
            money_issue.latest_summary = "Admin refund retry returned processing."
            money_issue.recommended_action_code = "verify_provider_refund"
            money_issue.updated_at = now
            append_money_issue_event(
                db,
                money_issue=money_issue,
                event_type="refund_outcome_linked",
                event_source="admin",
                actor_user_id=admin_user.id,
                admin_action_id=admin_action.id,
                refund_event_id=refund_event.id,
                reason_code="admin_retry_processing",
                summary="Admin refund retry returned processing.",
                previous_recommended_action_code=previous_action,
                new_recommended_action_code=money_issue.recommended_action_code,
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
    host_publish_fee = get_host_publish_fee_for_retry(
        db,
        refund.host_publish_fee_id,
    )
    validate_refund_retry(
        db,
        refund=refund,
        payment=payment,
        host_publish_fee=host_publish_fee,
    )
    before_snapshot = refund_audit_snapshot(refund)
    try:
        admin_action = record_admin_action(
            db,
            admin_user_id=admin_user.id,
            action_type="update_refund",
            target_user_id=payment.payer_user_id,
            target_booking_id=refund.booking_id or payment.booking_id,
            target_participant_id=refund.participant_id,
            target_payment_id=payment.id,
            target_refund_id=refund.id,
            target_host_publish_fee_id=refund.host_publish_fee_id,
            reason=reason,
            idempotency_key=idempotency_key,
            metadata=refund_audit_metadata(
                refund,
                source="admin_money_refund_retry",
            ),
        )
        db.flush()
    except IntegrityError as exc:
        db.rollback()
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
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_admin_action_conflict_detail(exc),
        ) from exc

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
            host_publish_fee=host_publish_fee,
            admin_action=admin_action,
            before_snapshot=before_snapshot,
            admin_user=admin_user,
            reason=reason,
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


def stage_refund_issue_for_terminal_or_unknown(
    db: Session,
    *,
    refund: Refund,
    payment: Payment,
    refund_event,
    reason_code: str,
    summary: str,
    now: datetime,
) -> None:
    if refund.refund_status == "failed":
        issue_type = (
            "refund_missing_provider_reference"
            if reason_code in {"provider_charge_id_missing", "missing_provider_refund_id"}
            else "refund_failed"
        )
    elif refund.refund_status == "cancelled":
        issue_type = "refund_cancelled"
    else:
        issue_type = "refund_outcome_unknown"

    stage_refund_money_issue(
        db,
        refund=refund,
        payment=payment,
        issue_type=issue_type,
        reason_code=reason_code,
        summary=summary,
        refund_event=refund_event,
        now=now,
    )


def link_reconciliation_to_open_issues(
    db: Session,
    *,
    refund: Refund,
    refund_event,
    admin_action: AdminAction,
    admin_user: User,
    reason_code: str,
    summary: str,
    recommended_action_code: str,
    now: datetime,
) -> None:
    for money_issue in list_related_money_issues(
        db,
        refund_id=refund.id,
        status_filter="open",
        limit=10,
    ):
        previous_action = money_issue.recommended_action_code
        money_issue.latest_reason_code = reason_code
        money_issue.latest_summary = summary
        money_issue.recommended_action_code = recommended_action_code
        money_issue.updated_at = now
        append_money_issue_event(
            db,
            money_issue=money_issue,
            event_type="refund_outcome_linked",
            event_source="admin",
            actor_user_id=admin_user.id,
            admin_action_id=admin_action.id,
            refund_event_id=refund_event.id,
            reason_code=reason_code,
            summary=summary,
            previous_recommended_action_code=previous_action,
            new_recommended_action_code=recommended_action_code,
            occurred_at=now,
        )


def reconcile_admin_money_refund(
    db: Session,
    *,
    admin_user: User,
    refund_id: uuid.UUID,
    payload: AdminMoneyRefundReconcileCreate,
) -> AdminMoneyRefundDetailRead:
    reason = normalize_retry_reason(payload.reason)
    idempotency_key = normalize_retry_idempotency_key(payload.idempotency_key)
    existing_action = get_existing_reconcile_action(
        db,
        admin_user_id=admin_user.id,
        refund_id=refund_id,
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        return get_admin_money_refund_detail(
            db,
            refund_id=refund_id,
            viewer_user=admin_user,
        )

    refund = get_refund_for_retry_or_404(db, refund_id)
    payment = get_payment_for_retry_or_404(db, refund.payment_id)
    booking = get_booking_for_retry(db, refund.booking_id or payment.booking_id)
    host_publish_fee = get_host_publish_fee_for_retry(db, refund.host_publish_fee_id)
    if refund.refund_status == "succeeded":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Succeeded refunds do not need provider reconciliation.",
        )

    now = datetime.now(timezone.utc)
    try:
        admin_action = record_admin_action(
            db,
            admin_user_id=admin_user.id,
            action_type="reconcile_refund",
            target_user_id=payment.payer_user_id,
            target_booking_id=refund.booking_id or payment.booking_id,
            target_participant_id=refund.participant_id,
            target_payment_id=payment.id,
            target_refund_id=refund.id,
            target_host_publish_fee_id=refund.host_publish_fee_id,
            reason=reason,
            idempotency_key=idempotency_key,
            metadata={
                "source": "admin_money_refund_reconcile",
                "refund_status": refund.refund_status,
            },
        )
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        existing_action = get_existing_reconcile_action(
            db,
            admin_user_id=admin_user.id,
            refund_id=refund_id,
            idempotency_key=idempotency_key,
        )
        if existing_action is not None:
            return get_admin_money_refund_detail(
                db,
                refund_id=refund_id,
                viewer_user=admin_user,
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_admin_action_conflict_detail(exc),
        ) from exc
    if refund.provider_refund_id is None:
        refund_event = record_refund_event(
            db,
            refund=refund,
            event_type="provider_outcome_unknown",
            event_source="reconciliation",
            actor_user_id=admin_user.id,
            admin_action_id=admin_action.id,
            provider=refund.provider,
            provider_refund_id=None,
            provider_charge_id=refund.provider_charge_id or payment.provider_charge_id,
            provider_status="unknown",
            new_refund_status="failed",
            reason_code="missing_provider_refund_id",
            summary="Provider status could not be checked because the refund has no provider refund id.",
            occurred_at=now,
        )
        stage_refund_issue_for_terminal_or_unknown(
            db,
            refund=refund,
            payment=payment,
            refund_event=refund_event,
            reason_code="missing_provider_refund_id",
            summary="Refund provider reference is missing.",
            now=now,
        )
        db.commit()
        return get_admin_money_refund_detail(
            db,
            refund_id=refund_id,
            viewer_user=admin_user,
        )

    try:
        provider_refund = retrieve_stripe_refund(refund.provider_refund_id)
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
            detail="Stripe refund status could not be checked.",
        ) from exc

    refund_status = map_admin_money_retry_refund_status(provider_refund.status)
    processing_threshold_reached = (
        refund_status == "processing"
        and refund_processing_threshold_reached(db, refund=refund, now=now)
    )
    processing_overdue_summary = (
        "Provider still reports the refund as processing after the "
        "configured threshold."
    )
    refund_event = record_refund_event(
        db,
        refund=refund,
        event_type=(
            "provider_result_recorded"
            if refund_status in {"succeeded", "failed", "cancelled"}
            else "reconciliation_checked"
        ),
        event_source="reconciliation",
        actor_user_id=admin_user.id,
        admin_action_id=admin_action.id,
        provider=refund.provider,
        provider_refund_id=provider_refund.id,
        provider_charge_id=provider_refund.charge_id or payment.provider_charge_id,
        provider_status=refund_status,
        new_refund_status=refund_status,
        reason_code=(
            "processing_threshold_reached"
            if processing_threshold_reached
            else f"provider_reconciliation_{refund_status}"
        ),
        summary=(
            processing_overdue_summary
            if processing_threshold_reached
            else "Provider refund status checked."
        ),
        occurred_at=now,
    )
    if refund_status == "succeeded":
        sync_refunded_payment_state(
            db,
            payment=payment,
            refund=refund,
            booking=booking,
            host_publish_fee=host_publish_fee,
            now=now,
        )
        maybe_notify_refund_processed(
            db,
            refund=refund,
            payment=payment,
            booking=booking,
            now=now,
        )
        link_reconciliation_to_open_issues(
            db,
            refund=refund,
            refund_event=refund_event,
            admin_action=admin_action,
            admin_user=admin_user,
            reason_code="provider_reconciliation_succeeded",
            summary="Provider confirmed the refund succeeded.",
            recommended_action_code="review_and_resolve_no_action",
            now=now,
        )
    elif refund_status in {"failed", "cancelled"}:
        stage_refund_issue_for_terminal_or_unknown(
            db,
            refund=refund,
            payment=payment,
            refund_event=refund_event,
            reason_code=f"provider_reconciliation_{refund_status}",
            summary="Provider confirmed the refund did not complete.",
            now=now,
        )
    elif processing_threshold_reached:
        stage_refund_money_issue(
            db,
            refund=refund,
            payment=payment,
            issue_type="refund_processing_overdue",
            reason_code="processing_threshold_reached",
            summary=processing_overdue_summary,
            refund_event=refund_event,
            admin_action=admin_action,
            now=now,
        )
    else:
        link_reconciliation_to_open_issues(
            db,
            refund=refund,
            refund_event=refund_event,
            admin_action=admin_action,
            admin_user=admin_user,
            reason_code="provider_reconciliation_processing",
            summary="Provider still reports the refund as processing.",
            recommended_action_code="verify_provider_refund",
            now=now,
        )

    try:
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
