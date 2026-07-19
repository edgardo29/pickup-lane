"""Admin publish-fee financial outcome workflows."""

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    AdminAction,
    AdminFinancialOutcome,
    AdminTargetNotice,
    Game,
    HostPublishEntitlement,
    HostPublishFee,
    Payment,
    Refund,
    User,
)
from backend.schemas.admin_money_schema import (
    AdminMoneyFinancialOutcomeCreate,
    AdminMoneyFinancialOutcomeRead,
)
from backend.services.admin_action_service import record_admin_action
from backend.services.admin_record_rules import (
    normalize_idempotency_key,
    normalize_optional_text,
)
from backend.services.admin_review_service import link_admin_action_to_open_review_case
from backend.services.admin_target_notice_service import create_admin_target_notice
from backend.services.refund_service import (
    build_refund_conflict_detail,
    validate_refund_amount_available,
)
from backend.services.stripe_service import (
    StripeConfigError,
    create_refund as create_stripe_refund,
)
from backend.services.support_flag_service import stage_support_flag

VALID_FINANCIAL_OUTCOMES = {
    "no_fee_charged",
    "refund",
    "credit",
    "forfeit",
    "manual_review",
}
APPLIED_OUTCOME_STATUSES = {"applied", "failed"}
ACTIVE_FINANCIAL_DECISION_STATUSES = {"pending", "applied", "not_applicable"}
REFUNDABLE_PAYMENT_STATUSES = {"succeeded", "partially_refunded"}
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
) -> AdminFinancialOutcome | None:
    action = get_existing_financial_outcome_action(
        db,
        admin_user_id=admin_user_id,
        idempotency_key=idempotency_key,
    )
    if action is None or action.target_financial_outcome_id is None:
        return None

    return db.get(AdminFinancialOutcome, action.target_financial_outcome_id)


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
    return (
        db.scalar(
            select(func.coalesce(func.sum(Refund.amount_cents), 0)).where(
                Refund.payment_id == payment_id,
                Refund.refund_status == "succeeded",
            )
        )
        or 0
    )


def sync_publish_fee_refunded_state(
    db: Session,
    *,
    payment: Payment,
    host_publish_fee: HostPublishFee,
    now: datetime,
) -> None:
    refunded_cents = sum_succeeded_refunds_for_payment(db, payment.id)
    payment.payment_status = (
        "refunded" if refunded_cents >= payment.amount_cents else "partially_refunded"
    )
    payment.updated_at = now
    db.add(payment)

    if payment.payment_status == "refunded":
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
        host_publish_fee = get_locked_host_publish_fee_or_404(
            db,
            payload.host_publish_fee_id,
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

        if (
            host_publish_fee.payment_id is not None
            and outcome in {"refund", "credit", "forfeit", "manual_review"}
        ):
            payment = get_locked_payment_or_404(db, host_publish_fee.payment_id)

        amount_cents = (
            payload.amount_cents
            if payload.amount_cents is not None
            else host_publish_fee.amount_cents
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
        .where(AdminFinancialOutcome.applied_status.in_(ACTIVE_FINANCIAL_DECISION_STATUSES))
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


def validate_refund_outcome_context(
    db: Session,
    *,
    host_publish_fee: HostPublishFee | None,
    payment: Payment | None,
    amount_cents: int,
) -> tuple[HostPublishFee, Payment]:
    if host_publish_fee is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refund outcomes require host_publish_fee_id.",
        )

    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refund outcomes require a paid publish fee payment.",
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
            detail="Refund outcomes require a community publish fee payment.",
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
            detail="Refund outcomes require a succeeded publish fee payment.",
        )

    if amount_cents <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refund outcomes require amount_cents greater than 0.",
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
) -> Refund:
    return Refund(
        id=uuid.uuid4(),
        payment_id=payment.id,
        booking_id=None,
        participant_id=None,
        host_publish_fee_id=host_publish_fee.id,
        provider_refund_id=None,
        amount_cents=amount_cents,
        currency=payment.currency,
        refund_reason=PUBLISH_FEE_REFUND_REASON,
        refund_status="processing",
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
        return refund

    try:
        provider_refund = create_stripe_refund(
            charge_id=payment.provider_charge_id,
            amount_cents=refund.amount_cents,
            currency=refund.currency,
            idempotency_key=f"{idempotency_key}:stripe-refund",
            metadata={
                "source": "community_publish_fee_financial_outcome",
                "payment_id": str(payment.id),
                "refund_id": str(refund.id),
                "host_publish_fee_id": str(host_publish_fee.id),
                "financial_outcome_id": str(financial_outcome.id),
                "admin_user_id": str(admin_user.id),
            },
        )
        refund.provider_refund_id = provider_refund.id
        refund.refund_status = map_stripe_refund_status(provider_refund.status)
    except StripeConfigError:
        refund.refund_status = "failed"
        financial_outcome.failure_reason = "Stripe refunds are not configured."
    except Exception:
        refund.refund_status = "failed"
        financial_outcome.failure_reason = (
            "Stripe publish fee refund could not be completed."
        )

    refund.refunded_at = now if refund.refund_status == "succeeded" else None
    refund.updated_at = now
    financial_outcome.applied_status = map_refund_status_to_outcome_status(
        refund.refund_status
    )
    financial_outcome.applied_by_user_id = admin_user.id
    if financial_outcome.applied_status in APPLIED_OUTCOME_STATUSES:
        financial_outcome.applied_at = now
    financial_outcome.updated_at = now
    if refund.refund_status == "succeeded":
        db.flush()
        sync_publish_fee_refunded_state(
            db,
            payment=payment,
            host_publish_fee=host_publish_fee,
            now=now,
        )
    db.add(refund)
    db.add(financial_outcome)
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


def add_notice_id_to_action_metadata(
    admin_action: AdminAction,
    notice: AdminTargetNotice,
) -> None:
    metadata = dict(admin_action.metadata_ or {})
    notice_ids = list(metadata.get("notice_ids") or [])
    notice_id = str(notice.id)
    if notice_id not in notice_ids:
        notice_ids.append(notice_id)
    metadata["notice_ids"] = notice_ids
    admin_action.metadata_ = metadata


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
        if admin_action is None and financial_outcome.admin_action_id is not None:
            admin_action = db.get(AdminAction, financial_outcome.admin_action_id)
        if admin_action is not None:
            add_notice_id_to_action_metadata(admin_action, existing_notice)
            db.add(admin_action)
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
        user_safe_reason=None,
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
    if admin_action is not None:
        add_notice_id_to_action_metadata(admin_action, notice)
        db.add(admin_action)
    return notice


def record_financial_outcome_actions(
    db: Session,
    *,
    financial_outcome: AdminFinancialOutcome,
    admin_user: User,
    idempotency_key: str,
    refund: Refund | None,
    payment: Payment | None,
) -> AdminAction:
    create_action = record_admin_action(
        db,
        admin_user_id=admin_user.id,
        action_type="create_financial_outcome",
        reason=financial_outcome.reason,
        idempotency_key=idempotency_key,
        metadata=financial_outcome_audit_metadata(
            financial_outcome,
            source="admin_money_financial_outcome_create",
            refund=refund,
            payment=payment,
        ),
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
        apply_action = record_admin_action(
            db,
            admin_user_id=admin_user.id,
            action_type="apply_financial_outcome",
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


def stage_financial_outcome_support_flag(
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

    target_game_id = financial_outcome.target_game_id
    if refund is None:
        if financial_outcome.failure_reason and payment is not None:
            stage_support_flag(
                db,
                flag_type="missing_stripe_charge_id",
                source="stripe",
                title="Publish fee refund could not start",
                summary="A publish-fee refund needs money support follow-up.",
                severity="urgent",
                metadata={
                    "operation": "admin_publish_fee_refund",
                    "financial_outcome_id": str(financial_outcome.id),
                    "applied_status": financial_outcome.applied_status,
                },
                idempotency_key=f"publish-fee-refund-missing-charge:{payment.id}",
                source_admin_action_id=admin_action.id,
                created_by_user_id=admin_user.id,
                reopen_resolved=True,
                target_user_id=financial_outcome.host_user_id,
                target_game_id=target_game_id,
                target_booking_id=None,
                target_payment_id=payment.id,
                target_refund_id=None,
                target_game_credit_id=None,
                target_venue_id=None,
                target_venue_image_id=None,
                target_notification_id=None,
            )
        return

    if financial_outcome.failure_reason == (
        "Publish fee payment is missing Stripe charge id."
    ):
        flag_type = "missing_stripe_charge_id"
        title = "Publish fee refund is missing a Stripe charge"
        summary = "A publish-fee refund needs money support follow-up."
        severity = "urgent"
        idempotency_status = "missing-charge"
    elif refund.refund_status == "processing":
        flag_type = "refund_follow_up_required"
        title = "Publish fee refund still processing"
        summary = (
            "A publish-fee refund was sent to Stripe but has not finalized yet."
        )
        severity = "attention"
        idempotency_status = "processing"
    elif refund.refund_status in {"failed", "cancelled"}:
        flag_type = "stripe_refund_failed"
        title = "Publish fee refund failed"
        summary = "A publish-fee refund did not complete in Stripe."
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
        metadata={
            "operation": "admin_publish_fee_refund",
            "financial_outcome_id": str(financial_outcome.id),
            "refund_status": refund.refund_status,
        },
        idempotency_key=(
            f"admin-publish-fee-refund:{refund.id}:{idempotency_status}"
        ),
        source_admin_action_id=admin_action.id,
        created_by_user_id=admin_user.id,
        reopen_resolved=True,
        target_user_id=financial_outcome.host_user_id,
        target_game_id=target_game_id,
        target_booking_id=None,
        target_payment_id=payment.id if payment is not None else None,
        target_refund_id=refund.id,
        target_game_credit_id=None,
        target_venue_id=None,
        target_venue_image_id=None,
        target_notification_id=None,
    )


def create_admin_financial_outcome(
    db: Session,
    *,
    admin_user: User,
    payload: AdminMoneyFinancialOutcomeCreate,
) -> AdminMoneyFinancialOutcomeRead:
    outcome, reason, internal_note, idempotency_key = (
        validate_financial_outcome_payload(payload)
    )
    existing_outcome = get_existing_financial_outcome(
        db,
        admin_user_id=admin_user.id,
        idempotency_key=idempotency_key,
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

    if outcome in {"refund", "credit", "forfeit"} and amount_cents <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{outcome} outcomes require amount_cents greater than 0.",
        )

    if outcome == "refund":
        host_publish_fee, payment = validate_refund_outcome_context(
            db,
            host_publish_fee=host_publish_fee,
            payment=payment,
            amount_cents=amount_cents,
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
        )
        stage_financial_outcome_support_flag(
            db,
            financial_outcome=financial_outcome,
            refund=refund,
            payment=payment,
            admin_user=admin_user,
            admin_action=admin_action,
        )
        db.commit()
        db.refresh(financial_outcome)
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_financial_outcome_conflict_detail(exc),
        ) from exc

    return AdminMoneyFinancialOutcomeRead.model_validate(financial_outcome)
