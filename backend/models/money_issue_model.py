import uuid
from datetime import datetime

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


# Money issues are the current admin queue rows for money obligations that
# require staff review.
class MoneyIssue(Base):
    __tablename__ = "money_issues"
    __table_args__ = (
        CheckConstraint("status IN ('open', 'resolved')", name="ck_money_issues_status"),
        CheckConstraint(
            (
                "issue_type IN ("
                "'refund_missing_provider_reference', "
                "'refund_processing_overdue', 'refund_failed', "
                "'refund_cancelled', 'refund_outcome_unknown', "
                "'credit_restore_failed', 'credit_release_failed'"
                ")"
            ),
            name="ck_money_issues_issue_type",
        ),
        CheckConstraint(
            (
                "origin_workflow IN ("
                "'player_removal', 'official_game_cancellation', "
                "'community_publish_fee_refund', 'direct_admin_refund', "
                "'official_game_checkout', 'pending_checkout_expiration', "
                "'pending_checkout_cancellation', 'admin_game_update'"
                ")"
            ),
            name="ck_money_issues_origin_workflow",
        ),
        CheckConstraint(
            (
                "value_kind IN ("
                "'cash_refund', 'game_credit_restore', 'game_credit_release'"
                ")"
            ),
            name="ck_money_issues_value_kind",
        ),
        CheckConstraint("amount_cents >= 0", name="ck_money_issues_amount_cents"),
        CheckConstraint("currency = 'USD'", name="ck_money_issues_currency"),
        CheckConstraint(
            (
                "recommended_action_code IN ("
                "'recover_provider_reference', 'retry_refund', "
                "'verify_provider_refund', 'retry_credit_restore', "
                "'retry_credit_release', 'review_unknown_outcome', "
                "'review_and_resolve_no_action', 'document_external_completion'"
                ")"
            ),
            name="ck_money_issues_recommended_action_code",
        ),
        CheckConstraint(
            (
                "resolution_reason_code IS NULL OR resolution_reason_code IN ("
                "'retried_successfully', 'provider_completed_no_action_required', "
                "'handled_externally', 'invalid_issue', "
                "'unable_to_complete_documented'"
                ")"
            ),
            name="ck_money_issues_resolution_reason_code",
        ),
        CheckConstraint(
            "occurrence_count >= 1",
            name="ck_money_issues_occurrence_count",
        ),
        CheckConstraint("reopen_count >= 0", name="ck_money_issues_reopen_count"),
        CheckConstraint(
            (
                "((status = 'open') "
                "AND resolved_at IS NULL "
                "AND resolved_by_user_id IS NULL "
                "AND resolution_reason_code IS NULL "
                "AND resolution_note IS NULL "
                "AND resolution_external_reference IS NULL) "
                "OR ((status = 'resolved') "
                "AND resolved_at IS NOT NULL "
                "AND resolved_by_user_id IS NOT NULL "
                "AND resolution_reason_code IS NOT NULL)"
            ),
            name="ck_money_issues_resolution_fields_match_status",
        ),
        CheckConstraint(
            (
                "(issue_type NOT LIKE 'refund_%' OR target_refund_id IS NOT NULL)"
            ),
            name="ck_money_issues_refund_requires_refund",
        ),
        CheckConstraint(
            (
                "(issue_type NOT LIKE 'credit_%' "
                "OR target_credit_usage_id IS NOT NULL)"
            ),
            name="ck_money_issues_credit_requires_usage",
        ),
        UniqueConstraint("operation_key", name="uq_money_issues_operation_key"),
        Index("ix_money_issues_open_queue", "status", "first_detected_at", "id"),
        Index("ix_money_issues_resolved", "resolved_at", "id"),
        Index("ix_money_issues_activity", "last_activity_at", "id"),
        Index("ix_money_issues_issue_type_status", "issue_type", "status"),
        Index("ix_money_issues_origin_workflow_status", "origin_workflow", "status"),
        Index("ix_money_issues_target_user_id", "target_user_id"),
        Index("ix_money_issues_target_game_id", "target_game_id"),
        Index("ix_money_issues_target_booking_id", "target_booking_id"),
        Index("ix_money_issues_target_payment_id", "target_payment_id"),
        Index("ix_money_issues_target_refund_id", "target_refund_id"),
        Index("ix_money_issues_target_game_credit_id", "target_game_credit_id"),
        Index("ix_money_issues_target_credit_usage_id", "target_credit_usage_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    operation_key: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    issue_type: Mapped[str] = mapped_column(String(80), nullable=False)
    origin_workflow: Mapped[str] = mapped_column(String(80), nullable=False)
    value_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(
        CHAR(3), nullable=False, server_default=text("'USD'")
    )
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    target_game_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("games.id", ondelete="SET NULL"), nullable=True
    )
    target_booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True
    )
    target_payment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payments.id", ondelete="SET NULL"), nullable=True
    )
    target_refund_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("refunds.id", ondelete="RESTRICT"), nullable=True
    )
    target_game_credit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("game_credits.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_credit_usage_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("game_credit_usage.id", ondelete="RESTRICT"),
        nullable=True,
    )
    latest_reason_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    latest_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_action_code: Mapped[str] = mapped_column(String(80), nullable=False)
    occurrence_count: Mapped[int] = mapped_column(Integer, nullable=False)
    reopen_count: Mapped[int] = mapped_column(Integer, nullable=False)
    first_detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolution_reason_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution_external_reference: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
