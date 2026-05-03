import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


# Booking status history stores append-only audit rows for booking lifecycle
# and payment status changes on a reservation/order.
class BookingStatusHistory(Base):
    __tablename__ = "booking_status_history"
    __table_args__ = (
        CheckConstraint(
            (
                "(old_booking_status IS NULL OR old_booking_status IN "
                "('pending_payment', 'confirmed', 'partially_cancelled', "
                "'cancelled', 'expired', 'failed'))"
            ),
            name="ck_booking_status_history_old_booking_status",
        ),
        CheckConstraint(
            (
                "new_booking_status IN ("
                "'pending_payment', 'confirmed', 'partially_cancelled', "
                "'cancelled', 'expired', 'failed'"
                ")"
            ),
            name="ck_booking_status_history_new_booking_status",
        ),
        CheckConstraint(
            (
                "(old_payment_status IS NULL OR old_payment_status IN ("
                "'unpaid', 'requires_action', 'processing', 'paid', 'failed', "
                "'partially_refunded', 'refunded', 'disputed'))"
            ),
            name="ck_booking_status_history_old_payment_status",
        ),
        CheckConstraint(
            (
                "(new_payment_status IS NULL OR new_payment_status IN ("
                "'unpaid', 'requires_action', 'processing', 'paid', 'failed', "
                "'partially_refunded', 'refunded', 'disputed'))"
            ),
            name="ck_booking_status_history_new_payment_status",
        ),
        CheckConstraint(
            (
                "change_source IN ("
                "'user', 'host', 'admin', 'system', 'payment_webhook', "
                "'scheduled_job'"
                ")"
            ),
            name="ck_booking_status_history_change_source",
        ),
        Index("ix_booking_status_history_booking_id", "booking_id"),
        Index(
            "ix_booking_status_history_changed_by_user_id",
            "changed_by_user_id",
        ),
        Index("ix_booking_status_history_change_source", "change_source"),
        Index("ix_booking_status_history_created_at", "created_at"),
        Index(
            "ix_booking_status_history_booking_id_created_at",
            "booking_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)

    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
    )

    old_booking_status: Mapped[str | None] = mapped_column(String(30), nullable=True)

    new_booking_status: Mapped[str] = mapped_column(String(30), nullable=False)

    old_payment_status: Mapped[str | None] = mapped_column(String(30), nullable=True)

    new_payment_status: Mapped[str | None] = mapped_column(String(30), nullable=True)

    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    change_source: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'system'")
    )

    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
