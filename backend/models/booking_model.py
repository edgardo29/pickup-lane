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


# This table stores the buyer-facing reservation/order for a game, including
# price snapshots and lifecycle state, before participant rows are modeled.
class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        # Keep booking and payment state within the supported values and ensure
        # money/count fields stay internally consistent.
        CheckConstraint(
            (
                "booking_status IN ("
                "'pending_payment', 'confirmed', 'partially_cancelled', "
                "'cancelled', 'expired', 'failed'"
                ")"
            ),
            name="ck_bookings_booking_status",
        ),
        CheckConstraint(
            (
                "payment_status IN ("
                "'unpaid', 'requires_action', 'processing', 'paid', 'failed', "
                "'partially_refunded', 'refunded', 'disputed'"
                ")"
            ),
            name="ck_bookings_payment_status",
        ),
        CheckConstraint(
            "currency = 'USD'",
            name="ck_bookings_currency",
        ),
        CheckConstraint(
            "participant_count > 0",
            name="ck_bookings_participant_count",
        ),
        CheckConstraint(
            "subtotal_cents >= 0",
            name="ck_bookings_subtotal_cents",
        ),
        CheckConstraint(
            "platform_fee_cents >= 0",
            name="ck_bookings_platform_fee_cents",
        ),
        CheckConstraint(
            "discount_cents >= 0",
            name="ck_bookings_discount_cents",
        ),
        CheckConstraint(
            "total_cents >= 0",
            name="ck_bookings_total_cents",
        ),
        CheckConstraint(
            "price_per_player_snapshot_cents >= 0",
            name="ck_bookings_price_per_player_snapshot_cents",
        ),
        CheckConstraint(
            "platform_fee_snapshot_cents >= 0",
            name="ck_bookings_platform_fee_snapshot_cents",
        ),
        CheckConstraint(
            "total_cents = subtotal_cents + platform_fee_cents - discount_cents",
            name="ck_bookings_total_cents_formula",
        ),
        CheckConstraint(
            "(booking_status <> 'confirmed' OR booked_at IS NOT NULL)",
            name="ck_bookings_confirmed_requires_booked_at",
        ),
        CheckConstraint(
            "(booking_status <> 'cancelled' OR cancelled_at IS NOT NULL)",
            name="ck_bookings_cancelled_requires_cancelled_at",
        ),
        # These indexes support the buyer, game, and operational views that
        # will be needed before participant and refund tables exist.
        Index("ix_bookings_game_id", "game_id"),
        Index("ix_bookings_buyer_user_id", "buyer_user_id"),
        Index("ix_bookings_booking_status", "booking_status"),
        Index("ix_bookings_payment_status", "payment_status"),
        Index(
            "ix_bookings_buyer_user_id_booking_status",
            "buyer_user_id",
            "booking_status",
        ),
        Index(
            "ix_bookings_game_id_booking_status",
            "game_id",
            "booking_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="RESTRICT"),
        nullable=False,
    )
    buyer_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    booking_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'pending_payment'")
    )
    payment_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'unpaid'")
    )
    participant_count: Mapped[int] = mapped_column(Integer, nullable=False)
    subtotal_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    platform_fee_cents: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    discount_cents: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    total_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(
        CHAR(3), nullable=False, server_default=text("'USD'")
    )
    price_per_player_snapshot_cents: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    platform_fee_snapshot_cents: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    booked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
