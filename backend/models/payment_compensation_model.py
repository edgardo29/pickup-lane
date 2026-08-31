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
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database_metadata import Base


class PaymentCompensation(Base):
    __tablename__ = "payment_compensations"
    __table_args__ = (
        CheckConstraint("action = 'refund'", name="ck_payment_compensations_action"),
        CheckConstraint(
            "reason IN ('reservation_expired', 'capacity_conflict', 'booking_cancelled')",
            name="ck_payment_compensations_reason",
        ),
        CheckConstraint(
            "status IN ('required', 'processing', 'succeeded', 'failed', 'cancelled')",
            name="ck_payment_compensations_status",
        ),
        CheckConstraint("amount_cents > 0", name="ck_payment_compensations_amount"),
        CheckConstraint("currency = 'USD'", name="ck_payment_compensations_currency"),
        Index("ix_payment_compensations_payment", "payment_id", "created_at", "id"),
        Index("ix_payment_compensations_booking", "booking_id", "created_at", "id"),
        Index(
            "uq_payment_compensations_active",
            "payment_id",
            "booking_id",
            unique=True,
            postgresql_where=text("status IN ('required', 'processing')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payments.id", ondelete="RESTRICT"), nullable=False
    )
    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="RESTRICT"), nullable=False
    )
    action: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'refund'")
    )
    reason: Mapped[str] = mapped_column(String(50), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(
        CHAR(3), nullable=False, server_default=text("'USD'")
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'required'")
    )
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
