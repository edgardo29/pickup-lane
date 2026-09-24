"""Admin publish-fee financial outcome workflows."""

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    AdminAction,
    AdminFinancialOutcome,
    AdminTargetNotice,
    Game,
    HostPublishEntitlement,
    HostPublishFee,
    MoneyIssue,
    Payment,
    Refund,
    User,
)
from backend.schemas.admin_money_financial_outcome_schema import (
    AdminMoneyFinancialOutcomeCreate,
    AdminMoneyFinancialOutcomeRead,
    AdminMoneyManualReviewResolveCreate,
)
from backend.services.admin_action_service import record_admin_action
from backend.services.admin_money_issue_service import (
    append_money_issue_event,
    publish_fee_prior_cash_attempts_are_incapable,
    refund_has_only_terminal_attempts,
    stage_refund_money_issue,
)
from backend.services.admin_record_rules import (
    normalize_idempotency_key,
    normalize_optional_text,
)
from backend.services.admin_review_service import link_admin_action_to_open_review_case
from backend.services.admin_target_notice_service import create_admin_target_notice
from backend.services.refund_event_service import record_refund_event
from backend.services.refund_service import (
    build_refund_conflict_detail,
    validate_refund_amount_available,
)

VALID_FINANCIAL_OUTCOMES = {
    "no_fee_charged",
    "refund",
    "credit",
    "forfeit",
    "manual_review",
}
APPLIED_OUTCOME_STATUSES = {"applied", "failed"}
ACTIVE_FINANCIAL_DECISION_STATUSES = {"pending", "applied", "not_applicable"}
REFUNDABLE_PAYMENT_STATUSES = {"succeeded"}
PUBLISH_FEE_REFUND_REASON = "publish_fee_refund"
FINANCIAL_OUTCOME_NOTICE_COPY = {
    "publish_fee_refunded": (
        "Publish fee refunded",
        "Your community game publish fee was refunded by Pickup Lane support.",
    ),
    "publish_credit_added": (
        "Publish credit added",
        "A replacement community publish credit was added to your account.",
    ),
}


def build_financial_outcome_conflict_detail(exc: IntegrityError) -> str:
    error_text = str(exc.orig)

    if "ck_admin_financial_outcomes_outcome" in error_text:
        return "outcome is not supported."

    if "ck_admin_financial_outcomes_target_required" in error_text:
        return "Financial outcomes require a host and target."

    if "uq_refunds_provider_refund_id" in error_text:
        return build_refund_conflict_detail(exc)

    if "ux_host_publish_entitlements_one_first_free_per_host" in error_text:
        return "This host already has a first free publish entitlement."

    if "ux_host_publish_entitlements_source_financial_outcome_id" in error_text:
        return "This financial outcome already has a publish-credit entitlement."

    if "uq_admin_actions_create_financial_outcome_idempotency" in error_text:
        return "Financial outcome with this idempotency key already exists."

    if (
        "uq_admin_financial_outcomes_active_fee_decision" in error_text
        or "uq_admin_financial_outcomes_active_game_no_fee_decision" in error_text
    ):
        return (
            "This publish fee already has an active financial outcome. "
            "Use the existing outcome or resolve it before recording another."
        )

    return error_text


def normalize_required_text(value: str | None, field_name: str) -> str:
    normalized = normalize_optional_text(value, field_name)
    if normalized is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} is required.",
        )

    return normalized


def normalize_required_idempotency_key(value: str | None) -> str:
    idempotency_key = normalize_idempotency_key(value)
    if idempotency_key is None or len(idempotency_key) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="idempotency_key must be at least 8 characters.",
        )

    return idempotency_key


def map_stripe_refund_status(provider_status: str) -> str:
    normalized_status = provider_status.strip().lower()
    if normalized_status == "succeeded":
        return "succeeded"
    if normalized_status == "failed":
        return "failed"
    if normalized_status in {"canceled", "cancelled"}:
        return "cancelled"
    return "processing"


def map_refund_status_to_outcome_status(refund_status: str) -> str:
    if refund_status == "succeeded":
        return "applied"
    if refund_status in {"failed", "cancelled"}:
        return "failed"
    return "pending"


def get_existing_financial_outcome_action(
    db: Session,
    *,
    admin_user_id: uuid.UUID,
    idempotency_key: str,
) -> AdminAction | None:
    return db.scalar(
        select(AdminAction)
        .where(
            AdminAction.admin_user_id == admin_user_id,
            AdminAction.action_type == "create_financial_outcome",
            AdminAction.idempotency_key == idempotency_key,
            AdminAction.target_financial_outcome_id.is_not(None),
        )
        .order_by(AdminAction.created_at.desc(), AdminAction.id.desc())
        .limit(1)
    )


def get_existing_financial_outcome(
    db: Session,
    *,
    admin_user_id: uuid.UUID,
    idempotency_key: str,
    request_identity: dict[str, Any],
) -> AdminFinancialOutcome | None:
    action = get_existing_financial_outcome_action(
        db,
        admin_user_id=admin_user_id,
        idempotency_key=idempotency_key,
    )
    if action is None or action.target_financial_outcome_id is None:
        return None

    if (action.metadata_ or {}).get("request_identity") != request_identity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Financial-outcome idempotency key was replayed with different request data.",
        )

    return db.get(AdminFinancialOutcome, action.target_financial_outcome_id)


def financial_outcome_request_identity(
    payload: AdminMoneyFinancialOutcomeCreate,
    *,
    outcome: str,
    reason: str,
    internal_note: str | None,
) -> dict[str, Any]:
    return {
        "outcome": outcome,
        "reason": reason,
        "internal_note": internal_note,
        "host_publish_fee_id": (
            str(payload.host_publish_fee_id)
            if payload.host_publish_fee_id is not None
            else None
        ),
        "host_user_id": (
            str(payload.host_user_id) if payload.host_user_id is not None else None
        ),
        "target_game_id": (
            str(payload.target_game_id) if payload.target_game_id is not None else None
        ),
        "amount_cents": payload.amount_cents,
    }


def get_admin_financial_outcome_detail(
    db: Session,
    *,
    financial_outcome_id: uuid.UUID,
) -> AdminMoneyFinancialOutcomeRead:
    financial_outcome = db.get(AdminFinancialOutcome, financial_outcome_id)
    if financial_outcome is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial outcome not found.",
        )
    return AdminMoneyFinancialOutcomeRead.model_validate(financial_outcome)


def get_locked_host_publish_fee_or_404(
    db: Session,
    host_publish_fee_id: uuid.UUID,
) -> HostPublishFee:
    host_publish_fee = db.scalar(
        select(HostPublishFee)
        .where(HostPublishFee.id == host_publish_fee_id)
        .with_for_update()
    )
    if host_publish_fee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Host publish fee not found.",
        )

    return host_publish_fee


def get_locked_payment_or_404(db: Session, payment_id: uuid.UUID) -> Payment:
    payment = db.scalar(
        select(Payment).where(Payment.id == payment_id).with_for_update()
    )
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found.",
        )

    return payment


def get_active_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Host user not found.",
        )

    return user


def get_active_game_or_404(db: Session, game_id: uuid.UUID) -> Game:
    game = db.get(Game, game_id)
    if game is None or game.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found.",
        )

    return game


def sum_succeeded_refunds_for_payment(db: Session, payment_id: uuid.UUID) -> int:
    from backend.services.refund_service import get_refund_payment_ledger

    payment = db.get(Payment, payment_id)
    if payment is None:
        return 0
    return get_refund_payment_ledger(
        db,
        payment_id=payment.id,
        payment_amount_cents=payment.amount_cents,
    ).confirmed_returned_cents


def sync_publish_fee_refunded_state(
    db: Session,
    *,
    payment: Payment,
    host_publish_fee: HostPublishFee,
    now: datetime,
) -> None:
    refunded_cents = sum_succeeded_refunds_for_payment(db, payment.id)
    if refunded_cents >= payment.amount_cents:
        host_publish_fee.fee_status = "refunded"
        host_publish_fee.updated_at = now
        db.add(host_publish_fee)


def validate_financial_outcome_payload(
    payload: AdminMoneyFinancialOutcomeCreate,
) -> tuple[str, str, str | None, str]:
    outcome = payload.outcome.strip().lower()
    if outcome not in VALID_FINANCIAL_OUTCOMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="outcome is not supported.",
        )

    reason = normalize_required_text(payload.reason, "reason")
    internal_note = normalize_optional_text(payload.internal_note, "internal_note")
    idempotency_key = normalize_required_idempotency_key(payload.idempotency_key)
    return outcome, reason, internal_note, idempotency_key


def resolve_outcome_context(
    db: Session,
    *,
    payload: AdminMoneyFinancialOutcomeCreate,
    outcome: str,
) -> tuple[uuid.UUID, uuid.UUID | None, HostPublishFee | None, Payment | None, int]:
    host_publish_fee = None
    payment = None
    target_game_id = payload.target_game_id

    if payload.host_publish_fee_id is not None:
        fee_reference = db.get(HostPublishFee, payload.host_publish_fee_id)
        if fee_reference is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Host publish fee not found.",
            )
        if fee_reference.payment_id is not None:
            payment = get_locked_payment_or_404(db, fee_reference.payment_id)
        host_publish_fee = get_locked_host_publish_fee_or_404(
            db, payload.host_publish_fee_id
        )
        target_game_id = target_game_id or host_publish_fee.game_id
        host_user_id = host_publish_fee.host_user_id
        if payload.host_user_id is not None and payload.host_user_id != host_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="host_user_id must match the host publish fee.",
            )

        if (
            payload.target_game_id is not None
            and payload.target_game_id != host_publish_fee.game_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="target_game_id must match the host publish fee game.",
            )

        if payment is not None and payment.id != host_publish_fee.payment_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Host publish fee payment changed while it was being locked.",
            )

        amount_cents = (
            payload.amount_cents
            if payload.amount_cents is not None
            else host_publish_fee.amount_cents
        )
        if amount_cents > host_publish_fee.amount_cents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="amount_cents exceeds the eligible target amount.",
            )
    else:
        if payload.host_user_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="host_user_id is required without host_publish_fee_id.",
            )
        host_user_id = payload.host_user_id
        get_active_user_or_404(db, host_user_id)
        amount_cents = payload.amount_cents if payload.amount_cents is not None else 0
        if amount_cents > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="amount_cents exceeds the eligible target amount.",
            )

    if target_game_id is not None:
        game = get_active_game_or_404(db, target_game_id)
        if game.game_type != "community":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Financial outcomes require a community game target.",
            )
        if game.host_user_id != host_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="target_game_id must belong to the host.",
            )

    if amount_cents < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="amount_cents must be greater than or equal to 0.",
        )

    return host_user_id, target_game_id, host_publish_fee, payment, amount_cents


def get_existing_active_financial_decision(
    db: Session,
    *,
    host_user_id: uuid.UUID,
    target_game_id: uuid.UUID | None,
    host_publish_fee: HostPublishFee | None,
) -> AdminFinancialOutcome | None:
    statement = (
        select(AdminFinancialOutcome)
        .where(
            AdminFinancialOutcome.applied_status.in_(ACTIVE_FINANCIAL_DECISION_STATUSES)
        )
        .order_by(
            AdminFinancialOutcome.created_at.desc(),
            AdminFinancialOutcome.id.desc(),
        )
        .with_for_update()
        .limit(1)
    )

    if host_publish_fee is not None:
        statement = statement.where(
            AdminFinancialOutcome.host_publish_fee_id == host_publish_fee.id
        )
    elif target_game_id is not None:
        statement = statement.where(
            AdminFinancialOutcome.host_user_id == host_user_id,
            AdminFinancialOutcome.target_game_id == target_game_id,
            AdminFinancialOutcome.host_publish_fee_id.is_(None),
        )
    else:
        return None

    return db.scalar(statement)


def enforce_no_existing_active_financial_decision(
    db: Session,
    *,
    host_user_id: uuid.UUID,
    target_game_id: uuid.UUID | None,
    host_publish_fee: HostPublishFee | None,
) -> None:
    existing_outcome = get_existing_active_financial_decision(
        db,
        host_user_id=host_user_id,
        target_game_id=target_game_id,
        host_publish_fee=host_publish_fee,
    )
    if existing_outcome is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This publish fee already has an active financial outcome. "
                "Use the existing outcome or resolve it before recording another."
            ),
        )


def validate_collected_publish_fee_context(
    *,
    host_publish_fee: HostPublishFee | None,
    payment: Payment | None,
    amount_cents: int,
) -> tuple[HostPublishFee, Payment]:
    if host_publish_fee is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Collected publish-fee outcomes require host_publish_fee_id.",
        )

    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Collected publish-fee outcomes require a paid publish fee payment.",
        )

    if host_publish_fee.fee_status == "refunded":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This host publish fee is already refunded.",
        )

    if host_publish_fee.fee_status != "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refund outcomes require a paid host publish fee.",
        )

    if payment.payment_type != "community_publish_fee":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Collected publish-fee outcomes require a community publish fee payment.",
        )

    if payment.payer_user_id != host_publish_fee.host_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Publish fee payment must use the host as payer.",
        )

    if payment.id != host_publish_fee.payment_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Host publish fee payment does not match the payment.",
        )

    if (
        payment.payment_status not in REFUNDABLE_PAYMENT_STATUSES
        or payment.paid_at is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Collected publish-fee outcomes require a succeeded publish fee payment.",
        )

    if amount_cents <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Collected publish-fee outcomes require amount_cents greater than 0.",
        )

    if amount_cents != host_publish_fee.amount_cents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Publish fee refunds must refund the full host publish fee.",
        )

    if payment.currency != host_publish_fee.currency:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Publish fee payment currency must match the fee currency.",
        )

    if payment.amount_cents != host_publish_fee.amount_cents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Publish fee payment amount must match the full fee amount.",
        )

    return host_publish_fee, payment


def validate_refund_outcome_context(
    db: Session,
    *,
    host_publish_fee: HostPublishFee | None,
    payment: Payment | None,
    amount_cents: int,
) -> tuple[HostPublishFee, Payment]:
    host_publish_fee, payment = validate_collected_publish_fee_context(
        host_publish_fee=host_publish_fee,
        payment=payment,
        amount_cents=amount_cents,
    )

    validate_refund_amount_available(
        db,
        payment.id,
        payment.amount_cents,
        amount_cents,
    )
    return host_publish_fee, payment


def create_base_financial_outcome(
    *,
    outcome: str,
    reason: str,
    internal_note: str | None,
    host_user_id: uuid.UUID,
    target_game_id: uuid.UUID | None,
    host_publish_fee: HostPublishFee | None,
    payment: Payment | None,
    amount_cents: int,
    admin_user: User,
    now: datetime,
) -> AdminFinancialOutcome:
    if outcome == "manual_review":
        applied_status = "pending"
        applied_at = None
        applied_by_user_id = None
    elif outcome == "no_fee_charged":
        applied_status = "not_applicable"
        applied_at = None
        applied_by_user_id = None
        amount_cents = 0
    else:
        applied_status = "pending"
        applied_at = None
        applied_by_user_id = None

    return AdminFinancialOutcome(
        id=uuid.uuid4(),
        target_game_id=target_game_id,
        target_sub_post_id=None,
        host_user_id=host_user_id,
        host_publish_fee_id=host_publish_fee.id if host_publish_fee else None,
        payment_id=payment.id if payment else None,
        refund_id=None,
        host_publish_entitlement_id=None,
        admin_action_id=None,
        review_case_id=None,
        outcome=outcome,
        applied_status=applied_status,
        amount_cents=amount_cents,
        currency="USD",
        reason=reason,
        internal_note=internal_note,
        failure_reason=None,
        created_by_user_id=admin_user.id,
        applied_by_user_id=applied_by_user_id,
        applied_at=applied_at,
        created_at=now,
        updated_at=now,
    )


def create_publish_fee_refund_record(
    *,
    payment: Payment,
    host_publish_fee: HostPublishFee,
    amount_cents: int,
    admin_user: User,
    now: datetime,
    financial_outcome_id: uuid.UUID,
) -> Refund:
    refund_id = uuid.uuid4()
    return Refund(
        id=refund_id,
        payment_id=payment.id,
        booking_id=None,
        participant_id=None,
        host_publish_fee_id=host_publish_fee.id,
        origin_workflow="community_publish_fee_refund",
        provider="stripe",
        provider_refund_id=None,
        origin_operation_key=(
            f"community_publish_fee_refund:financial_outcome:{financial_outcome_id}"
        ),
        current_attempt_number=1,
        stripe_request_key=f"refund:{refund_id}:attempt:1",
        provider_attempt_started_at=None,
        automatic_mutation_blocked_reason=None,
        automatic_mutation_blocked_at=None,
        provider_charge_id=payment.provider_charge_id,
        provider_status=None,
        provider_status_observed_at=None,
        last_refund_event_at=None,
        amount_cents=amount_cents,
        currency=payment.currency,
        refund_reason=PUBLISH_FEE_REFUND_REASON,
        refund_status="approved",
        requested_by_user_id=admin_user.id,
        approved_by_user_id=admin_user.id,
        requested_at=now,
        approved_at=now,
        refunded_at=None,
        created_at=now,
        updated_at=now,
    )


def apply_refund_outcome(
    db: Session,
    *,
    financial_outcome: AdminFinancialOutcome,
    host_publish_fee: HostPublishFee,
    payment: Payment,
    admin_user: User,
    idempotency_key: str,
    now: datetime,
) -> Refund:
    refund = create_publish_fee_refund_record(
        payment=payment,
        host_publish_fee=host_publish_fee,
        amount_cents=financial_outcome.amount_cents,
        admin_user=admin_user,
        now=now,
        financial_outcome_id=financial_outcome.id,
    )
    db.add(refund)
    db.flush()
    financial_outcome.refund_id = refund.id

    if payment.provider_charge_id is None:
        refund.refund_status = "failed"
        refund.refunded_at = None
        refund.updated_at = now
        financial_outcome.applied_status = "failed"
        financial_outcome.failure_reason = (
            "Publish fee payment is missing Stripe charge id."
        )
        financial_outcome.applied_by_user_id = admin_user.id
        financial_outcome.applied_at = now
        financial_outcome.updated_at = now
        db.add(refund)
        db.add(financial_outcome)
        refund_event = record_refund_event(
            db,
            refund=refund,
            event_type="local_status_changed",
            event_source="system",
            actor_user_id=admin_user.id,
            provider="stripe",
            provider_charge_id=None,
            provider_status=None,
            new_refund_status="failed",
            reason_code="provider_charge_id_missing",
            summary="Publish-fee refund could not start because the payment has no provider charge id.",
            metadata={"provider_call_started": False},
            occurred_at=now,
        )
        stage_refund_money_issue(
            db,
            refund=refund,
            payment=payment,
            issue_type="refund_missing_provider_reference",
            reason_code="provider_charge_id_missing",
            summary="Publish-fee refund could not start because the payment has no provider charge id.",
            refund_event=refund_event,
            now=now,
        )
        return refund

    financial_outcome.applied_status = "pending"
    financial_outcome.applied_at = None
    financial_outcome.applied_by_user_id = None
    financial_outcome.failure_reason = None
    financial_outcome.updated_at = now
    db.add(financial_outcome)
    record_refund_event(
        db,
        refund=refund,
        event_type="local_status_changed",
        event_source="system",
        actor_user_id=admin_user.id,
        provider="stripe",
        provider_charge_id=payment.provider_charge_id,
        new_refund_status="approved",
        reason_code="refund_approved_for_fulfillment",
        summary="Publish-fee refund approved for durable fulfillment.",
        occurred_at=now,
    )
    from backend.services.payment_job_service import build_production_job_registry
    from backend.services.refund_fulfillment_service import (
        enqueue_refund_fulfillment_job,
    )

    enqueue_refund_fulfillment_job(
        db, refund=refund, registry=build_production_job_registry()
    )
    return refund


def apply_credit_outcome(
    db: Session,
    *,
    financial_outcome: AdminFinancialOutcome,
    admin_user: User,
    now: datetime,
) -> HostPublishEntitlement:
    if financial_outcome.amount_cents <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Credit outcomes require amount_cents greater than 0.",
        )

    entitlement = HostPublishEntitlement(
        id=uuid.uuid4(),
        host_user_id=financial_outcome.host_user_id,
        entitlement_type="refund_replacement",
        status="available",
        source="financial_outcome",
        source_admin_action_id=None,
        source_financial_outcome_id=financial_outcome.id,
        reserved_by_attempt_id=None,
        used_by_game_id=None,
        used_by_host_publish_fee_id=None,
        used_at=None,
        revoked_at=None,
        revoked_by_user_id=None,
        revoke_reason=None,
        created_at=now,
        updated_at=now,
    )
    db.add(entitlement)
    db.flush()

    financial_outcome.host_publish_entitlement_id = entitlement.id
    financial_outcome.applied_status = "applied"
    financial_outcome.applied_by_user_id = admin_user.id
    financial_outcome.applied_at = now
    financial_outcome.updated_at = now
    db.add(financial_outcome)
    return entitlement


def apply_non_refund_outcome(
    *,
    financial_outcome: AdminFinancialOutcome,
    admin_user: User,
    now: datetime,
) -> None:
    if financial_outcome.outcome == "forfeit":
        financial_outcome.applied_status = "applied"
        financial_outcome.applied_by_user_id = admin_user.id
        financial_outcome.applied_at = now
    elif financial_outcome.outcome == "no_fee_charged":
        financial_outcome.applied_status = "not_applicable"
        financial_outcome.applied_by_user_id = None
        financial_outcome.applied_at = None
        financial_outcome.amount_cents = 0
    elif financial_outcome.outcome == "manual_review":
        financial_outcome.applied_status = "pending"
        financial_outcome.applied_by_user_id = None
        financial_outcome.applied_at = None
    financial_outcome.updated_at = now


def financial_outcome_audit_metadata(
    financial_outcome: AdminFinancialOutcome,
    *,
    source: str,
    refund: Refund | None = None,
    payment: Payment | None = None,
) -> dict[str, Any]:
    return {
        "source": source,
        "financial_outcome_id": str(financial_outcome.id),
        "outcome": financial_outcome.outcome,
        "applied_status": financial_outcome.applied_status,
        "amount_cents": financial_outcome.amount_cents,
        "currency": financial_outcome.currency,
        "host_publish_fee_id": (
            str(financial_outcome.host_publish_fee_id)
            if financial_outcome.host_publish_fee_id is not None
            else None
        ),
        "host_publish_entitlement_id": (
            str(financial_outcome.host_publish_entitlement_id)
            if financial_outcome.host_publish_entitlement_id is not None
            else None
        ),
        "failure_reason": financial_outcome.failure_reason,
        "refund_status": refund.refund_status if refund is not None else None,
        "refund_reason": refund.refund_reason if refund is not None else None,
        "payment_status": payment.payment_status if payment is not None else None,
        "payment_type": payment.payment_type if payment is not None else None,
    }


def financial_outcome_audit_targets(
    financial_outcome: AdminFinancialOutcome,
) -> dict[str, uuid.UUID | None]:
    return {
        "target_user_id": financial_outcome.host_user_id,
        "target_game_id": financial_outcome.target_game_id,
        "target_payment_id": financial_outcome.payment_id,
        "target_refund_id": financial_outcome.refund_id,
        "target_financial_outcome_id": financial_outcome.id,
        "target_host_publish_fee_id": financial_outcome.host_publish_fee_id,
        "target_host_publish_entitlement_id": (
            financial_outcome.host_publish_entitlement_id
        ),
    }


def get_financial_outcome_notice_type(
    financial_outcome: AdminFinancialOutcome,
) -> str | None:
    if (
        financial_outcome.outcome == "refund"
        and financial_outcome.applied_status == "applied"
    ):
        return "publish_fee_refunded"

    if (
        financial_outcome.outcome == "credit"
        and financial_outcome.applied_status == "applied"
    ):
        return "publish_credit_added"

    return None


def find_existing_financial_outcome_notice(
    db: Session,
    *,
    financial_outcome: AdminFinancialOutcome,
    notice_type: str,
) -> AdminTargetNotice | None:
    return db.scalar(
        select(AdminTargetNotice)
        .where(
            AdminTargetNotice.notice_type == notice_type,
            AdminTargetNotice.recipient_user_id == financial_outcome.host_user_id,
            AdminTargetNotice.notice_metadata.contains(
                {"financial_outcome_id": str(financial_outcome.id)}
            ),
        )
        .limit(1)
    )


def create_financial_outcome_notice_if_needed(
    db: Session,
    *,
    financial_outcome: AdminFinancialOutcome,
    admin_action: AdminAction | None = None,
    created_by_user_id: uuid.UUID | None = None,
) -> AdminTargetNotice | None:
    notice_type = get_financial_outcome_notice_type(financial_outcome)
    if notice_type is None:
        return None

    existing_notice = find_existing_financial_outcome_notice(
        db,
        financial_outcome=financial_outcome,
        notice_type=notice_type,
    )
    if existing_notice is not None:
        return existing_notice

    if admin_action is None and financial_outcome.admin_action_id is not None:
        admin_action = db.get(AdminAction, financial_outcome.admin_action_id)

    title, body = FINANCIAL_OUTCOME_NOTICE_COPY[notice_type]
    notice = create_admin_target_notice(
        db,
        notice_type=notice_type,
        title=title,
        body=body,
        recipient_user_id=financial_outcome.host_user_id,
        target_user_id=financial_outcome.host_user_id,
        target_game_id=financial_outcome.target_game_id,
        admin_action=admin_action,
        created_by_user_id=created_by_user_id or financial_outcome.created_by_user_id,
        notice_metadata={
            "financial_outcome_id": str(financial_outcome.id),
            "host_publish_fee_id": (
                str(financial_outcome.host_publish_fee_id)
                if financial_outcome.host_publish_fee_id is not None
                else None
            ),
            "refund_id": (
                str(financial_outcome.refund_id)
                if financial_outcome.refund_id is not None
                else None
            ),
            "host_publish_entitlement_id": (
                str(financial_outcome.host_publish_entitlement_id)
                if financial_outcome.host_publish_entitlement_id is not None
                else None
            ),
        },
    )
    return notice


def record_financial_outcome_actions(
    db: Session,
    *,
    financial_outcome: AdminFinancialOutcome,
    admin_user: User,
    idempotency_key: str,
    refund: Refund | None,
    payment: Payment | None,
    request_identity: dict[str, Any],
) -> AdminAction:
    create_action = record_admin_action(
        db,
        admin_user_id=admin_user.id,
        action_type="create_financial_outcome",
        outcome="succeeded",
        reason=financial_outcome.reason,
        idempotency_key=idempotency_key,
        metadata={
            **financial_outcome_audit_metadata(
                financial_outcome,
                source="admin_money_financial_outcome_create",
                refund=refund,
                payment=payment,
            ),
            "request_identity": request_identity,
        },
        **financial_outcome_audit_targets(financial_outcome),
    )
    linked_review_case = link_admin_action_to_open_review_case(db, create_action)
    if linked_review_case is not None and financial_outcome.review_case_id is None:
        financial_outcome.review_case_id = linked_review_case.id
    db.flush()
    financial_outcome.admin_action_id = create_action.id
    db.add(financial_outcome)
    if financial_outcome.host_publish_entitlement_id is not None:
        entitlement = db.get(
            HostPublishEntitlement,
            financial_outcome.host_publish_entitlement_id,
        )
        if entitlement is not None and entitlement.source_admin_action_id is None:
            entitlement.source_admin_action_id = create_action.id
            entitlement.updated_at = datetime.now(timezone.utc)
            db.add(entitlement)

    if financial_outcome.outcome in {"refund", "credit", "forfeit"}:
        apply_action_outcome = {
            "applied": "succeeded",
            "not_applicable": "succeeded",
            "failed": "failed",
            "pending": "pending",
        }[financial_outcome.applied_status]
        apply_action = record_admin_action(
            db,
            admin_user_id=admin_user.id,
            action_type="apply_financial_outcome",
            outcome=apply_action_outcome,
            reason=financial_outcome.reason,
            metadata=financial_outcome_audit_metadata(
                financial_outcome,
                source="admin_money_financial_outcome_apply",
                refund=refund,
                payment=payment,
            ),
            **financial_outcome_audit_targets(financial_outcome),
        )
        link_admin_action_to_open_review_case(db, apply_action)

    create_financial_outcome_notice_if_needed(
        db,
        financial_outcome=financial_outcome,
        admin_action=create_action,
        created_by_user_id=admin_user.id,
    )
    return create_action


def stage_financial_outcome_money_issue(
    db: Session,
    *,
    financial_outcome: AdminFinancialOutcome,
    refund: Refund | None,
    payment: Payment | None,
    admin_user: User,
    admin_action: AdminAction,
) -> None:
    if financial_outcome.outcome != "refund":
        return

    if refund is None:
        return

    if financial_outcome.failure_reason == (
        "Publish fee payment is missing Stripe charge id."
    ):
        issue_type = "refund_missing_provider_reference"
        summary = "A publish-fee refund needs Money Issue review."
        reason_code = "provider_charge_id_missing"
    elif refund.refund_status == "processing":
        return
    elif refund.refund_status in {"failed", "cancelled"}:
        issue_type = (
            "refund_failed" if refund.refund_status == "failed" else "refund_cancelled"
        )
        summary = "A publish-fee refund did not complete in Stripe."
        reason_code = f"publish_fee_refund_{refund.refund_status}"
    else:
        return

    stage_refund_money_issue(
        db,
        refund=refund,
        payment=payment,
        issue_type=issue_type,
        reason_code=reason_code,
        summary=summary,
        admin_action=admin_action,
    )


def reclassify_superseded_publish_refund_issues(
    db: Session,
    *,
    financial_outcome: AdminFinancialOutcome,
    admin_user: User | None = None,
    admin_action: AdminAction | None = None,
) -> None:
    if (
        financial_outcome.host_publish_fee_id is None
        or financial_outcome.applied_status not in ACTIVE_FINANCIAL_DECISION_STATUSES
        or financial_outcome.outcome
        not in {"credit", "forfeit", "refund", "manual_review"}
    ):
        return
    fee = db.get(HostPublishFee, financial_outcome.host_publish_fee_id)
    if fee is None or financial_outcome.amount_cents != fee.amount_cents:
        return
    prior_refund_query = select(Refund).where(
        Refund.host_publish_fee_id == financial_outcome.host_publish_fee_id,
        Refund.refund_status.in_({"failed", "cancelled"}),
    )
    if financial_outcome.refund_id is not None:
        prior_refund_query = prior_refund_query.where(
            Refund.id != financial_outcome.refund_id
        )
    prior_refunds = list(
        db.scalars(
            prior_refund_query.order_by(Refund.id.asc()).with_for_update()
        ).all()
    )
    if not prior_refunds:
        return
    list(
        db.scalars(
            select(AdminFinancialOutcome)
            .where(
                AdminFinancialOutcome.host_publish_fee_id
                == financial_outcome.host_publish_fee_id
            )
            .order_by(AdminFinancialOutcome.id.asc())
            .with_for_update()
        ).all()
    )
    issues = list(
        db.scalars(
            select(MoneyIssue).where(
                MoneyIssue.target_refund_id.in_([refund.id for refund in prior_refunds]),
                MoneyIssue.status == "open",
            )
            .order_by(MoneyIssue.id.asc())
            .with_for_update()
        ).all()
    )
    for issue in issues:
        previous_action = issue.recommended_action_code
        issue.recommended_action_code = "review_superseding_financial_outcome"
        issue.latest_reason_code = "superseded_by_financial_outcome"
        issue.latest_summary = (
            "A later authoritative publish-fee decision supersedes this cash refund."
        )
        issue.updated_at = financial_outcome.updated_at
        db.add(issue)
        append_money_issue_event(
            db,
            money_issue=issue,
            event_type="recommended_action_changed",
            event_source="admin" if admin_user is not None else "system",
            actor_user_id=admin_user.id if admin_user is not None else None,
            admin_action_id=admin_action.id if admin_action is not None else None,
            reason_code="superseded_by_financial_outcome",
            summary=issue.latest_summary,
            previous_recommended_action_code=previous_action,
            new_recommended_action_code=issue.recommended_action_code,
            metadata={
                "replacement_financial_outcome_id": str(financial_outcome.id)
            },
        )


def recompute_superseded_publish_refund_issues(
    db: Session,
    *,
    financial_outcome: AdminFinancialOutcome,
) -> None:
    """Restore truthful retry guidance when a replacement stops being authoritative."""
    if financial_outcome.host_publish_fee_id is None:
        return
    authoritative = db.scalars(
        select(AdminFinancialOutcome).where(
            AdminFinancialOutcome.host_publish_fee_id
            == financial_outcome.host_publish_fee_id,
            AdminFinancialOutcome.applied_status.in_(ACTIVE_FINANCIAL_DECISION_STATUSES),
        )
    ).first()
    if authoritative is not None:
        return
    prior_refunds = list(
        db.scalars(
            select(Refund).where(
                Refund.host_publish_fee_id == financial_outcome.host_publish_fee_id,
                Refund.refund_status.in_({"failed", "cancelled"}),
            )
            .order_by(Refund.id.asc())
            .with_for_update()
        ).all()
    )
    if not prior_refunds:
        return
    refunds_by_id = {refund.id: refund for refund in prior_refunds}
    issues = list(
        db.scalars(
            select(MoneyIssue)
            .where(
                MoneyIssue.target_refund_id.in_(refunds_by_id),
                MoneyIssue.status == "open",
                MoneyIssue.recommended_action_code
                == "review_superseding_financial_outcome",
            )
            .order_by(MoneyIssue.id.asc())
            .with_for_update()
        ).all()
    )
    now = datetime.now(timezone.utc)
    for issue in issues:
        refund = refunds_by_id.get(issue.target_refund_id)
        if refund is None:
            continue
        previous_action = issue.recommended_action_code
        if refund_has_only_terminal_attempts(db, refund):
            next_action = "retry_refund"
        elif refund.provider_refund_id is None:
            next_action = "recover_provider_reference"
        else:
            next_action = "review_unknown_outcome"
        issue.recommended_action_code = next_action
        issue.latest_reason_code = "superseding_financial_outcome_failed"
        issue.latest_summary = (
            "The replacement financial outcome failed; the earlier refund requires "
            "a fresh provider-state review."
        )
        issue.updated_at = now
        append_money_issue_event(
            db,
            money_issue=issue,
            event_type="recommended_action_changed",
            event_source="system",
            reason_code="superseding_financial_outcome_failed",
            summary=issue.latest_summary,
            previous_recommended_action_code=previous_action,
            new_recommended_action_code=issue.recommended_action_code,
            occurred_at=now,
        )


def create_admin_financial_outcome(
    db: Session,
    *,
    admin_user: User,
    payload: AdminMoneyFinancialOutcomeCreate,
    commit: bool = True,
) -> AdminMoneyFinancialOutcomeRead:
    outcome, reason, internal_note, idempotency_key = (
        validate_financial_outcome_payload(payload)
    )
    request_identity = financial_outcome_request_identity(
        payload,
        outcome=outcome,
        reason=reason,
        internal_note=internal_note,
    )
    existing_outcome = get_existing_financial_outcome(
        db,
        admin_user_id=admin_user.id,
        idempotency_key=idempotency_key,
        request_identity=request_identity,
    )
    if existing_outcome is not None:
        return AdminMoneyFinancialOutcomeRead.model_validate(existing_outcome)

    now = datetime.now(timezone.utc)
    (
        host_user_id,
        target_game_id,
        host_publish_fee,
        payment,
        amount_cents,
    ) = resolve_outcome_context(db, payload=payload, outcome=outcome)

    if outcome in {"refund", "credit", "forfeit", "manual_review"} and amount_cents <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{outcome} outcomes require amount_cents greater than 0.",
        )

    if host_publish_fee is not None:
        collected_payment = (
            payment is not None
            and payment.payment_status == "succeeded"
            and payment.paid_at is not None
        )
        paid_context = host_publish_fee.fee_status == "paid" or collected_payment
        if paid_context and outcome == "no_fee_charged":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A collected publish fee cannot resolve to no_fee_charged.",
            )
        if not paid_context and outcome not in {"no_fee_charged", "manual_review"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An uncollected publish fee allows only no_fee_charged or manual_review.",
            )
        if outcome in {"refund", "credit", "forfeit", "manual_review"} and (
            amount_cents != host_publish_fee.amount_cents
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Publish-fee financial decisions must use the full host publish fee.",
            )
        if outcome == "no_fee_charged" and amount_cents != 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="no_fee_charged requires amount_cents 0.",
            )

        if paid_context and outcome in {"refund", "credit", "forfeit", "manual_review"}:
            host_publish_fee, payment = validate_collected_publish_fee_context(
                host_publish_fee=host_publish_fee,
                payment=payment,
                amount_cents=amount_cents,
            )

    if outcome == "refund":
        if host_publish_fee is None or payment is None:
            raise AssertionError("validated refund outcome is missing context")
        validate_refund_amount_available(
            db,
            payment.id,
            payment.amount_cents,
            amount_cents,
        )
    if (
        host_publish_fee is not None
        and outcome in {"refund", "credit", "forfeit"}
        and not publish_fee_prior_cash_attempts_are_incapable(
            db, host_publish_fee_id=host_publish_fee.id
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A prior cash refund attempt may still return value. Reconcile every "
                "attempt before applying a replacement financial outcome."
            ),
        )
    enforce_no_existing_active_financial_decision(
        db,
        host_user_id=host_user_id,
        target_game_id=target_game_id,
        host_publish_fee=host_publish_fee,
    )

    financial_outcome = create_base_financial_outcome(
        outcome=outcome,
        reason=reason,
        internal_note=internal_note,
        host_user_id=host_user_id,
        target_game_id=target_game_id,
        host_publish_fee=host_publish_fee,
        payment=payment,
        amount_cents=amount_cents,
        admin_user=admin_user,
        now=now,
    )

    refund: Refund | None = None
    try:
        db.add(financial_outcome)
        db.flush()

        if outcome == "refund":
            if host_publish_fee is None or payment is None:
                raise AssertionError("validated refund outcome is missing context")
            refund = apply_refund_outcome(
                db,
                financial_outcome=financial_outcome,
                host_publish_fee=host_publish_fee,
                payment=payment,
                admin_user=admin_user,
                idempotency_key=idempotency_key,
                now=now,
            )
        elif outcome == "credit":
            entitlement = apply_credit_outcome(
                db,
                financial_outcome=financial_outcome,
                admin_user=admin_user,
                now=now,
            )
            db.add(entitlement)
        else:
            apply_non_refund_outcome(
                financial_outcome=financial_outcome,
                admin_user=admin_user,
                now=now,
            )

        db.add(financial_outcome)
        db.flush()
        admin_action = record_financial_outcome_actions(
            db,
            financial_outcome=financial_outcome,
            admin_user=admin_user,
            idempotency_key=idempotency_key,
            refund=refund,
            payment=payment,
            request_identity=request_identity,
        )
        stage_financial_outcome_money_issue(
            db,
            financial_outcome=financial_outcome,
            refund=refund,
            payment=payment,
            admin_user=admin_user,
            admin_action=admin_action,
        )
        reclassify_superseded_publish_refund_issues(
            db,
            financial_outcome=financial_outcome,
            admin_user=admin_user,
            admin_action=admin_action,
        )
        if commit:
            db.commit()
            db.refresh(financial_outcome)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        existing_outcome = get_existing_financial_outcome(
            db,
            admin_user_id=admin_user.id,
            idempotency_key=idempotency_key,
            request_identity=request_identity,
        )
        if existing_outcome is not None:
            return AdminMoneyFinancialOutcomeRead.model_validate(existing_outcome)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_financial_outcome_conflict_detail(exc),
        ) from exc

    return AdminMoneyFinancialOutcomeRead.model_validate(financial_outcome)


def resolve_admin_manual_review(
    db: Session,
    *,
    admin_user: User,
    financial_outcome_id: uuid.UUID,
    payload: AdminMoneyManualReviewResolveCreate,
) -> AdminMoneyFinancialOutcomeRead:
    idempotency_key = normalize_required_idempotency_key(payload.idempotency_key)
    replay_identity = {
        "outcome": payload.outcome.strip().lower(),
        "reason": normalize_required_text(payload.reason, "reason"),
        "internal_note": normalize_optional_text(payload.internal_note, "internal_note"),
        "amount_cents": payload.amount_cents,
    }
    existing_action = db.scalars(
        select(AdminAction).where(
            AdminAction.admin_user_id == admin_user.id,
            AdminAction.action_type == "resolve_manual_review",
            AdminAction.target_financial_outcome_id == financial_outcome_id,
            AdminAction.idempotency_key == idempotency_key,
        )
    ).first()
    if existing_action is not None:
        existing_metadata = existing_action.metadata_ or {}
        if existing_metadata.get("resolution_identity") != replay_identity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Manual-review idempotency key was replayed with different resolution data.",
            )
        replacement_id = existing_metadata.get(
            "replacement_financial_outcome_id"
        )
        try:
            replacement_uuid = uuid.UUID(replacement_id)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Manual-review replay is missing its replacement outcome.",
            )
        return get_admin_financial_outcome_detail(
            db, financial_outcome_id=replacement_uuid
        )

    reference = db.get(AdminFinancialOutcome, financial_outcome_id)
    if reference is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial outcome not found.",
        )
    payment = (
        get_locked_payment_or_404(db, reference.payment_id)
        if reference.payment_id is not None
        else None
    )
    fee = (
        get_locked_host_publish_fee_or_404(db, reference.host_publish_fee_id)
        if reference.host_publish_fee_id is not None
        else None
    )
    manual_review = db.scalars(
        select(AdminFinancialOutcome)
        .where(AdminFinancialOutcome.id == financial_outcome_id)
        .with_for_update()
    ).first()
    existing_action = db.scalars(
        select(AdminAction).where(
            AdminAction.admin_user_id == admin_user.id,
            AdminAction.action_type == "resolve_manual_review",
            AdminAction.target_financial_outcome_id == financial_outcome_id,
            AdminAction.idempotency_key == idempotency_key,
        )
    ).first()
    if existing_action is not None:
        existing_metadata = existing_action.metadata_ or {}
        if existing_metadata.get("resolution_identity") != replay_identity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Manual-review idempotency key was replayed with different resolution data.",
            )
        replacement_id = existing_metadata.get("replacement_financial_outcome_id")
        try:
            replacement_uuid = uuid.UUID(replacement_id)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Manual-review replay is missing its replacement outcome.",
            )
        return get_admin_financial_outcome_detail(
            db, financial_outcome_id=replacement_uuid
        )
    if (
        manual_review is None
        or manual_review.outcome != "manual_review"
        or manual_review.applied_status != "pending"
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only an active pending manual review can be resolved.",
        )
    paid = payment is not None and payment.payment_status == "succeeded"
    if paid and payload.outcome == "no_fee_charged":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A collected publish fee cannot resolve to no_fee_charged.",
        )
    if not paid and payload.outcome != "no_fee_charged":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An uncollected publish fee can resolve only to no_fee_charged.",
        )
    now = datetime.now(timezone.utc)
    manual_review.applied_status = "superseded"
    manual_review.superseded_at = now
    manual_review.applied_at = None
    manual_review.applied_by_user_id = None
    manual_review.updated_at = now
    db.add(manual_review)
    db.flush()
    replacement_idempotency_key = (
        "manual-review-replacement:"
        + hashlib.sha256(
            f"{manual_review.id}:{admin_user.id}:{idempotency_key}".encode()
        ).hexdigest()
    )
    replacement = create_admin_financial_outcome(
        db,
        admin_user=admin_user,
        payload=AdminMoneyFinancialOutcomeCreate(
            outcome=payload.outcome,
            reason=payload.reason,
            internal_note=payload.internal_note,
            idempotency_key=replacement_idempotency_key,
            host_publish_fee_id=fee.id if fee is not None else None,
            host_user_id=manual_review.host_user_id,
            target_game_id=manual_review.target_game_id,
            amount_cents=payload.amount_cents,
        ),
        commit=False,
    )
    record_admin_action(
        db,
        admin_user_id=admin_user.id,
        action_type="resolve_manual_review",
        outcome="succeeded",
        target_user_id=manual_review.host_user_id,
        target_game_id=manual_review.target_game_id,
        target_payment_id=manual_review.payment_id,
        target_financial_outcome_id=manual_review.id,
        target_host_publish_fee_id=manual_review.host_publish_fee_id,
        reason=payload.reason,
        idempotency_key=idempotency_key,
        metadata={
            "manual_review_financial_outcome_id": str(manual_review.id),
            "replacement_financial_outcome_id": str(replacement.id),
            "resolution_identity": replay_identity,
        },
    )
    db.commit()
    return get_admin_financial_outcome_detail(
        db, financial_outcome_id=replacement.id
    )
