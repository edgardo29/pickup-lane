"""Admin money refund reads and retry workflows."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    AdminAction,
    Booking,
    Game,
    GameCredit,
    GameParticipant,
    HostPublishFee,
    MoneyIssue,
    Payment,
    Refund,
    RefundEvent,
    User,
)
from backend.schemas.admin_money_schema import (
    AdminMoneyAuditActionSummaryRead,
    AdminMoneyBookingContextRead,
    AdminMoneyGameContextRead,
    AdminMoneyHostPublishFeeContextRead,
    AdminMoneyParticipantContextRead,
    AdminMoneyPaymentUserContextRead,
    AdminMoneyRefundActionRead,
    AdminMoneyRefundCreditContextRead,
    AdminMoneyRefundDetailRead,
    AdminMoneyRefundDetailItemRead,
    AdminMoneyRefundEventListResponseRead,
    AdminMoneyRefundListRead,
    AdminMoneyRefundListResponseRead,
    AdminMoneyRefundProviderSnapshotRead,
    AdminMoneyRefundReconcileCreate,
    AdminMoneyRefundRetryCreate,
)
from backend.services.admin_action_service import (
    build_admin_action_conflict_detail,
    record_admin_action,
    user_can_read_admin_action,
)
from backend.services.admin_money_cursor import (
    apply_desc_cursor,
    next_cursor_for_rows,
    page_has_more,
)
from backend.services.admin_money_display import admin_money_display, compact_id
from backend.services.admin_money_payment_service import (
    build_payment_summary,
    get_payment_game,
    load_by_id,
    list_payment_credit_grants,
    list_payment_credit_usages,
)
from backend.services.admin_money_issue_service import (
    append_money_issue_event,
    list_related_money_issues,
    stage_refund_money_issue,
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
from backend.services.refund_event_service import record_refund_event
from backend.services.stripe_service import (
    StripeConfigError,
    StripeRefundResult,
    create_refund as create_stripe_refund,
    retrieve_refund as retrieve_stripe_refund,
)

ADMIN_MONEY_DETAIL_RELATED_LIMIT = 100
ADMIN_MONEY_REFUND_STATUSES = VALID_REFUND_STATUSES | {"all"}
RETRYABLE_REFUND_STATUSES = {"failed", "cancelled"}
RETRYABLE_PAYMENT_STATUSES = {"succeeded"}
UNCERTAIN_PROVIDER_REFUND_STATUSES = {"processing", "unknown"}
REFUND_PROCESSING_OVERDUE_AFTER = timedelta(hours=24)


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


def get_refund_or_404(db: Session, refund_id: uuid.UUID) -> Refund:
    refund = db.get(Refund, refund_id)
    if refund is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found.",
        )
    return refund


def build_refund_summary(db: Session, refund: Refund) -> AdminMoneyRefundListRead:
    payment = db.get(Payment, refund.payment_id)
    booking = get_refund_booking(db, refund=refund, payment=payment)
    game = (
        get_payment_game(db, payment=payment, booking=booking)
        if payment is not None
        else None
    )
    payer = db.get(User, payment.payer_user_id) if payment is not None else None
    linked_issues = list_related_money_issues(
        db,
        refund_id=refund.id,
        status_filter="open",
        limit=1,
    )
    context_label = None
    if booking is not None:
        context_label = f"Booking {compact_id(booking.id)}"
    elif refund.host_publish_fee_id is not None:
        context_label = f"Publish fee {compact_id(refund.host_publish_fee_id)}"

    return AdminMoneyRefundListRead(
        id=refund.id,
        payment_id=refund.payment_id,
        booking_id=refund.booking_id,
        participant_id=refund.participant_id,
        host_publish_fee_id=refund.host_publish_fee_id,
        game_id=game.id if game is not None else None,
        target_user_id=payment.payer_user_id if payment is not None else None,
        origin_workflow=refund.origin_workflow,
        provider=refund.provider,
        provider_refund_id=refund.provider_refund_id,
        provider_charge_id=refund.provider_charge_id,
        provider_status=refund.provider_status,
        provider_status_observed_at=refund.provider_status_observed_at,
        amount_cents=refund.amount_cents,
        currency=refund.currency,
        refund_reason=refund.refund_reason,
        refund_status=refund.refund_status,
        requested_by_user_id=refund.requested_by_user_id,
        approved_by_user_id=refund.approved_by_user_id,
        requested_at=refund.requested_at,
        approved_at=refund.approved_at,
        refunded_at=refund.refunded_at,
        last_refund_event_at=refund.last_refund_event_at,
        linked_issue=linked_issues[0] if linked_issues else None,
        display=admin_money_display(
            user=payer,
            game=game,
            context_label=context_label,
            payment_id=refund.payment_id,
            refund_id=refund.id,
        ),
        created_at=refund.created_at,
        updated_at=refund.updated_at,
    )


def build_refund_summary_from_context(
    refund: Refund,
    *,
    payment: Payment | None,
    booking: Booking | None,
    game: Game | None,
    payer: User | None,
    linked_issue: MoneyIssue | None,
) -> AdminMoneyRefundListRead:
    context_label = None
    if booking is not None:
        context_label = f"Booking {compact_id(booking.id)}"
    elif refund.host_publish_fee_id is not None:
        context_label = f"Publish fee {compact_id(refund.host_publish_fee_id)}"

    return AdminMoneyRefundListRead(
        id=refund.id,
        payment_id=refund.payment_id,
        booking_id=refund.booking_id,
        participant_id=refund.participant_id,
        host_publish_fee_id=refund.host_publish_fee_id,
        game_id=game.id if game is not None else None,
        target_user_id=payment.payer_user_id if payment is not None else None,
        origin_workflow=refund.origin_workflow,
        provider=refund.provider,
        provider_refund_id=refund.provider_refund_id,
        provider_charge_id=refund.provider_charge_id,
        provider_status=refund.provider_status,
        provider_status_observed_at=refund.provider_status_observed_at,
        amount_cents=refund.amount_cents,
        currency=refund.currency,
        refund_reason=refund.refund_reason,
        refund_status=refund.refund_status,
        requested_by_user_id=refund.requested_by_user_id,
        approved_by_user_id=refund.approved_by_user_id,
        requested_at=refund.requested_at,
        approved_at=refund.approved_at,
        refunded_at=refund.refunded_at,
        last_refund_event_at=refund.last_refund_event_at,
        linked_issue=linked_issue,
        display=admin_money_display(
            user=payer,
            game=game,
            context_label=context_label,
            payment_id=refund.payment_id,
            refund_id=refund.id,
        ),
        created_at=refund.created_at,
        updated_at=refund.updated_at,
    )


def build_refund_summaries(
    db: Session,
    refunds: list[Refund],
    *,
    linked_issue_status: str | None = "open",
) -> list[AdminMoneyRefundListRead]:
    if not refunds:
        return []
    refund_ids = {refund.id for refund in refunds}
    payment_ids = {refund.payment_id for refund in refunds}
    payments = load_by_id(db, Payment, payment_ids)
    booking_ids = {
        refund.booking_id for refund in refunds if refund.booking_id is not None
    }
    booking_ids.update(
        payment.booking_id
        for payment in payments.values()
        if payment is not None and payment.booking_id is not None
    )
    bookings = load_by_id(db, Booking, booking_ids)
    payer_ids = {
        payment.payer_user_id
        for payment in payments.values()
        if payment is not None
    }
    users = load_by_id(db, User, payer_ids)
    game_ids = {
        payment.game_id
        for payment in payments.values()
        if payment is not None and payment.game_id is not None
    }
    game_ids.update(
        booking.game_id for booking in bookings.values() if booking is not None
    )
    games = load_by_id(db, Game, game_ids)

    linked_issue_by_refund_id: dict[uuid.UUID, MoneyIssue] = {}
    issue_statement = select(MoneyIssue).where(
        MoneyIssue.target_refund_id.in_(refund_ids)
    )
    if linked_issue_status is not None:
        issue_statement = issue_statement.where(MoneyIssue.status == linked_issue_status)
    issue_rows = list(
        db.scalars(
            issue_statement.order_by(
                MoneyIssue.last_activity_at.desc(),
                MoneyIssue.id.desc(),
            )
        ).all()
    )
    for issue in issue_rows:
        if (
            issue.target_refund_id is not None
            and issue.target_refund_id not in linked_issue_by_refund_id
        ):
            linked_issue_by_refund_id[issue.target_refund_id] = issue

    summaries = []
    for refund in refunds:
        payment = payments.get(refund.payment_id)
        booking_id = refund.booking_id or (
            payment.booking_id if payment is not None else None
        )
        booking = bookings.get(booking_id) if booking_id is not None else None
        game_id = (
            payment.game_id
            if payment is not None and payment.game_id is not None
            else (booking.game_id if booking is not None else None)
        )
        payer = users.get(payment.payer_user_id) if payment is not None else None
        summaries.append(
            build_refund_summary_from_context(
                refund,
                payment=payment,
                booking=booking,
                game=games.get(game_id) if game_id is not None else None,
                payer=payer,
                linked_issue=linked_issue_by_refund_id.get(refund.id),
            )
        )
    return summaries


def validate_admin_money_refund_status(refund_status: str) -> None:
    if refund_status not in ADMIN_MONEY_REFUND_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="refund_status is not supported.",
        )


def parse_refund_query_uuid(query_text: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(query_text)
    except (TypeError, ValueError):
        return None


def list_admin_money_refunds(
    db: Session,
    *,
    user_id: uuid.UUID | None = None,
    refund_status: str = "all",
    payment_id: uuid.UUID | None = None,
    query_text: str | None = None,
    limit: int = 50,
    cursor: str | None = None,
) -> AdminMoneyRefundListResponseRead:
    validate_admin_money_refund_status(refund_status)

    query = (
        select(Refund)
        .join(Payment, Refund.payment_id == Payment.id)
        .outerjoin(
            Booking,
            Booking.id == func.coalesce(Refund.booking_id, Payment.booking_id),
        )
        .outerjoin(User, Payment.payer_user_id == User.id)
    )
    if user_id is not None:
        query = query.where(Payment.payer_user_id == user_id)
    if refund_status != "all":
        query = query.where(Refund.refund_status == refund_status)
    if payment_id is not None:
        query = query.where(Refund.payment_id == payment_id)

    normalized_query = " ".join((query_text or "").strip().split())
    if normalized_query:
        query_uuid = parse_refund_query_uuid(normalized_query)
        text_filters = []
        if query_uuid is not None:
            text_filters.extend(
                [
                    Refund.id == query_uuid,
                    Refund.payment_id == query_uuid,
                    Refund.booking_id == query_uuid,
                    Refund.participant_id == query_uuid,
                    Refund.host_publish_fee_id == query_uuid,
                    Payment.payer_user_id == query_uuid,
                    Payment.booking_id == query_uuid,
                ]
            )
        elif normalized_query.startswith("re_"):
            text_filters.append(Refund.provider_refund_id == normalized_query)
        elif normalized_query.startswith("ch_"):
            text_filters.extend(
                [
                    Refund.provider_charge_id == normalized_query,
                    Payment.provider_charge_id == normalized_query,
                ]
            )
        else:
            prefix_query = f"{normalized_query}%"
            text_filters.extend(
                [
                    User.email.ilike(prefix_query),
                    User.first_name.ilike(prefix_query),
                    User.last_name.ilike(prefix_query),
                ]
            )
            name_parts = normalized_query.split()
            if len(name_parts) >= 2:
                text_filters.append(
                    and_(
                        User.first_name.ilike(f"{name_parts[0]}%"),
                        User.last_name.ilike(f"{name_parts[-1]}%"),
                    )
                )
        query = query.where(or_(*text_filters))

    query = apply_desc_cursor(query, Refund, Refund.created_at, cursor)

    refunds = list(
        db.scalars(
            query.order_by(Refund.created_at.desc(), Refund.id.desc()).limit(limit + 1)
        ).all()
    )
    return AdminMoneyRefundListResponseRead(
        items=build_refund_summaries(
            db,
            refunds[:limit],
            linked_issue_status="open",
        ),
        has_more=page_has_more(refunds, limit=limit),
        next_cursor=next_cursor_for_rows(
            refunds,
            limit=limit,
            sort_attr="created_at",
        ),
    )


def list_refund_events(
    db: Session,
    refund_id: uuid.UUID,
    *,
    event_type: str | None = None,
    event_source: str | None = None,
    limit: int = 50,
    cursor: str | None = None,
) -> AdminMoneyRefundEventListResponseRead:
    if db.get(Refund, refund_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found.",
        )
    statement = select(RefundEvent).where(RefundEvent.refund_id == refund_id)
    if event_type is not None:
        statement = statement.where(RefundEvent.event_type == event_type)
    if event_source is not None:
        statement = statement.where(RefundEvent.event_source == event_source)
    statement = apply_desc_cursor(statement, RefundEvent, RefundEvent.occurred_at, cursor)
    rows = list(
        db.scalars(
            statement
            .order_by(RefundEvent.occurred_at.desc(), RefundEvent.id.desc())
            .limit(limit + 1)
        ).all()
    )
    return AdminMoneyRefundEventListResponseRead(
        items=rows[:limit],
        has_more=page_has_more(rows, limit=limit),
        next_cursor=next_cursor_for_rows(
            rows,
            limit=limit,
            sort_attr="occurred_at",
        ),
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


def get_refund_participant(db: Session, refund: Refund) -> GameParticipant | None:
    if refund.participant_id is None:
        return None
    return db.get(GameParticipant, refund.participant_id)


def get_refund_host_publish_fee(db: Session, refund: Refund) -> HostPublishFee | None:
    if refund.host_publish_fee_id is None:
        return None
    return db.get(HostPublishFee, refund.host_publish_fee_id)


def build_refund_provider_snapshot(refund: Refund) -> AdminMoneyRefundProviderSnapshotRead:
    return AdminMoneyRefundProviderSnapshotRead(
        provider=refund.provider,
        provider_status=refund.provider_status,
        provider_status_observed_at=refund.provider_status_observed_at,
        provider_refund_id=refund.provider_refund_id,
        provider_charge_id=refund.provider_charge_id,
    )


def list_refund_admin_activity(
    db: Session,
    *,
    viewer_user: User,
    refund: Refund,
    linked_money_issue: MoneyIssue | None,
) -> list[AdminAction]:
    filters = [AdminAction.target_refund_id == refund.id]
    if linked_money_issue is not None:
        filters.append(AdminAction.target_money_issue_id == linked_money_issue.id)

    actions = db.scalars(
        select(AdminAction)
        .where(or_(*filters))
        .order_by(AdminAction.created_at.desc(), AdminAction.id.desc())
        .limit(ADMIN_MONEY_DETAIL_RELATED_LIMIT)
    ).all()
    return [
        action
        for action in actions
        if user_can_read_admin_action(viewer_user, action)
    ]


def refund_available_actions(
    *,
    refund: Refund,
    payment: Payment | None,
    linked_money_issue: MoneyIssue | None = None,
) -> list[AdminMoneyRefundActionRead]:
    retry_blockers: list[str] = []
    if refund.refund_status not in RETRYABLE_REFUND_STATUSES:
        retry_blockers.append("Refund is not failed or cancelled.")
    if refund.provider_status in UNCERTAIN_PROVIDER_REFUND_STATUSES:
        retry_blockers.append("Refund provider outcome is still uncertain.")
    if payment is None:
        retry_blockers.append("Payment context is missing.")
    elif payment.payment_status not in RETRYABLE_PAYMENT_STATUSES:
        retry_blockers.append("Payment did not succeed.")
    elif payment.paid_at is None:
        retry_blockers.append("Payment was not marked paid.")
    elif not payment.provider_charge_id:
        retry_blockers.append("Payment is missing provider charge id.")

    check_provider_blockers: list[str] = []
    if refund.refund_status == "succeeded":
        check_provider_blockers.append("Refund already succeeded.")
    elif (
        refund.provider_refund_id
        or refund.provider_status in {"processing", "unknown"}
        or refund.refund_status == "processing"
    ):
        pass
    else:
        check_provider_blockers.append("Refund has no provider state that can be checked.")

    open_provider_blockers: list[str] = []
    if not refund.provider_refund_id:
        open_provider_blockers.append("Refund is missing provider refund id.")

    open_issue_blockers: list[str] = []
    if linked_money_issue is None:
        open_issue_blockers.append("No linked Money Issue exists.")

    return [
        AdminMoneyRefundActionRead(
            action_code="retry_refund",
            enabled=not retry_blockers,
            blockers=retry_blockers,
            confirmation_text="Retry this refund through Stripe.",
        ),
        AdminMoneyRefundActionRead(
            action_code="check_provider_status",
            enabled=not check_provider_blockers,
            blockers=check_provider_blockers,
            confirmation_text="Check Stripe for the latest refund status.",
        ),
        AdminMoneyRefundActionRead(
            action_code="open_provider_reference",
            enabled=not open_provider_blockers,
            blockers=open_provider_blockers,
            confirmation_text="Open the provider refund reference.",
        ),
        AdminMoneyRefundActionRead(
            action_code="open_money_issue",
            enabled=not open_issue_blockers,
            blockers=open_issue_blockers,
            confirmation_text="Open the linked Money Issue.",
        ),
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
    payer = db.get(User, payment.payer_user_id) if payment is not None else None
    participant = get_refund_participant(db, refund)
    host_publish_fee = get_refund_host_publish_fee(db, refund)
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
    linked_issues = list_related_money_issues(
        db,
        refund_id=refund.id,
        limit=1,
    )
    linked_money_issue = linked_issues[0] if linked_issues else None
    payment_summary = (
        build_payment_summary(db, payment, detail=True)
        if payment is not None
        else None
    )
    recent_refund_events = list_refund_events(
        db,
        refund.id,
        limit=ADMIN_MONEY_DETAIL_RELATED_LIMIT,
    ).items
    admin_activity = list_refund_admin_activity(
        db,
        viewer_user=viewer_user,
        refund=refund,
        linked_money_issue=linked_money_issue,
    )

    refund_summary = build_refund_summary(db, refund)

    return AdminMoneyRefundDetailRead(
        refund=AdminMoneyRefundDetailItemRead(**refund_summary.model_dump()),
        current_provider_snapshot=build_refund_provider_snapshot(refund),
        payment_summary=payment_summary,
        user_summary=(
            AdminMoneyPaymentUserContextRead.model_validate(payer)
            if payer is not None
            else None
        ),
        booking_summary=(
            AdminMoneyBookingContextRead.model_validate(booking)
            if booking is not None
            else None
        ),
        participant_summary=(
            AdminMoneyParticipantContextRead.model_validate(participant)
            if participant is not None
            else None
        ),
        game_summary=(
            AdminMoneyGameContextRead.model_validate(game)
            if game is not None
            else None
        ),
        publish_fee_summary=(
            AdminMoneyHostPublishFeeContextRead.model_validate(host_publish_fee)
            if host_publish_fee is not None
            else None
        ),
        credit_context=AdminMoneyRefundCreditContextRead(
            credit_grants=credit_grants,
            credit_usages=credit_usages,
        ),
        recent_refund_events=recent_refund_events,
        admin_activity=[
            AdminMoneyAuditActionSummaryRead.model_validate(action)
            for action in admin_activity
        ],
        linked_money_issue=linked_money_issue,
        available_actions=refund_available_actions(
            refund=refund,
            payment=payment,
            linked_money_issue=linked_money_issue,
        ),
    )
