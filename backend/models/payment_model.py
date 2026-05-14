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
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


# This table stores Stripe-backed payment attempts and payment records without
# storing raw card data.
class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint(
            (
                "payment_type IN ("
                "'booking', 'community_publish_fee', 'refund_adjustment', "
                "'admin_charge'"
                ")"
            ),
            name="ck_payments_payment_type",
        ),
        CheckConstraint(
            "provider IN ('stripe')",
            name="ck_payments_provider",
        ),
        CheckConstraint(
            (
                "payment_status IN ("
                "'processing', 'requires_action', 'succeeded', 'failed', "
                "'canceled', 'refunded', 'partially_refunded', 'disputed'"
                ")"
            ),
            name="ck_payments_payment_status",
        ),
        CheckConstraint(
            "currency = 'USD'",
            name="ck_payments_currency",
        ),
        CheckConstraint(
            "amount_cents >= 0",
            name="ck_payments_amount_cents",
        ),
        CheckConstraint(
            "(payment_type <> 'booking' OR booking_id IS NOT NULL)",
            name="ck_payments_booking_requires_booking_id",
        ),
        CheckConstraint(
            (
                "(payment_type <> 'community_publish_fee' "
                "OR (game_id IS NOT NULL AND booking_id IS NULL))"
            ),
            name="ck_payments_community_publish_fee_game_only",
        ),
        CheckConstraint(
            "(payment_status <> 'succeeded' OR paid_at IS NOT NULL)",
            name="ck_payments_succeeded_requires_paid_at",
        ),
        UniqueConstraint(
            "provider_payment_intent_id",
            name="uq_payments_provider_payment_intent_id",
        ),
        UniqueConstraint(
            "idempotency_key",
            name="uq_payments_idempotency_key",
        ),
        Index("ix_payments_payer_user_id", "payer_user_id"),
        Index("ix_payments_booking_id", "booking_id"),
        Index("ix_payments_game_id", "game_id"),
        Index("ix_payments_payment_type", "payment_type"),
        Index("ix_payments_payment_status", "payment_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    payer_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="SET NULL"),
        nullable=True,
    )
    game_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="SET NULL"),
        nullable=True,
    )
    payment_type: Mapped[str] = mapped_column(String(30), nullable=False)
    provider: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'stripe'")
    )
    provider_payment_intent_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    provider_charge_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(
        CHAR(3), nullable=False, server_default=text("'USD'")
    )
    payment_status: Mapped[str] = mapped_column(String(30), nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_metadata: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
