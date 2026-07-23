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


# Game credit usage records track reserved, redeemed, released, and reversed
# movement against Pickup Lane credit grants.
class GameCreditUsage(Base):
    __tablename__ = "game_credit_usage"
    __table_args__ = (
        CheckConstraint(
            "usage_type IN ('redeem', 'reverse', 'restore')",
            name="ck_game_credit_usage_usage_type",
        ),
        CheckConstraint(
            (
                "usage_status IN ("
                "'reserved', 'redeemed', 'released', 'reversed', 'restored'"
                ")"
            ),
            name="ck_game_credit_usage_usage_status",
        ),
        CheckConstraint(
            (
                "((usage_type = 'redeem' "
                "AND usage_status IN ('reserved', 'redeemed', 'released')) "
                "OR (usage_type = 'reverse' AND usage_status = 'reversed') "
                "OR (usage_type = 'restore' AND usage_status = 'restored'))"
            ),
            name="ck_game_credit_usage_type_status_match",
        ),
        CheckConstraint("currency = 'USD'", name="ck_game_credit_usage_currency"),
        CheckConstraint("amount_cents > 0", name="ck_game_credit_usage_amount_cents"),
        CheckConstraint(
            "(usage_type <> 'redeem' OR booking_id IS NOT NULL)",
            name="ck_game_credit_usage_redeem_requires_booking",
        ),
        CheckConstraint(
            "(usage_status <> 'reserved' OR reserved_at IS NOT NULL)",
            name="ck_game_credit_usage_reserved_requires_reserved_at",
        ),
        CheckConstraint(
            "(usage_status <> 'redeemed' OR redeemed_at IS NOT NULL)",
            name="ck_game_credit_usage_redeemed_requires_redeemed_at",
        ),
        CheckConstraint(
            "(usage_status <> 'released' OR released_at IS NOT NULL)",
            name="ck_game_credit_usage_released_requires_released_at",
        ),
        CheckConstraint(
            "(usage_type <> 'restore' OR original_usage_id IS NOT NULL)",
            name="ck_game_credit_usage_restore_requires_original_usage",
        ),
        UniqueConstraint("idempotency_key", name="uq_game_credit_usage_idempotency_key"),
        Index("ix_game_credit_usage_game_credit_id", "game_credit_id"),
        Index(
            "ix_game_credit_usage_credit_created",
            "game_credit_id",
            "created_at",
            "id",
        ),
        Index(
            "ix_game_credit_usage_credit_status",
            "game_credit_id",
            "usage_status",
        ),
        Index("ix_game_credit_usage_game_id", "game_id"),
        Index("ix_game_credit_usage_booking_id", "booking_id"),
        Index("ix_game_credit_usage_payment_id", "payment_id"),
        Index("ix_game_credit_usage_original_usage_id", "original_usage_id"),
        Index(
            "uq_game_credit_usage_one_restore_per_original",
            "original_usage_id",
            unique=True,
            postgresql_where=text(
                "usage_type = 'restore' "
                "AND usage_status = 'restored' "
                "AND original_usage_id IS NOT NULL"
            ),
        ),
        Index("ix_game_credit_usage_usage_type", "usage_type"),
        Index("ix_game_credit_usage_usage_status", "usage_status"),
        Index("ix_game_credit_usage_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    game_credit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("game_credits.id", ondelete="RESTRICT"),
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
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
    )
    original_usage_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("game_credit_usage.id", ondelete="RESTRICT"),
        nullable=True,
    )
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(
        CHAR(3), nullable=False, server_default=text("'USD'")
    )
    usage_type: Mapped[str] = mapped_column(String(30), nullable=False)
    usage_status: Mapped[str] = mapped_column(String(30), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    reserved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    redeemed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    released_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
