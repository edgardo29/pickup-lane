import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


# Payment events store durable Stripe webhook/event audit records separately
# from the current payment status stored on the payments table.
class PaymentEvent(Base):
    __tablename__ = "payment_events"
    __table_args__ = (
        CheckConstraint(
            "provider IN ('stripe')",
            name="ck_payment_events_provider",
        ),
        CheckConstraint(
            "processing_status IN ('pending', 'processed', 'failed', 'ignored')",
            name="ck_payment_events_processing_status",
        ),
        CheckConstraint(
            "char_length(btrim(event_type)) > 0",
            name="ck_payment_events_event_type_not_empty",
        ),
        CheckConstraint(
            "(processing_status <> 'processed' OR processed_at IS NOT NULL)",
            name="ck_payment_events_processed_requires_processed_at",
        ),
        CheckConstraint(
            "(processing_status <> 'failed' OR processing_error IS NOT NULL)",
            name="ck_payment_events_failed_requires_processing_error",
        ),
        UniqueConstraint(
            "provider_event_id",
            name="uq_payment_events_provider_event_id",
        ),
        Index("ix_payment_events_payment_id", "payment_id"),
        Index("ix_payment_events_event_type", "event_type"),
        Index("ix_payment_events_processing_status", "processing_status"),
        Index("ix_payment_events_created_at", "created_at"),
        Index("ix_payment_events_payment_id_created_at", "payment_id", "created_at"),
        Index(
            "ix_payment_events_processing_status_created_at",
            "processing_status",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)

    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
    )

    provider: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'stripe'")
    )

    provider_event_id: Mapped[str] = mapped_column(String(255), nullable=False)

    event_type: Mapped[str] = mapped_column(String(100), nullable=False)

    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)

    processing_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'pending'")
    )

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )