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


# Host deposits track the refundable deposit lifecycle for one community-hosted
# game without storing Stripe provider details directly.
class HostDeposit(Base):
    __tablename__ = "host_deposits"
    __table_args__ = (
        CheckConstraint(
            (
                "deposit_status IN ("
                "'required', 'payment_pending', 'paid', 'held', 'released', "
                "'refunded', 'forfeited', 'waived'"
                ")"
            ),
            name="ck_host_deposits_deposit_status",
        ),
        CheckConstraint(
            "currency = 'USD'",
            name="ck_host_deposits_currency",
        ),
        CheckConstraint(
            "required_amount_cents >= 0",
            name="ck_host_deposits_required_amount_cents",
        ),
        CheckConstraint(
            (
                "(deposit_status NOT IN "
                "('paid', 'held', 'released', 'refunded', 'forfeited') "
                "OR payment_id IS NOT NULL)"
            ),
            name="ck_host_deposits_payment_statuses_require_payment",
        ),
        CheckConstraint(
            "(deposit_status <> 'paid' OR paid_at IS NOT NULL)",
            name="ck_host_deposits_paid_requires_paid_at",
        ),
        CheckConstraint(
            "(deposit_status <> 'held' OR paid_at IS NOT NULL)",
            name="ck_host_deposits_held_requires_paid_at",
        ),
        CheckConstraint(
            "(deposit_status <> 'released' OR released_at IS NOT NULL)",
            name="ck_host_deposits_released_requires_released_at",
        ),
        CheckConstraint(
            "(deposit_status <> 'refunded' OR refunded_at IS NOT NULL)",
            name="ck_host_deposits_refunded_requires_refunded_at",
        ),
        CheckConstraint(
            "(deposit_status <> 'refunded' OR refund_id IS NOT NULL)",
            name="ck_host_deposits_refunded_requires_refund",
        ),
        CheckConstraint(
            "(deposit_status <> 'forfeited' OR forfeited_at IS NOT NULL)",
            name="ck_host_deposits_forfeited_requires_forfeited_at",
        ),
        CheckConstraint(
            "(deposit_status <> 'forfeited' OR decision_reason IS NOT NULL)",
            name="ck_host_deposits_forfeited_requires_decision_reason",
        ),
        UniqueConstraint("game_id", name="uq_host_deposits_game_id"),
        UniqueConstraint("payment_id", name="uq_host_deposits_payment_id"),
        UniqueConstraint("refund_id", name="uq_host_deposits_refund_id"),
        Index("ix_host_deposits_host_user_id", "host_user_id"),
        Index("ix_host_deposits_deposit_status", "deposit_status"),
        Index("ix_host_deposits_decision_by_user_id", "decision_by_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="RESTRICT"),
        nullable=False,
    )
    host_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    required_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(
        CHAR(3), nullable=False, server_default=text("'USD'")
    )
    deposit_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'required'")
    )
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="RESTRICT"),
        nullable=True,
    )
    refund_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("refunds.id", ondelete="RESTRICT"),
        nullable=True,
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    released_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    forfeited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    refunded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    decision_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
