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


# Host publish fees track first-game waivers and paid community publish fees.
class HostPublishFee(Base):
    __tablename__ = "host_publish_fees"
    __table_args__ = (
        CheckConstraint(
            "amount_cents >= 0",
            name="ck_host_publish_fees_amount_cents",
        ),
        CheckConstraint(
            "currency = 'USD'",
            name="ck_host_publish_fees_currency",
        ),
        CheckConstraint(
            "fee_status IN ('paid', 'waived')",
            name="ck_host_publish_fees_fee_status",
        ),
        CheckConstraint(
            "waiver_reason IN ('none', 'first_game_free', 'admin_comp')",
            name="ck_host_publish_fees_waiver_reason",
        ),
        CheckConstraint(
            (
                "fee_status <> 'paid' OR ("
                "payment_id IS NOT NULL AND paid_at IS NOT NULL "
                "AND amount_cents > 0)"
            ),
            name="ck_host_publish_fees_paid_requires_payment",
        ),
        CheckConstraint(
            (
                "fee_status <> 'waived' OR ("
                "amount_cents = 0 AND waiver_reason <> 'none' "
                "AND payment_id IS NULL)"
            ),
            name="ck_host_publish_fees_waived_requirements",
        ),
        UniqueConstraint("game_id", name="uq_host_publish_fees_game_id"),
        UniqueConstraint("payment_id", name="uq_host_publish_fees_payment_id"),
        Index("ix_host_publish_fees_game_id", "game_id"),
        Index("ix_host_publish_fees_host_user_id", "host_user_id"),
        Index("ix_host_publish_fees_fee_status", "fee_status"),
        Index("ix_host_publish_fees_payment_id", "payment_id"),
        Index(
            "ux_host_publish_fees_one_first_free_per_host",
            "host_user_id",
            unique=True,
            postgresql_where=text("waiver_reason = 'first_game_free'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="RESTRICT"),
        nullable=False,
    )
    host_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="RESTRICT"),
        nullable=True,
    )
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(
        CHAR(3), nullable=False, server_default=text("'USD'")
    )
    fee_status: Mapped[str] = mapped_column(String(30), nullable=False)
    waiver_reason: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'none'")
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
