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
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


# Refunds track Stripe refund records against a payment, optionally scoped to
# either a full booking or one specific participant.
class Refund(Base):
    __tablename__ = "refunds"
    __table_args__ = (
        CheckConstraint(
            (
                "refund_reason IN ("
                "'player_cancelled', 'late_cancel', 'host_cancelled', "
                "'game_cancelled', 'weather', 'admin_refund', "
                "'duplicate_payment', 'dispute_resolution'"
                ")"
            ),
            name="ck_refunds_refund_reason",
        ),
        CheckConstraint(
            (
                "refund_status IN ("
                "'pending', 'approved', 'processing', 'succeeded', "
                "'failed', 'cancelled'"
                ")"
            ),
            name="ck_refunds_refund_status",
        ),
        CheckConstraint(
            "currency = 'USD'",
            name="ck_refunds_currency",
        ),
        CheckConstraint(
            "amount_cents > 0",
            name="ck_refunds_amount_cents",
        ),
        CheckConstraint(
            "(refund_status <> 'approved' OR approved_at IS NOT NULL)",
            name="ck_refunds_approved_requires_approved_at",
        ),
        CheckConstraint(
            "(refund_status <> 'succeeded' OR refunded_at IS NOT NULL)",
            name="ck_refunds_succeeded_requires_refunded_at",
        ),
        CheckConstraint(
            "(booking_id IS NOT NULL OR participant_id IS NOT NULL)",
            name="ck_refunds_booking_or_participant_required",
        ),
        UniqueConstraint(
            "provider_refund_id",
            name="uq_refunds_provider_refund_id",
        ),
        Index("ix_refunds_payment_id", "payment_id"),
        Index("ix_refunds_booking_id", "booking_id"),
        Index("ix_refunds_participant_id", "participant_id"),
        Index("ix_refunds_refund_status", "refund_status"),
        Index("ix_refunds_refund_reason", "refund_reason"),
        Index("ix_refunds_requested_by_user_id", "requested_by_user_id"),
        Index("ix_refunds_approved_by_user_id", "approved_by_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="RESTRICT"),
        nullable=True,
    )
    participant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("game_participants.id", ondelete="RESTRICT"),
        nullable=True,
    )
    provider_refund_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(
        CHAR(3), nullable=False, server_default=text("'USD'")
    )
    refund_reason: Mapped[str] = mapped_column(String(40), nullable=False)
    refund_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'pending'")
    )
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    refunded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
