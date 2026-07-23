import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


# Money issue events store issue and staff workflow history.
class MoneyIssueEvent(Base):
    __tablename__ = "money_issue_events"
    __table_args__ = (
        CheckConstraint(
            (
                "event_type IN ("
                "'issue_opened', 'issue_reopened', 'classification_changed', "
                "'recommended_action_changed', 'admin_retry_initiated', "
                "'refund_outcome_linked', 'credit_restore_failed', "
                "'credit_restore_succeeded', 'credit_release_failed', "
                "'credit_release_succeeded', 'issue_resolved'"
                ")"
            ),
            name="ck_money_issue_events_event_type",
        ),
        CheckConstraint(
            "event_source IN ('system', 'admin')",
            name="ck_money_issue_events_event_source",
        ),
        Index("ix_money_issue_events_money_issue_id", "money_issue_id"),
        Index(
            "ix_money_issue_events_issue_occurred_id",
            "money_issue_id",
            "occurred_at",
            "id",
        ),
        Index("ix_money_issue_events_refund_event_id", "refund_event_id"),
        Index("ix_money_issue_events_result_credit_usage_id", "result_credit_usage_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    money_issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("money_issues.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    event_source: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    admin_action_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_actions.id", ondelete="SET NULL"),
        nullable=True,
    )
    refund_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("refund_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    result_credit_usage_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("game_credit_usage.id", ondelete="SET NULL"),
        nullable=True,
    )
    previous_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    new_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    previous_issue_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    new_issue_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    previous_recommended_action_code: Mapped[str | None] = mapped_column(
        String(80), nullable=True
    )
    new_recommended_action_code: Mapped[str | None] = mapped_column(
        String(80), nullable=True
    )
    reason_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_metadata: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
