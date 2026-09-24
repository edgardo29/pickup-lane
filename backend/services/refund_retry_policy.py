"""Shared refund retry eligibility for mutations and staff projections."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.models import HostPublishFee, Payment, Refund
from backend.services.admin_money_refund_rules import (
    RETRYABLE_PAYMENT_STATUSES,
    RETRYABLE_REFUND_STATUSES,
    UNCERTAIN_PROVIDER_REFUND_STATUSES,
)
from backend.services.publish_fee_financial_policy import (
    active_publish_fee_sibling_outcome,
)
from backend.services.refund_attempt_policy import refund_has_only_terminal_attempts
from backend.services.refund_service import get_refund_payment_ledger


@dataclass(frozen=True)
class RefundRetryBlocker:
    code: str
    message: str
    conflict: bool = False


@dataclass(frozen=True)
class RefundRetryEligibility:
    blockers: tuple[RefundRetryBlocker, ...]
    remaining_cents: int

    @property
    def mutation_allowed(self) -> bool:
        return not self.blockers

    @property
    def no_action_required(self) -> bool:
        return self.mutation_allowed and self.remaining_cents == 0

    @property
    def provider_retry_allowed(self) -> bool:
        return self.mutation_allowed and self.remaining_cents > 0


def evaluate_refund_retry_eligibility(
    db: Session,
    *,
    refund: Refund,
    payment: Payment | None,
) -> RefundRetryEligibility:
    blockers: list[RefundRetryBlocker] = []

    if refund.refund_status not in RETRYABLE_REFUND_STATUSES:
        blockers.append(
            RefundRetryBlocker(
                "refund_not_retryable", "Refund is not failed or cancelled."
            )
        )
    if refund.provider_status in UNCERTAIN_PROVIDER_REFUND_STATUSES:
        blockers.append(
            RefundRetryBlocker(
                "provider_outcome_uncertain",
                "Refund provider outcome is still uncertain.",
            )
        )
    if refund.automatic_mutation_blocked_reason is not None:
        blockers.append(
            RefundRetryBlocker(
                "automatic_mutation_blocked",
                "Refund has contradictory attempt history and requires reconciliation.",
                conflict=True,
            )
        )
    if not refund_has_only_terminal_attempts(db, refund):
        blockers.append(
            RefundRetryBlocker(
                "attempt_history_incomplete",
                "Refund attempt history does not prove every attempt is terminal.",
                conflict=True,
            )
        )

    if payment is None:
        blockers.append(
            RefundRetryBlocker("payment_missing", "Payment context is missing.")
        )
        return RefundRetryEligibility(tuple(blockers), 0)

    if payment.payment_status not in RETRYABLE_PAYMENT_STATUSES:
        blockers.append(
            RefundRetryBlocker("payment_not_succeeded", "Payment did not succeed.")
        )
    if payment.paid_at is None:
        blockers.append(
            RefundRetryBlocker("payment_not_paid", "Payment was not marked paid.")
        )
    if not payment.provider_charge_id:
        blockers.append(
            RefundRetryBlocker(
                "provider_charge_missing", "Payment is missing provider charge id."
            )
        )
    if refund.currency != payment.currency:
        blockers.append(
            RefundRetryBlocker(
                "currency_mismatch", "Refund currency must match the payment currency."
            )
        )
    if refund.booking_id is not None and refund.booking_id != payment.booking_id:
        blockers.append(
            RefundRetryBlocker(
                "booking_mismatch", "Refund booking must match the payment booking."
            )
        )

    if refund.host_publish_fee_id is not None:
        host_publish_fee = db.get(HostPublishFee, refund.host_publish_fee_id)
        if host_publish_fee is None:
            blockers.append(
                RefundRetryBlocker(
                    "publish_fee_missing", "Refund retry requires a host publish fee."
                )
            )
        else:
            if payment.payment_type != "community_publish_fee":
                blockers.append(
                    RefundRetryBlocker(
                        "payment_type_mismatch",
                        "Refund retry requires a community publish fee payment.",
                    )
                )
            if host_publish_fee.payment_id != payment.id:
                blockers.append(
                    RefundRetryBlocker(
                        "publish_fee_payment_mismatch",
                        "Host publish fee payment must match the refund payment.",
                    )
                )
            if host_publish_fee.host_user_id != payment.payer_user_id:
                blockers.append(
                    RefundRetryBlocker(
                        "publish_fee_payer_mismatch",
                        "Host publish fee payment must use the host as payer.",
                    )
                )
        if active_publish_fee_sibling_outcome(db, refund=refund) is not None:
            blockers.append(
                RefundRetryBlocker(
                    "active_publish_fee_sibling",
                    "Another active publish-fee financial decision supersedes this refund.",
                    conflict=True,
                )
            )
    elif payment.booking_id is None:
        blockers.append(
            RefundRetryBlocker(
                "booking_payment_required", "Refund retry requires a booking payment."
            )
        )

    ledger = get_refund_payment_ledger(
        db,
        payment_id=payment.id,
        payment_amount_cents=payment.amount_cents,
        exclude_refund_id=refund.id,
    )
    if ledger.reserved_cents > 0 or ledger.unresolved_attempt_cents > 0:
        blockers.append(
            RefundRetryBlocker(
                "sibling_refund_reservation",
                "Another refund attempt may still return value for this payment.",
                conflict=True,
            )
        )
    return RefundRetryEligibility(
        tuple(blockers), min(refund.amount_cents, ledger.available_cents)
    )
