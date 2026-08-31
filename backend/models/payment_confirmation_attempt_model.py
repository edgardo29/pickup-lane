import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database_metadata import Base


class PaymentConfirmationAttempt(Base):
    __tablename__ = "payment_confirmation_attempts"
    __table_args__ = (
        CheckConstraint(
            "outcome IN ('pending', 'provider_unknown', 'succeeded', 'failed')",
            name="ck_payment_confirmation_attempts_outcome",
        ),
        Index(
            "ix_payment_confirmation_attempts_payment_created",
            "payment_id",
            "created_at",
            "id",
        ),
        Index(
            "uq_payment_confirmation_attempts_fingerprint",
            "payment_id",
            "confirmation_fingerprint",
            unique=True,
        ),
        Index(
            "uq_payment_confirmation_attempts_idempotency",
            "confirmation_idempotency_key",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payments.id", ondelete="CASCADE"), nullable=False
    )
    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    provider_customer_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_payment_method_id: Mapped[str] = mapped_column(String(255), nullable=False)
    confirmation_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    confirmation_idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    outcome: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'pending'")
    )
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
