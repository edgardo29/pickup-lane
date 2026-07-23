"""Read-only admin user money snapshot and navigation hub."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from backend.models import GameCredit, MoneyIssue, Payment, Refund, User, UserPaymentMethod
from backend.schemas.admin_money_schema import (
    AdminMoneyCreditPreviewSectionRead,
    AdminMoneyIssuePreviewSectionRead,
    AdminMoneyPaymentPreviewSectionRead,
    AdminMoneyUserCreditPreviewRead,
    AdminMoneyRefundPreviewSectionRead,
    AdminMoneySavedCardsSectionRead,
    AdminMoneyUserDetailRead,
    AdminMoneyUserIssuePreviewRead,
    AdminMoneyUserPaymentPreviewRead,
    AdminMoneyUserRefundPreviewRead,
    AdminMoneyUserSummaryRead,
    AdminMoneyUserSnapshotRead,
)
from backend.services.admin_money_issue_service import list_admin_money_issues
from backend.services.admin_money_display import compact_id
from backend.services.admin_money_payment_service import sum_payment_refunded_cents

USER_MONEY_PREVIEW_LIMIT = 5
USER_MONEY_SAVED_CARD_LIMIT = 10


def get_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    return user


def parse_offset_cursor(cursor: str | None) -> int:
    if cursor is None:
        return 0
    try:
        offset = int(cursor)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="saved_cards_cursor is not valid.",
        ) from exc
    if offset < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="saved_cards_cursor is not valid.",
        )
    return offset


def build_saved_cards_section(
    db: Session,
    *,
    user_id: uuid.UUID,
    include_inactive: bool,
    saved_cards_cursor: str | None,
) -> AdminMoneySavedCardsSectionRead:
    offset = parse_offset_cursor(saved_cards_cursor)
    active_count = int(
        db.scalar(
            select(func.count())
            .select_from(UserPaymentMethod)
            .where(
                UserPaymentMethod.user_id == user_id,
                UserPaymentMethod.method_status == "active",
            )
        )
        or 0
    )
    statement = select(UserPaymentMethod).where(UserPaymentMethod.user_id == user_id)
    if not include_inactive:
        statement = statement.where(UserPaymentMethod.method_status == "active")

    status_rank = case(
        (UserPaymentMethod.method_status == "active", 0),
        else_=1,
    )
    rows = list(
        db.scalars(
            statement.order_by(
                status_rank.asc(),
                UserPaymentMethod.created_at.desc(),
                UserPaymentMethod.id.desc(),
            )
            .offset(offset)
            .limit(USER_MONEY_SAVED_CARD_LIMIT + 1)
        ).all()
    )
    has_more = len(rows) > USER_MONEY_SAVED_CARD_LIMIT
    return AdminMoneySavedCardsSectionRead(
        items=rows[:USER_MONEY_SAVED_CARD_LIMIT],
        active_count=active_count,
        has_more=has_more,
        includes_inactive=include_inactive,
        next_cursor=str(offset + USER_MONEY_SAVED_CARD_LIMIT) if has_more else None,
    )


def count_open_money_issues(db: Session, user_id: uuid.UUID) -> int:
    count = db.scalar(
        select(func.count())
        .select_from(MoneyIssue)
        .where(
            MoneyIssue.target_user_id == user_id,
            MoneyIssue.status == "open",
        )
    )
    return int(count or 0)


def sum_available_credit(db: Session, user_id: uuid.UUID) -> int:
    total = db.scalar(
        select(func.coalesce(func.sum(GameCredit.available_cents), 0)).where(
            GameCredit.user_id == user_id,
            GameCredit.credit_status == "active",
            GameCredit.available_cents > 0,
        )
    )
    return int(total or 0)


def build_user_summary(user: User) -> AdminMoneyUserSummaryRead:
    name = " ".join(
        part
        for part in (user.first_name, user.last_name)
        if part
    ) or user.email or "User"
    return AdminMoneyUserSummaryRead(
        id=user.id,
        name=name,
        email=user.email,
        account_status=user.account_status,
        created_at=user.created_at,
    )


def build_user_issue_preview(issue: MoneyIssue) -> AdminMoneyUserIssuePreviewRead:
    return AdminMoneyUserIssuePreviewRead(
        id=issue.id,
        status=issue.status,
        issue_type=issue.issue_type,
        origin_workflow=issue.origin_workflow,
        value_kind=issue.value_kind,
        amount_cents=issue.amount_cents,
        currency=issue.currency,
        target_payment_id=issue.target_payment_id,
        target_refund_id=issue.target_refund_id,
        target_game_credit_id=issue.target_game_credit_id,
        target_credit_usage_id=issue.target_credit_usage_id,
        latest_reason_code=issue.latest_reason_code,
        latest_summary=issue.latest_summary,
        recommended_action_code=issue.recommended_action_code,
        first_detected_at=issue.first_detected_at,
        last_detected_at=issue.last_detected_at,
    )


def build_user_payment_preview(
    db: Session,
    payment: Payment,
) -> AdminMoneyUserPaymentPreviewRead:
    refunded_cents = sum_payment_refunded_cents(db, payment.id)
    context_label = None
    if payment.booking_id is not None:
        context_label = f"Booking {compact_id(payment.booking_id)}"
    elif payment.payment_type == "community_publish_fee":
        context_label = "Community publish fee"
    elif payment.payment_type == "admin_charge":
        context_label = "Admin charge"

    return AdminMoneyUserPaymentPreviewRead(
        id=payment.id,
        booking_id=payment.booking_id,
        game_id=payment.game_id,
        payment_type=payment.payment_type,
        amount_cents=payment.amount_cents,
        currency=payment.currency,
        payment_status=payment.payment_status,
        paid_at=payment.paid_at,
        is_fully_refunded=refunded_cents >= payment.amount_cents
        if payment.amount_cents > 0
        else False,
        context_label=context_label,
        created_at=payment.created_at,
    )


def project_user_refund_preview(refund: Refund) -> AdminMoneyUserRefundPreviewRead:
    context_label = None
    if refund.booking_id is not None:
        context_label = f"Booking {compact_id(refund.booking_id)}"
    elif refund.participant_id is not None:
        context_label = f"Participant {compact_id(refund.participant_id)}"
    elif refund.host_publish_fee_id is not None:
        context_label = f"Publish fee {compact_id(refund.host_publish_fee_id)}"

    return AdminMoneyUserRefundPreviewRead(
        id=refund.id,
        payment_id=refund.payment_id,
        booking_id=refund.booking_id,
        participant_id=refund.participant_id,
        host_publish_fee_id=refund.host_publish_fee_id,
        amount_cents=refund.amount_cents,
        currency=refund.currency,
        refund_reason=refund.refund_reason,
        refund_status=refund.refund_status,
        refunded_at=refund.refunded_at,
        context_label=context_label,
        created_at=refund.created_at,
    )


def build_user_credit_preview(credit: GameCredit) -> AdminMoneyUserCreditPreviewRead:
    context_label = None
    if credit.source_booking_id is not None:
        context_label = f"Booking {compact_id(credit.source_booking_id)}"
    elif credit.source_game_id is not None:
        context_label = f"Game {compact_id(credit.source_game_id)}"
    elif credit.source_payment_id is not None:
        context_label = f"Payment {compact_id(credit.source_payment_id)}"

    return AdminMoneyUserCreditPreviewRead(
        id=credit.id,
        amount_cents=credit.amount_cents,
        available_cents=credit.available_cents,
        currency=credit.currency,
        credit_status=credit.credit_status,
        credit_reason=credit.credit_reason,
        source_game_id=credit.source_game_id,
        source_booking_id=credit.source_booking_id,
        source_payment_id=credit.source_payment_id,
        context_label=context_label,
        created_at=credit.created_at,
    )


def recent_payments_section(
    db: Session,
    *,
    user_id: uuid.UUID,
) -> AdminMoneyPaymentPreviewSectionRead:
    payments = list(
        db.scalars(
            select(Payment)
            .where(Payment.payer_user_id == user_id)
            .order_by(Payment.created_at.desc(), Payment.id.desc())
            .limit(USER_MONEY_PREVIEW_LIMIT + 1)
        ).all()
    )
    has_more = len(payments) > USER_MONEY_PREVIEW_LIMIT
    return AdminMoneyPaymentPreviewSectionRead(
        items=[
            build_user_payment_preview(db, payment)
            for payment in payments[:USER_MONEY_PREVIEW_LIMIT]
        ],
        has_more=has_more,
    )


def recent_refunds_section(
    db: Session,
    *,
    user_id: uuid.UUID,
) -> AdminMoneyRefundPreviewSectionRead:
    refunds = list(
        db.scalars(
            select(Refund)
            .join(Payment, Refund.payment_id == Payment.id)
            .where(Payment.payer_user_id == user_id)
            .order_by(Refund.created_at.desc(), Refund.id.desc())
            .limit(USER_MONEY_PREVIEW_LIMIT + 1)
        ).all()
    )
    return AdminMoneyRefundPreviewSectionRead(
        items=[
            project_user_refund_preview(refund)
            for refund in refunds[:USER_MONEY_PREVIEW_LIMIT]
        ],
        has_more=len(refunds) > USER_MONEY_PREVIEW_LIMIT,
    )


def recent_credits_section(
    db: Session,
    *,
    user_id: uuid.UUID,
) -> AdminMoneyCreditPreviewSectionRead:
    credits = list(
        db.scalars(
            select(GameCredit)
            .where(GameCredit.user_id == user_id)
            .order_by(GameCredit.created_at.desc(), GameCredit.id.desc())
            .limit(USER_MONEY_PREVIEW_LIMIT + 1)
        ).all()
    )
    return AdminMoneyCreditPreviewSectionRead(
        items=[
            build_user_credit_preview(credit)
            for credit in credits[:USER_MONEY_PREVIEW_LIMIT]
        ],
        has_more=len(credits) > USER_MONEY_PREVIEW_LIMIT,
    )


def get_admin_money_user_detail(
    db: Session,
    *,
    user_id: uuid.UUID,
    viewer_user: User,
    include_inactive_payment_methods: bool = False,
    saved_cards_cursor: str | None = None,
) -> AdminMoneyUserDetailRead:
    user = get_user_or_404(db, user_id)
    open_issue_count = count_open_money_issues(db, user.id)
    open_issues = list_admin_money_issues(
        db,
        issue_status="open",
        user_id=user.id,
        limit=USER_MONEY_PREVIEW_LIMIT + 1,
    )

    return AdminMoneyUserDetailRead(
        user=build_user_summary(user),
        snapshot=AdminMoneyUserSnapshotRead(
            available_credit_cents=sum_available_credit(db, user.id),
            currency="USD",
            open_money_issue_count=open_issue_count,
        ),
        open_money_issues=AdminMoneyIssuePreviewSectionRead(
            items=[
                build_user_issue_preview(issue)
                for issue in open_issues[:USER_MONEY_PREVIEW_LIMIT]
            ],
            count=open_issue_count,
            has_more=len(open_issues) > USER_MONEY_PREVIEW_LIMIT,
        ),
        saved_cards=build_saved_cards_section(
            db,
            user_id=user.id,
            include_inactive=include_inactive_payment_methods,
            saved_cards_cursor=saved_cards_cursor,
        ),
        recent_payments=recent_payments_section(db, user_id=user.id),
        recent_refunds=recent_refunds_section(db, user_id=user.id),
        recent_credits=recent_credits_section(db, user_id=user.id),
    )
