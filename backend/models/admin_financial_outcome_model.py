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
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class AdminFinancialOutcome(Base):
    __tablename__ = "admin_financial_outcomes"
    __table_args__ = (
        CheckConstraint(
            (
                "outcome IN ('no_fee_charged', 'refund', 'credit', "
                "'forfeit', 'manual_review')"
            ),
            name="ck_admin_financial_outcomes_outcome",
        ),
        CheckConstraint(
            "applied_status IN ('pending', 'applied', 'failed', 'not_applicable')",
            name="ck_admin_financial_outcomes_applied_status",
        ),
        CheckConstraint(
            "amount_cents >= 0",
            name="ck_admin_financial_outcomes_amount_cents",
        ),
        CheckConstraint(
            "currency = 'USD'",
            name="ck_admin_financial_outcomes_currency",
        ),
        CheckConstraint(
            (
                "host_user_id IS NOT NULL AND ("
                "target_game_id IS NOT NULL "
                "OR target_sub_post_id IS NOT NULL "
                "OR host_publish_fee_id IS NOT NULL "
                "OR payment_id IS NOT NULL)"
            ),
            name="ck_admin_financial_outcomes_target_required",
        ),
        CheckConstraint(
            (
                "applied_status NOT IN ('applied', 'failed') "
                "OR applied_at IS NOT NULL"
            ),
            name="ck_admin_financial_outcomes_terminal_requires_applied_at",
        ),
        Index("ix_admin_financial_outcomes_target_game_id", "target_game_id"),
        Index("ix_admin_financial_outcomes_target_sub_post_id", "target_sub_post_id"),
        Index("ix_admin_financial_outcomes_host_user_id", "host_user_id"),
        Index(
            "ix_admin_financial_outcomes_host_publish_fee_id",
            "host_publish_fee_id",
        ),
        Index("ix_admin_financial_outcomes_payment_id", "payment_id"),
        Index("ix_admin_financial_outcomes_refund_id", "refund_id"),
        Index(
            "ix_admin_financial_outcomes_entitlement_id",
            "host_publish_entitlement_id",
        ),
        Index("ix_admin_financial_outcomes_admin_action_id", "admin_action_id"),
        Index("ix_admin_financial_outcomes_review_case_id", "review_case_id"),
        Index("ix_admin_financial_outcomes_outcome", "outcome"),
        Index("ix_admin_financial_outcomes_applied_status", "applied_status"),
        Index("ix_admin_financial_outcomes_created_by_user_id", "created_by_user_id"),
        Index(
            "uq_admin_financial_outcomes_active_fee_decision",
            "host_publish_fee_id",
            unique=True,
            postgresql_where=text(
                "host_publish_fee_id IS NOT NULL "
                "AND applied_status IN ('pending', 'applied', 'not_applicable')"
            ),
        ),
        Index(
            "uq_admin_financial_outcomes_active_game_no_fee_decision",
            "host_user_id",
            "target_game_id",
            unique=True,
            postgresql_where=text(
                "target_game_id IS NOT NULL "
                "AND host_publish_fee_id IS NULL "
                "AND applied_status IN ('pending', 'applied', 'not_applicable')"
            ),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    target_game_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_sub_post_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sub_posts.id", ondelete="SET NULL"),
        nullable=True,
    )
    host_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    host_publish_fee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("host_publish_fees.id", ondelete="SET NULL"),
        nullable=True,
    )
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
    )
    refund_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("refunds.id", ondelete="SET NULL"),
        nullable=True,
    )
    host_publish_entitlement_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("host_publish_entitlements.id", ondelete="SET NULL"),
        nullable=True,
    )
    admin_action_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_actions.id", ondelete="SET NULL"),
        nullable=True,
    )
    review_case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_review_cases.id", ondelete="SET NULL"),
        nullable=True,
    )
    outcome: Mapped[str] = mapped_column(String(40), nullable=False)
    applied_status: Mapped[str] = mapped_column(String(30), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(
        CHAR(3), nullable=False, server_default=text("'USD'")
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    internal_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    applied_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    applied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
