"""Shared read-only policy for publish-fee replacement decisions."""

from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.models import AdminFinancialOutcome, Refund
from backend.services.refund_attempt_policy import refund_has_only_unsuccessful_attempts

ACTIVE_FINANCIAL_DECISION_STATUSES = frozenset({"pending", "applied", "not_applicable"})


def active_publish_fee_sibling_outcome(
    db: Session, *, refund: Refund
) -> AdminFinancialOutcome | None:
    if refund.host_publish_fee_id is None:
        return None
    return db.scalars(
        select(AdminFinancialOutcome)
        .where(
            AdminFinancialOutcome.host_publish_fee_id == refund.host_publish_fee_id,
            AdminFinancialOutcome.applied_status.in_(ACTIVE_FINANCIAL_DECISION_STATUSES),
            or_(
                AdminFinancialOutcome.refund_id.is_(None),
                AdminFinancialOutcome.refund_id != refund.id,
            ),
        )
        .order_by(AdminFinancialOutcome.created_at.desc(), AdminFinancialOutcome.id.desc())
    ).first()


def publish_fee_prior_cash_attempts_are_incapable(
    db: Session,
    *,
    host_publish_fee_id: uuid.UUID,
    excluding_refund_id: uuid.UUID | None = None,
) -> bool:
    query = select(Refund).where(Refund.host_publish_fee_id == host_publish_fee_id)
    if excluding_refund_id is not None:
        query = query.where(Refund.id != excluding_refund_id)
    refunds = list(db.scalars(query.order_by(Refund.id.asc()).with_for_update()).all())
    return all(
        refund.refund_status in {"failed", "cancelled"}
        and refund_has_only_unsuccessful_attempts(db, refund)
        for refund in refunds
    )
