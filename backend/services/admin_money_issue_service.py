"""Admin money issue staging, resolution, and retry workflows."""

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import (
    AdminAction,
    AdminFinancialOutcome,
    Booking,
    Game,
    GameCredit,
    GameCreditUsage,
    HostPublishEntitlement,
    HostPublishFee,
    MoneyIssue,
    MoneyIssueEvent,
    Payment,
    PaymentCompensation,
    Refund,
    RefundEvent,
    User,
)
from backend.schemas.admin_money_issue_detail_schema import AdminMoneyIssueDetailRead
from backend.schemas.admin_money_issue_schema import (
    AdminMoneyIssueCreditRetryCreate,
    AdminMoneyIssueResolveCreate,
)
from backend.services.admin_action_service import (
    build_admin_action_conflict_detail,
    record_admin_action,
)
from backend.services.admin_money_issue_query_service import (
    get_admin_money_issue_detail,
)
from backend.services.admin_money_issue_rules import (
    ISSUE_DEFAULTS,
    ISSUE_RESOLUTION_REASONS,
    build_credit_release_issue_operation_key,
    build_credit_restore_issue_operation_key,
    build_refund_issue_operation_key,
    detection_event_type,
)
from backend.services.admin_record_rules import (
    normalize_idempotency_key,
    normalize_optional_text,
)
from backend.services.game_credit_service import (
    GameCreditLedgerError,
    release_reserved_game_credit_usage,
    restore_redeemed_game_credit_usage,
)
from backend.services.publish_fee_financial_policy import (
    active_publish_fee_sibling_outcome,
    publish_fee_prior_cash_attempts_are_incapable,
)
from backend.services.refund_attempt_policy import (
    authoritative_succeeded_amount_for_refunds,
    refund_attempt_statuses,
    refund_expected_attempts_are_terminal,
    refund_has_only_terminal_attempts,
)
from backend.services.refund_service import get_refund_payment_ledger


def refund_issue_action_under_publish_fee_policy(
    db: Session, *, refund: Refund, default_action: str
) -> tuple[str, str | None, str | None]:
    sibling = active_publish_fee_sibling_outcome(db, refund=refund)
    if sibling is None:
        return default_action, None, None
    return (
        "review_superseding_financial_outcome",
        "superseded_by_financial_outcome",
        "A later authoritative publish-fee decision blocks further cash-refund work.",
    )


def get_money_issue_for_update_or_404(
    db: Session,
    money_issue_id: uuid.UUID,
) -> MoneyIssue:
    money_issue = db.scalars(
        select(MoneyIssue).where(MoneyIssue.id == money_issue_id).with_for_update()
    ).first()
    if money_issue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Money issue not found.",
        )
    return money_issue


def get_money_issue_with_financial_context_for_update_or_404(
    db: Session, money_issue_id: uuid.UUID
) -> MoneyIssue:
    reference = db.get(MoneyIssue, money_issue_id)
    if reference is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Money issue not found.",
        )
    if reference.target_game_id is not None:
        db.scalar(
            select(Game).where(Game.id == reference.target_game_id).with_for_update()
        )
    if reference.target_booking_id is not None:
        db.scalar(
            select(Booking)
            .where(Booking.id == reference.target_booking_id)
            .with_for_update()
        )
    if reference.target_payment_id is not None:
        db.scalar(
            select(Payment)
            .where(Payment.id == reference.target_payment_id)
            .with_for_update()
        )
    refund_reference = (
        db.get(Refund, reference.target_refund_id)
        if reference.target_refund_id is not None
        else None
    )
    if refund_reference is not None and refund_reference.host_publish_fee_id is not None:
        db.scalar(
            select(HostPublishFee)
            .where(HostPublishFee.id == refund_reference.host_publish_fee_id)
            .with_for_update()
        )
    if refund_reference is not None:
        related_refunds = list(
            db.scalars(
                select(Refund)
                .where(
                    Refund.host_publish_fee_id
                    == refund_reference.host_publish_fee_id
                    if refund_reference.host_publish_fee_id is not None
                    else Refund.id == refund_reference.id
                )
                .order_by(Refund.id.asc())
                .with_for_update()
            ).all()
        )
        related_refund_ids = [refund.id for refund in related_refunds]
        list(
            db.scalars(
                select(AdminFinancialOutcome)
                .where(
                    AdminFinancialOutcome.host_publish_fee_id
                    == refund_reference.host_publish_fee_id
                )
                .order_by(AdminFinancialOutcome.id.asc())
                .with_for_update()
            ).all()
        )
        related_issues = list(
            db.scalars(
                select(MoneyIssue)
                .where(MoneyIssue.target_refund_id.in_(related_refund_ids))
                .order_by(MoneyIssue.id.asc())
                .with_for_update()
            ).all()
        )
        selected = next(
            (issue for issue in related_issues if issue.id == money_issue_id), None
        )
        if selected is not None:
            return selected
    return get_money_issue_for_update_or_404(db, money_issue_id)


def get_existing_money_issue_action(
    db: Session,
    *,
    admin_user_id: uuid.UUID,
    money_issue_id: uuid.UUID,
    action_type: str,
    idempotency_key: str,
) -> AdminAction | None:
    return db.scalars(
        select(AdminAction)
        .where(
            AdminAction.admin_user_id == admin_user_id,
            AdminAction.action_type == action_type,
            AdminAction.target_money_issue_id == money_issue_id,
            AdminAction.idempotency_key == idempotency_key,
        )
        .order_by(AdminAction.created_at.desc(), AdminAction.id.desc())
    ).first()


def append_money_issue_event(
    db: Session,
    *,
    money_issue: MoneyIssue,
    event_type: str,
    event_source: str,
    reason_code: str,
    summary: str,
    actor_user_id: uuid.UUID | None = None,
    admin_action_id: uuid.UUID | None = None,
    refund_event_id: uuid.UUID | None = None,
    result_credit_usage_id: uuid.UUID | None = None,
    previous_status: str | None = None,
    new_status: str | None = None,
    previous_issue_type: str | None = None,
    new_issue_type: str | None = None,
    previous_recommended_action_code: str | None = None,
    new_recommended_action_code: str | None = None,
    metadata: dict[str, Any] | None = None,
    occurred_at: datetime | None = None,
) -> MoneyIssueEvent:
    now = occurred_at or datetime.now(timezone.utc)
    event = MoneyIssueEvent(
        id=uuid.uuid4(),
        money_issue_id=money_issue.id,
        event_type=event_type,
        event_source=event_source,
        actor_user_id=actor_user_id,
        admin_action_id=admin_action_id,
        refund_event_id=refund_event_id,
        result_credit_usage_id=result_credit_usage_id,
        previous_status=previous_status,
        new_status=new_status,
        previous_issue_type=previous_issue_type,
        new_issue_type=new_issue_type,
        previous_recommended_action_code=previous_recommended_action_code,
        new_recommended_action_code=new_recommended_action_code,
        reason_code=reason_code,
        summary=summary,
        event_metadata=metadata,
        occurred_at=now,
        created_at=now,
    )
    money_issue.last_activity_at = now
    money_issue.updated_at = now
    db.add(money_issue)
    db.add(event)
    db.flush()
    return event


def financial_outcome_safely_supersedes_refund(
    db: Session,
    *,
    refund: Refund,
    replacement: AdminFinancialOutcome,
) -> bool:
    if (
        refund.host_publish_fee_id is None
        or replacement.host_publish_fee_id != refund.host_publish_fee_id
        or replacement.applied_status != "applied"
        or replacement.outcome not in {"credit", "forfeit", "refund"}
        or not publish_fee_prior_cash_attempts_are_incapable(
            db,
            host_publish_fee_id=refund.host_publish_fee_id,
            excluding_refund_id=replacement.refund_id,
        )
    ):
        return False
    fee = db.get(HostPublishFee, refund.host_publish_fee_id)
    if (
        fee is None
        or replacement.amount_cents != fee.amount_cents
        or replacement.currency != fee.currency
    ):
        return False
    if replacement.outcome == "forfeit":
        return True
    if replacement.outcome == "credit":
        if replacement.host_publish_entitlement_id is None:
            return False
        entitlement = db.get(
            HostPublishEntitlement, replacement.host_publish_entitlement_id
        )
        return bool(
            entitlement is not None
            and entitlement.id == replacement.host_publish_entitlement_id
            and entitlement.host_user_id == replacement.host_user_id
            and entitlement.entitlement_type == "refund_replacement"
            and entitlement.source == "financial_outcome"
            and entitlement.source_financial_outcome_id == replacement.id
            and entitlement.status != "revoked"
        )
    if replacement.refund_id is None:
        return False
    replacement_refund = db.get(Refund, replacement.refund_id)
    if (
        replacement_refund is None
        or not refund_expected_attempts_are_terminal(db, replacement_refund)
    ):
        return False
    returned = authoritative_succeeded_amount_for_refunds(
        db, (replacement_refund,)
    )
    return returned >= replacement.amount_cents


def refund_payment_no_action_obligation_is_satisfied(
    db: Session,
    *,
    refund: Refund,
    payment: Payment | None = None,
) -> bool:
    """Prove that payment-wide cash and compensation work is complete."""
    if not refund_has_only_terminal_attempts(db, refund):
        return False
    resolved_payment = payment or db.get(Payment, refund.payment_id)
    if resolved_payment is None:
        return False
    compensation = db.scalars(
        select(PaymentCompensation).where(PaymentCompensation.refund_id == refund.id)
    ).first()
    ledger = get_refund_payment_ledger(
        db,
        payment_id=resolved_payment.id,
        payment_amount_cents=resolved_payment.amount_cents,
    )
    return bool(
        ledger.confirmed_returned_cents >= resolved_payment.amount_cents
        and ledger.reserved_cents == 0
        and ledger.unresolved_attempt_cents == 0
        and (compensation is None or compensation.status == "succeeded")
    )


def stage_refund_money_issue(
    db: Session,
    *,
    refund: Refund,
    payment: Payment | None,
    issue_type: str,
    reason_code: str,
    summary: str,
    refund_event: RefundEvent | None = None,
    admin_action: AdminAction | None = None,
    now: datetime | None = None,
) -> MoneyIssue:
    if issue_type not in ISSUE_DEFAULTS or not issue_type.startswith("refund_"):
        raise ValueError("Unsupported refund money issue type.")

    detected_at = now or datetime.now(timezone.utc)
    value_kind, recommended_action_code = ISSUE_DEFAULTS[issue_type]
    active_sibling = active_publish_fee_sibling_outcome(db, refund=refund)
    if active_sibling is not None:
        recommended_action_code = "review_superseding_financial_outcome"
        reason_code = "superseded_by_financial_outcome"
        summary = (
            "A later authoritative publish-fee decision blocks this cash refund "
            "until the complete fee outcome is settled."
        )
    operation_key = build_refund_issue_operation_key(refund.id)
    target_booking_id = refund.booking_id or (
        payment.booking_id if payment is not None else None
    )
    target_game_id = payment.game_id if payment is not None else None
    if target_game_id is None and target_booking_id is not None:
        booking = db.get(Booking, target_booking_id)
        target_game_id = booking.game_id if booking is not None else None
    money_issue = db.scalars(
        select(MoneyIssue)
        .where(MoneyIssue.operation_key == operation_key)
        .with_for_update()
    ).first()

    if money_issue is not None and money_issue.status == "resolved":
        if money_issue.resolution_reason_code == "retried_successfully":
            returned = authoritative_succeeded_amount_for_refunds(db, (refund,))
            if (
                returned >= refund.amount_cents
                and refund_expected_attempts_are_terminal(db, refund)
            ):
                return money_issue
        if (
            money_issue.resolution_reason_code
            == "provider_completed_no_action_required"
            and refund_payment_no_action_obligation_is_satisfied(
                db,
                refund=refund,
                payment=payment,
            )
        ):
            return money_issue
        if money_issue.resolution_reason_code == "superseded_by_financial_outcome":
            replacements = list(
                db.scalars(
                select(AdminFinancialOutcome).where(
                    AdminFinancialOutcome.host_publish_fee_id
                    == refund.host_publish_fee_id,
                    or_(
                        AdminFinancialOutcome.refund_id.is_(None),
                        AdminFinancialOutcome.refund_id != refund.id,
                    ),
                    AdminFinancialOutcome.applied_status == "applied",
                )
                ).all()
            )
            if any(
                financial_outcome_safely_supersedes_refund(
                    db, refund=refund, replacement=replacement
                )
                for replacement in replacements
            ):
                return money_issue

    if money_issue is None:
        money_issue = MoneyIssue(
            id=uuid.uuid4(),
            operation_key=operation_key,
            status="open",
            issue_type=issue_type,
            origin_workflow=refund.origin_workflow,
            value_kind=value_kind,
            amount_cents=refund.amount_cents,
            currency=refund.currency,
            target_user_id=payment.payer_user_id if payment is not None else None,
            target_game_id=target_game_id,
            target_booking_id=target_booking_id,
            target_payment_id=refund.payment_id,
            target_refund_id=refund.id,
            target_game_credit_id=None,
            target_credit_usage_id=None,
            latest_reason_code=reason_code,
            latest_summary=summary,
            recommended_action_code=recommended_action_code,
            occurrence_count=1,
            reopen_count=0,
            first_detected_at=detected_at,
            last_detected_at=detected_at,
            last_activity_at=detected_at,
            created_at=detected_at,
            updated_at=detected_at,
        )
        db.add(money_issue)
        db.flush()
        append_money_issue_event(
            db,
            money_issue=money_issue,
            event_type="issue_opened",
            event_source="system",
            actor_user_id=admin_action.admin_user_id
            if admin_action is not None
            else None,
            admin_action_id=admin_action.id if admin_action is not None else None,
            refund_event_id=refund_event.id if refund_event is not None else None,
            reason_code=reason_code,
            summary=summary,
            new_status="open",
            new_issue_type=issue_type,
            new_recommended_action_code=recommended_action_code,
        )
        return money_issue

    previous_status = money_issue.status
    previous_issue_type = money_issue.issue_type
    previous_action = money_issue.recommended_action_code
    money_issue.status = "open"
    money_issue.issue_type = issue_type
    money_issue.origin_workflow = refund.origin_workflow
    money_issue.value_kind = value_kind
    money_issue.amount_cents = refund.amount_cents
    money_issue.currency = refund.currency
    money_issue.target_user_id = payment.payer_user_id if payment is not None else None
    money_issue.target_game_id = target_game_id
    money_issue.target_booking_id = target_booking_id
    money_issue.target_payment_id = refund.payment_id
    money_issue.target_refund_id = refund.id
    money_issue.latest_reason_code = reason_code
    money_issue.latest_summary = summary
    money_issue.recommended_action_code = recommended_action_code
    money_issue.occurrence_count += 1
    money_issue.last_detected_at = detected_at
    money_issue.resolved_at = None
    money_issue.resolved_by_user_id = None
    money_issue.resolution_reason_code = None
    money_issue.resolution_note = None
    money_issue.resolution_external_reference = None
    if previous_status == "resolved":
        money_issue.reopen_count += 1

    append_money_issue_event(
        db,
        money_issue=money_issue,
        event_type=detection_event_type(
            previous_status=previous_status,
            previous_issue_type=previous_issue_type,
            issue_type=issue_type,
            previous_action=previous_action,
            recommended_action_code=recommended_action_code,
            fallback_event_type="refund_outcome_linked"
            if refund_event is not None
            else "recommended_action_changed",
        ),
        event_source="system",
        actor_user_id=admin_action.admin_user_id if admin_action is not None else None,
        admin_action_id=admin_action.id if admin_action is not None else None,
        refund_event_id=refund_event.id if refund_event is not None else None,
        reason_code=reason_code,
        summary=summary,
        previous_status=previous_status,
        new_status="open",
        previous_issue_type=previous_issue_type,
        new_issue_type=issue_type,
        previous_recommended_action_code=previous_action,
        new_recommended_action_code=recommended_action_code,
    )
    return money_issue


def stage_credit_money_issue(
    db: Session,
    *,
    credit_usage: GameCreditUsage,
    game_credit: GameCredit | None,
    issue_type: str,
    origin_workflow: str,
    reason_code: str,
    summary: str,
    admin_action: AdminAction | None = None,
    now: datetime | None = None,
) -> MoneyIssue:
    if issue_type not in ISSUE_DEFAULTS or not issue_type.startswith("credit_"):
        raise ValueError("Unsupported credit money issue type.")

    detected_at = now or datetime.now(timezone.utc)
    value_kind, recommended_action_code = ISSUE_DEFAULTS[issue_type]
    if origin_workflow in {"official_game_cancellation", "player_removal"}:
        recommended_action_code = "reexecute_origin_workflow"
    operation_key = (
        build_credit_release_issue_operation_key(credit_usage.id)
        if issue_type == "credit_release_failed"
        else build_credit_restore_issue_operation_key(credit_usage.id)
    )
    money_issue = db.scalars(
        select(MoneyIssue)
        .where(MoneyIssue.operation_key == operation_key)
        .with_for_update()
    ).first()
    target_user_id = game_credit.user_id if game_credit is not None else None

    if money_issue is None:
        money_issue = MoneyIssue(
            id=uuid.uuid4(),
            operation_key=operation_key,
            status="open",
            issue_type=issue_type,
            origin_workflow=origin_workflow,
            value_kind=value_kind,
            amount_cents=credit_usage.amount_cents,
            currency=credit_usage.currency,
            target_user_id=target_user_id,
            target_game_id=credit_usage.game_id,
            target_booking_id=credit_usage.booking_id,
            target_payment_id=credit_usage.payment_id,
            target_refund_id=None,
            target_game_credit_id=credit_usage.game_credit_id,
            target_credit_usage_id=credit_usage.id,
            latest_reason_code=reason_code,
            latest_summary=summary,
            recommended_action_code=recommended_action_code,
            occurrence_count=1,
            reopen_count=0,
            first_detected_at=detected_at,
            last_detected_at=detected_at,
            last_activity_at=detected_at,
            created_at=detected_at,
            updated_at=detected_at,
        )
        db.add(money_issue)
        db.flush()
        append_money_issue_event(
            db,
            money_issue=money_issue,
            event_type="issue_opened",
            event_source="system",
            actor_user_id=admin_action.admin_user_id
            if admin_action is not None
            else None,
            admin_action_id=admin_action.id if admin_action is not None else None,
            reason_code=reason_code,
            summary=summary,
            new_status="open",
            new_issue_type=issue_type,
            new_recommended_action_code=recommended_action_code,
        )
        return money_issue

    previous_status = money_issue.status
    previous_issue_type = money_issue.issue_type
    previous_action = money_issue.recommended_action_code
    money_issue.status = "open"
    money_issue.issue_type = issue_type
    money_issue.origin_workflow = origin_workflow
    money_issue.value_kind = value_kind
    money_issue.amount_cents = credit_usage.amount_cents
    money_issue.currency = credit_usage.currency
    money_issue.target_user_id = target_user_id
    money_issue.target_game_id = credit_usage.game_id
    money_issue.target_booking_id = credit_usage.booking_id
    money_issue.target_payment_id = credit_usage.payment_id
    money_issue.target_game_credit_id = credit_usage.game_credit_id
    money_issue.target_credit_usage_id = credit_usage.id
    money_issue.latest_reason_code = reason_code
    money_issue.latest_summary = summary
    money_issue.recommended_action_code = recommended_action_code
    money_issue.occurrence_count += 1
    money_issue.last_detected_at = detected_at
    money_issue.resolved_at = None
    money_issue.resolved_by_user_id = None
    money_issue.resolution_reason_code = None
    money_issue.resolution_note = None
    money_issue.resolution_external_reference = None
    if previous_status == "resolved":
        money_issue.reopen_count += 1
    append_money_issue_event(
        db,
        money_issue=money_issue,
        event_type=detection_event_type(
            previous_status=previous_status,
            previous_issue_type=previous_issue_type,
            issue_type=issue_type,
            previous_action=previous_action,
            recommended_action_code=recommended_action_code,
            fallback_event_type=issue_type,
        ),
        event_source="system",
        actor_user_id=admin_action.admin_user_id if admin_action is not None else None,
        admin_action_id=admin_action.id if admin_action is not None else None,
        reason_code=reason_code,
        summary=summary,
        previous_status=previous_status,
        new_status="open",
        previous_issue_type=previous_issue_type,
        new_issue_type=issue_type,
        previous_recommended_action_code=previous_action,
        new_recommended_action_code=recommended_action_code,
    )
    return money_issue


def money_issue_has_successful_credit_retry(
    db: Session, money_issue: MoneyIssue
) -> bool:
    if money_issue.target_credit_usage_id is None:
        return False

    if money_issue.issue_type == "credit_release_failed":
        target_usage = db.get(GameCreditUsage, money_issue.target_credit_usage_id)
        return target_usage is not None and target_usage.usage_status == "released"

    if money_issue.issue_type == "credit_restore_failed":
        restored_usage = db.scalars(
            select(GameCreditUsage)
            .where(
                GameCreditUsage.original_usage_id == money_issue.target_credit_usage_id,
                GameCreditUsage.usage_type == "restore",
                GameCreditUsage.usage_status == "restored",
            )
            .limit(1)
        ).first()
        return restored_usage is not None

    return False


def resolve_reexecuted_origin_credit_issues(
    db: Session,
    *,
    origin_workflow: str,
    target_game_id: uuid.UUID,
    target_booking_id: uuid.UUID | None,
    admin_action: AdminAction,
    now: datetime,
) -> list[uuid.UUID]:
    """Resolve rollback markers only after their origin workflow returned credit."""
    filters = [
        MoneyIssue.target_game_id == target_game_id,
        MoneyIssue.status == "open",
        MoneyIssue.origin_workflow == origin_workflow,
        MoneyIssue.recommended_action_code == "reexecute_origin_workflow",
        MoneyIssue.issue_type.in_({"credit_release_failed", "credit_restore_failed"}),
    ]
    if target_booking_id is not None:
        filters.append(MoneyIssue.target_booking_id == target_booking_id)
    issues = list(
        db.scalars(
            select(MoneyIssue)
            .where(*filters)
            .order_by(MoneyIssue.id.asc())
            .with_for_update()
        ).all()
    )
    resolved_ids: list[uuid.UUID] = []
    for issue in issues:
        if not money_issue_has_successful_credit_retry(db, issue):
            continue
        result_usage_id = issue.target_credit_usage_id
        if issue.issue_type == "credit_restore_failed":
            restored = db.scalars(
                select(GameCreditUsage)
                .where(
                    GameCreditUsage.original_usage_id == issue.target_credit_usage_id,
                    GameCreditUsage.usage_type == "restore",
                    GameCreditUsage.usage_status == "restored",
                )
                .limit(1)
            ).first()
            result_usage_id = restored.id if restored is not None else None
        issue.status = "resolved"
        issue.resolved_at = now
        issue.resolved_by_user_id = admin_action.admin_user_id
        issue.resolution_reason_code = "retried_successfully"
        issue.resolution_note = "Origin workflow re-execution returned the credit."
        issue.resolution_external_reference = None
        issue.latest_reason_code = "origin_workflow_reexecuted"
        issue.latest_summary = "Origin workflow re-execution returned the credit."
        issue.last_activity_at = now
        issue.updated_at = now
        append_money_issue_event(
            db,
            money_issue=issue,
            event_type="issue_resolved",
            event_source="admin",
            actor_user_id=admin_action.admin_user_id,
            admin_action_id=admin_action.id,
            result_credit_usage_id=result_usage_id,
            reason_code="retried_successfully",
            summary=issue.resolution_note,
            previous_status="open",
            new_status="resolved",
            previous_recommended_action_code="reexecute_origin_workflow",
            new_recommended_action_code="review_and_resolve_no_action",
            occurred_at=now,
        )
        issue.recommended_action_code = "review_and_resolve_no_action"
        db.add(issue)
        resolved_ids.append(issue.id)
    return resolved_ids


def validate_money_issue_resolution(
    db: Session,
    *,
    money_issue: MoneyIssue,
    resolution_reason_code: str,
    resolution_note: str | None,
    resolution_external_reference: str | None,
) -> AdminFinancialOutcome | None:
    if resolution_reason_code not in ISSUE_RESOLUTION_REASONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="resolution_reason_code is not supported.",
        )

    if resolution_reason_code == "handled_externally":
        if resolution_note is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="handled_externally requires resolution_note.",
            )
        if resolution_external_reference is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="handled_externally requires resolution_external_reference.",
            )
        return None

    if resolution_reason_code in {"invalid_issue", "unable_to_complete_documented"}:
        if resolution_note is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{resolution_reason_code} requires resolution_note.",
            )
        return None

    if resolution_reason_code == "superseded_by_financial_outcome":
        if money_issue.target_refund_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Superseded resolution requires a related refund.",
            )
        refund = db.get(Refund, money_issue.target_refund_id)
        if refund is None or refund.host_publish_fee_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Superseded resolution requires publish-fee refund context.",
            )
        replacements = list(
            db.scalars(
            select(AdminFinancialOutcome).where(
                AdminFinancialOutcome.host_publish_fee_id
                == refund.host_publish_fee_id,
                or_(
                    AdminFinancialOutcome.refund_id.is_(None),
                    AdminFinancialOutcome.refund_id != refund.id,
                ),
                AdminFinancialOutcome.applied_status == "applied",
            )
            ).all()
        )
        replacement = next(
            (
                candidate
                for candidate in replacements
                if financial_outcome_safely_supersedes_refund(
                    db, refund=refund, replacement=candidate
                )
            ),
            None,
        )
        if replacement is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A verified applied replacement financial outcome is required.",
            )
        return replacement

    if resolution_reason_code == "retried_successfully":
        if money_issue.issue_type.startswith("refund_"):
            if money_issue.target_refund_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Refund issue is missing refund context.",
                )
            refund = db.get(Refund, money_issue.target_refund_id)
            if (
                refund is None
                or refund.refund_status != "succeeded"
                or not refund_expected_attempts_are_terminal(db, refund)
                or refund_attempt_statuses(db, refund.id).get(
                    refund.current_attempt_number
                )
                != "succeeded"
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"{resolution_reason_code} requires the related refund "
                        "to be succeeded."
                    ),
                )
            return

        if money_issue.issue_type.startswith("credit_"):
            if not money_issue_has_successful_credit_retry(db, money_issue):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"{resolution_reason_code} requires the related credit "
                        "movement to be completed."
                    ),
                )
            return

    if resolution_reason_code == "provider_completed_no_action_required":
        if not money_issue.issue_type.startswith("refund_") or money_issue.target_refund_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provider no-action resolution requires refund context.",
            )
        refund = db.get(Refund, money_issue.target_refund_id)
        if refund is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provider no-action resolution is missing its refund.",
            )
        payment = db.get(Payment, refund.payment_id)
        if not refund_payment_no_action_obligation_is_satisfied(
            db,
            refund=refund,
            payment=payment,
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Provider no-action resolution requires the payment obligation to be satisfied.",
            )
        return

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Money issue resolution is not valid for this issue.",
    )


def resolve_admin_money_issue(
    db: Session,
    *,
    admin_user: User,
    money_issue_id: uuid.UUID,
    payload: AdminMoneyIssueResolveCreate,
) -> AdminMoneyIssueDetailRead:
    resolution_reason_code = normalize_optional_text(
        payload.resolution_reason_code,
        "resolution_reason_code",
        max_length=80,
    )
    resolution_note = normalize_optional_text(
        payload.resolution_note,
        "resolution_note",
        max_length=1000,
    )
    resolution_external_reference = normalize_optional_text(
        payload.resolution_external_reference,
        "resolution_external_reference",
        max_length=255,
    )
    idempotency_key = normalize_idempotency_key(payload.idempotency_key)
    if resolution_reason_code is None or idempotency_key is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid resolution payload.",
        )

    existing_action = get_existing_money_issue_action(
        db,
        admin_user_id=admin_user.id,
        money_issue_id=money_issue_id,
        action_type="resolve_money_issue",
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        return get_admin_money_issue_detail(db, money_issue_id=money_issue_id)

    money_issue = get_money_issue_with_financial_context_for_update_or_404(
        db, money_issue_id
    )
    existing_action = get_existing_money_issue_action(
        db,
        admin_user_id=admin_user.id,
        money_issue_id=money_issue_id,
        action_type="resolve_money_issue",
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        return get_admin_money_issue_detail(db, money_issue_id=money_issue_id)
    if money_issue.status == "resolved":
        return get_admin_money_issue_detail(db, money_issue_id=money_issue.id)
    replacement_financial_outcome = validate_money_issue_resolution(
        db,
        money_issue=money_issue,
        resolution_reason_code=resolution_reason_code,
        resolution_note=resolution_note,
        resolution_external_reference=resolution_external_reference,
    )

    now = datetime.now(timezone.utc)
    previous_status = money_issue.status
    admin_action = record_admin_action(
        db,
        admin_user_id=admin_user.id,
        action_type="resolve_money_issue",
        outcome="succeeded",
        target_user_id=money_issue.target_user_id,
        target_game_id=money_issue.target_game_id,
        target_booking_id=money_issue.target_booking_id,
        target_payment_id=money_issue.target_payment_id,
        target_refund_id=money_issue.target_refund_id,
        target_game_credit_id=money_issue.target_game_credit_id,
        target_credit_usage_id=money_issue.target_credit_usage_id,
        target_money_issue_id=money_issue.id,
        reason=resolution_note or resolution_reason_code,
        idempotency_key=idempotency_key,
        metadata={
            "old_status": previous_status,
            "new_status": "resolved",
            "resolution_reason_code": resolution_reason_code,
            "resolution_external_reference": resolution_external_reference,
            "replacement_financial_outcome_id": (
                str(replacement_financial_outcome.id)
                if replacement_financial_outcome is not None
                else None
            ),
            "source": "admin_money_issue_resolve",
        },
    )
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        existing_action = get_existing_money_issue_action(
            db,
            admin_user_id=admin_user.id,
            money_issue_id=money_issue_id,
            action_type="resolve_money_issue",
            idempotency_key=idempotency_key,
        )
        if existing_action is not None:
            return get_admin_money_issue_detail(db, money_issue_id=money_issue_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_admin_action_conflict_detail(exc),
        ) from exc
    money_issue.status = "resolved"
    money_issue.resolved_at = now
    money_issue.resolved_by_user_id = admin_user.id
    money_issue.resolution_reason_code = resolution_reason_code
    money_issue.resolution_note = resolution_note
    money_issue.resolution_external_reference = resolution_external_reference
    money_issue.updated_at = now
    append_money_issue_event(
        db,
        money_issue=money_issue,
        event_type="issue_resolved",
        event_source="admin",
        actor_user_id=admin_user.id,
        admin_action_id=admin_action.id,
        reason_code=resolution_reason_code,
        summary=resolution_note or "Money issue resolved.",
        previous_status=previous_status,
        new_status="resolved",
        metadata={
            "replacement_financial_outcome_id": str(
                replacement_financial_outcome.id
            )
        }
        if replacement_financial_outcome is not None
        else None,
    )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing_action = get_existing_money_issue_action(
            db,
            admin_user_id=admin_user.id,
            money_issue_id=money_issue_id,
            action_type="resolve_money_issue",
            idempotency_key=idempotency_key,
        )
        if existing_action is not None:
            return get_admin_money_issue_detail(db, money_issue_id=money_issue_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_admin_action_conflict_detail(exc),
        ) from exc

    return get_admin_money_issue_detail(db, money_issue_id=money_issue.id)


def retry_admin_money_issue_credit(
    db: Session,
    *,
    admin_user: User,
    money_issue_id: uuid.UUID,
    payload: AdminMoneyIssueCreditRetryCreate,
) -> AdminMoneyIssueDetailRead:
    reason = normalize_optional_text(payload.reason, "reason", max_length=1000)
    idempotency_key = normalize_idempotency_key(payload.idempotency_key)
    if reason is None or idempotency_key is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credit retry payload.",
        )

    existing_action = get_existing_money_issue_action(
        db,
        admin_user_id=admin_user.id,
        money_issue_id=money_issue_id,
        action_type="retry_money_issue_credit",
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        return get_admin_money_issue_detail(db, money_issue_id=money_issue_id)

    money_issue = get_money_issue_for_update_or_404(db, money_issue_id)
    existing_action = get_existing_money_issue_action(
        db,
        admin_user_id=admin_user.id,
        money_issue_id=money_issue_id,
        action_type="retry_money_issue_credit",
        idempotency_key=idempotency_key,
    )
    if existing_action is not None:
        return get_admin_money_issue_detail(db, money_issue_id=money_issue_id)
    if money_issue.status != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only open money issues can be retried.",
        )
    if money_issue.issue_type not in {"credit_restore_failed", "credit_release_failed"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Money issue is not a credit retry issue.",
        )
    if money_issue.recommended_action_code == "reexecute_origin_workflow":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This credit issue must be repaired by re-running its originating "
                "cancellation or player-removal preview."
            ),
        )
    if (
        money_issue.target_credit_usage_id is None
        or money_issue.target_booking_id is None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Credit retry issue is missing usage or booking context.",
        )

    target_usage = db.scalars(
        select(GameCreditUsage)
        .where(GameCreditUsage.id == money_issue.target_credit_usage_id)
        .with_for_update()
    ).first()
    if target_usage is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credit usage not found.",
        )

    target_credit = db.scalars(
        select(GameCredit)
        .where(GameCredit.id == target_usage.game_credit_id)
        .with_for_update()
    ).first()
    if target_credit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Game credit not found."
        )

    now = datetime.now(timezone.utc)
    retry_kind = (
        "release" if money_issue.issue_type == "credit_release_failed" else "restore"
    )
    try:
        admin_action = record_admin_action(
            db,
            admin_user_id=admin_user.id,
            action_type="retry_money_issue_credit",
            outcome="succeeded",
            target_user_id=money_issue.target_user_id,
            target_game_id=money_issue.target_game_id,
            target_booking_id=money_issue.target_booking_id,
            target_payment_id=money_issue.target_payment_id,
            target_game_credit_id=money_issue.target_game_credit_id,
            target_credit_usage_id=money_issue.target_credit_usage_id,
            target_money_issue_id=money_issue.id,
            reason=reason,
            idempotency_key=idempotency_key,
            metadata={
                "issue_type": money_issue.issue_type,
                "operation_key": money_issue.operation_key,
                "retry_kind": retry_kind,
                "source": "admin_money_issue_credit_retry",
            },
        )
        db.flush()
        append_money_issue_event(
            db,
            money_issue=money_issue,
            event_type="admin_retry_initiated",
            event_source="admin",
            actor_user_id=admin_user.id,
            admin_action_id=admin_action.id,
            reason_code="admin_retry_initiated",
            summary=reason,
            occurred_at=now,
        )

        if retry_kind == "release":
            result_usage = release_reserved_game_credit_usage(
                db,
                target_usage.id,
                now=now,
                reason_code="admin_retry_credit_release",
            )
        else:
            result_usage = restore_redeemed_game_credit_usage(
                db,
                target_usage.id,
                now=now,
                restore_reason="admin_retry_credit_restore",
            )

        if result_usage is None:
            raise GameCreditLedgerError("No eligible credit usage was retried.")

        previous_action = money_issue.recommended_action_code
        money_issue.latest_reason_code = f"admin_retry_credit_{retry_kind}_succeeded"
        money_issue.latest_summary = "Admin credit retry completed."
        money_issue.recommended_action_code = "review_and_resolve_no_action"
        money_issue.updated_at = now
        append_money_issue_event(
            db,
            money_issue=money_issue,
            event_type=f"credit_{retry_kind}_succeeded",
            event_source="admin",
            actor_user_id=admin_user.id,
            admin_action_id=admin_action.id,
            result_credit_usage_id=result_usage.id,
            reason_code=money_issue.latest_reason_code,
            summary="Admin credit retry completed.",
            previous_recommended_action_code=previous_action,
            new_recommended_action_code=money_issue.recommended_action_code,
            occurred_at=now,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing_action = get_existing_money_issue_action(
            db,
            admin_user_id=admin_user.id,
            money_issue_id=money_issue_id,
            action_type="retry_money_issue_credit",
            idempotency_key=idempotency_key,
        )
        if existing_action is not None:
            return get_admin_money_issue_detail(db, money_issue_id=money_issue_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=build_admin_action_conflict_detail(exc),
        ) from exc
    except GameCreditLedgerError as exc:
        db.rollback()
        failed_issue = get_money_issue_for_update_or_404(db, money_issue_id)
        failure_action = record_admin_action(
            db,
            admin_user_id=admin_user.id,
            action_type="retry_money_issue_credit",
            outcome="failed",
            target_user_id=failed_issue.target_user_id,
            target_game_id=failed_issue.target_game_id,
            target_booking_id=failed_issue.target_booking_id,
            target_payment_id=failed_issue.target_payment_id,
            target_game_credit_id=failed_issue.target_game_credit_id,
            target_credit_usage_id=failed_issue.target_credit_usage_id,
            target_money_issue_id=failed_issue.id,
            reason=reason,
            idempotency_key=idempotency_key,
            metadata={
                "issue_type": failed_issue.issue_type,
                "operation_key": failed_issue.operation_key,
                "retry_kind": retry_kind,
                "failure": "game_credit_ledger_error",
                "source": "admin_money_issue_credit_retry",
            },
        )
        try:
            db.flush()
        except IntegrityError as integrity_exc:
            db.rollback()
            existing_action = get_existing_money_issue_action(
                db,
                admin_user_id=admin_user.id,
                money_issue_id=money_issue_id,
                action_type="retry_money_issue_credit",
                idempotency_key=idempotency_key,
            )
            if existing_action is not None:
                return get_admin_money_issue_detail(db, money_issue_id=money_issue_id)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=build_admin_action_conflict_detail(integrity_exc),
            ) from integrity_exc
        failed_issue.latest_reason_code = f"admin_retry_credit_{retry_kind}_failed"
        failed_issue.latest_summary = str(exc)
        failed_issue.occurrence_count += 1
        failed_issue.last_detected_at = now
        failed_issue.updated_at = now
        append_money_issue_event(
            db,
            money_issue=failed_issue,
            event_type=f"credit_{retry_kind}_failed",
            event_source="admin",
            actor_user_id=admin_user.id,
            admin_action_id=failure_action.id,
            reason_code=failed_issue.latest_reason_code,
            summary=str(exc),
            occurred_at=now,
        )
        try:
            db.commit()
        except IntegrityError as integrity_exc:
            db.rollback()
            existing_action = get_existing_money_issue_action(
                db,
                admin_user_id=admin_user.id,
                money_issue_id=money_issue_id,
                action_type="retry_money_issue_credit",
                idempotency_key=idempotency_key,
            )
            if existing_action is not None:
                return get_admin_money_issue_detail(db, money_issue_id=money_issue_id)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=build_admin_action_conflict_detail(integrity_exc),
            ) from integrity_exc
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc

    return get_admin_money_issue_detail(db, money_issue_id=money_issue.id)
