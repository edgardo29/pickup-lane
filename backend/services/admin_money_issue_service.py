"""Admin money issue staging, resolution, and retry workflows."""

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
    GameCredit,
    GameCreditUsage,
    MoneyIssue,
    MoneyIssueEvent,
    Payment,
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
from backend.services.admin_money_issue_query_service import get_admin_money_issue_detail
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
    operation_key = build_refund_issue_operation_key(refund.id)
    target_booking_id = refund.booking_id or (payment.booking_id if payment is not None else None)
    target_game_id = payment.game_id if payment is not None else None
    if target_game_id is None:
        if target_booking_id is not None:
            booking = db.get(Booking, target_booking_id)
            target_game_id = booking.game_id if booking is not None else None
    money_issue = db.scalars(
        select(MoneyIssue).where(MoneyIssue.operation_key == operation_key).with_for_update()
    ).first()

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
            actor_user_id=admin_action.admin_user_id if admin_action is not None else None,
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
    operation_key = (
        build_credit_release_issue_operation_key(credit_usage.id)
        if issue_type == "credit_release_failed"
        else build_credit_restore_issue_operation_key(credit_usage.id)
    )
    money_issue = db.scalars(
        select(MoneyIssue).where(MoneyIssue.operation_key == operation_key).with_for_update()
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
            actor_user_id=admin_action.admin_user_id if admin_action is not None else None,
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


def money_issue_has_successful_credit_retry(db: Session, money_issue: MoneyIssue) -> bool:
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


def validate_money_issue_resolution(
    db: Session,
    *,
    money_issue: MoneyIssue,
    resolution_reason_code: str,
    resolution_note: str | None,
    resolution_external_reference: str | None,
) -> None:
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
        return

    if resolution_reason_code in {"invalid_issue", "unable_to_complete_documented"}:
        if resolution_note is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{resolution_reason_code} requires resolution_note.",
            )
        return

    if resolution_reason_code in {
        "retried_successfully",
        "provider_completed_no_action_required",
    }:
        if money_issue.issue_type.startswith("refund_"):
            if money_issue.target_refund_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Refund issue is missing refund context.",
                )
            refund = db.get(Refund, money_issue.target_refund_id)
            if refund is None or refund.refund_status != "succeeded":
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

    money_issue = get_money_issue_for_update_or_404(db, money_issue_id)
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
    validate_money_issue_resolution(
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
    if money_issue.target_credit_usage_id is None or money_issue.target_booking_id is None:
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game credit not found.")

    now = datetime.now(timezone.utc)
    retry_kind = "release" if money_issue.issue_type == "credit_release_failed" else "restore"
    try:
        admin_action = record_admin_action(
            db,
            admin_user_id=admin_user.id,
            action_type="retry_money_issue_credit",
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
                "failure": str(exc),
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
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return get_admin_money_issue_detail(db, money_issue_id=money_issue.id)
