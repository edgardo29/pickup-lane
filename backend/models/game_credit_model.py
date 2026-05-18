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


# Game credits are Pickup Lane-managed credit grants for official/in-app games.
# Community games with off-app host payments should not create these records.
class GameCredit(Base):
    __tablename__ = "game_credits"
    __table_args__ = (
        CheckConstraint(
            "credit_status IN ('active', 'used', 'expired', 'reversed')",
            name="ck_game_credits_credit_status",
        ),
        CheckConstraint(
            (
                "credit_reason IN ("
                "'official_game_cancelled', 'weather_cancelled', "
                "'player_cancelled_on_time', 'admin_credit', 'support_adjustment'"
                ")"
            ),
            name="ck_game_credits_credit_reason",
        ),
        CheckConstraint("currency = 'USD'", name="ck_game_credits_currency"),
        CheckConstraint("amount_cents > 0", name="ck_game_credits_amount_cents"),
        CheckConstraint(
            "remaining_cents >= 0",
            name="ck_game_credits_remaining_cents_non_negative",
        ),
        CheckConstraint(
            "remaining_cents <= amount_cents",
            name="ck_game_credits_remaining_not_above_amount",
        ),
        CheckConstraint(
            "(credit_status = 'active' OR remaining_cents = 0)",
            name="ck_game_credits_inactive_has_no_remaining",
        ),
        UniqueConstraint("idempotency_key", name="uq_game_credits_idempotency_key"),
        Index("ix_game_credits_user_id", "user_id"),
        Index("ix_game_credits_credit_status", "credit_status"),
        Index("ix_game_credits_credit_reason", "credit_reason"),
        Index("ix_game_credits_source_game_id", "source_game_id"),
        Index("ix_game_credits_source_booking_id", "source_booking_id"),
        Index("ix_game_credits_created_at", "created_at"),
        Index(
            "ix_game_credits_user_id_credit_status",
            "user_id",
            "credit_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    remaining_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(
        CHAR(3), nullable=False, server_default=text("'USD'")
    )
    credit_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'active'")
    )
    credit_reason: Mapped[str] = mapped_column(String(40), nullable=False)
    source_game_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_payment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
    )
    issued_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reversed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reversed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
