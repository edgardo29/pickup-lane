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


# Game credit usage records where Pickup Lane credit was redeemed or reversed.
class GameCreditUsage(Base):
    __tablename__ = "game_credit_usage"
    __table_args__ = (
        CheckConstraint(
            "usage_type IN ('redeem', 'reverse')",
            name="ck_game_credit_usage_usage_type",
        ),
        CheckConstraint("currency = 'USD'", name="ck_game_credit_usage_currency"),
        CheckConstraint("amount_cents > 0", name="ck_game_credit_usage_amount_cents"),
        CheckConstraint(
            "(usage_type <> 'redeem' OR booking_id IS NOT NULL)",
            name="ck_game_credit_usage_redeem_requires_booking",
        ),
        UniqueConstraint("idempotency_key", name="uq_game_credit_usage_idempotency_key"),
        Index("ix_game_credit_usage_game_credit_id", "game_credit_id"),
        Index("ix_game_credit_usage_user_id", "user_id"),
        Index("ix_game_credit_usage_booking_id", "booking_id"),
        Index("ix_game_credit_usage_usage_type", "usage_type"),
        Index("ix_game_credit_usage_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    game_credit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("game_credits.id", ondelete="RESTRICT"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="SET NULL"),
        nullable=True,
    )
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(
        CHAR(3), nullable=False, server_default=text("'USD'")
    )
    usage_type: Mapped[str] = mapped_column(String(30), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
