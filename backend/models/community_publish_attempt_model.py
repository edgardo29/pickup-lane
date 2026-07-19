import uuid
from datetime import date, datetime

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    Date,
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


# Community publish attempts are internal payment/publish attempts. They are
# not user-facing drafts and never make a game visible before payment succeeds.
class CommunityPublishAttempt(Base):
    __tablename__ = "community_publish_attempts"
    __table_args__ = (
        CheckConstraint(
            (
                "attempt_status IN ("
                "'requires_payment_method', 'requires_action', 'processing', "
                "'succeeded', 'failed', 'cancelled', 'expired'"
                ")"
            ),
            name="ck_community_publish_attempts_status",
        ),
        CheckConstraint(
            "jsonb_typeof(publish_payload) = 'object'",
            name="ck_community_publish_attempts_payload_object",
        ),
        CheckConstraint(
            "amount_cents >= 0",
            name="ck_community_publish_attempts_amount_cents",
        ),
        CheckConstraint(
            "currency = 'USD'",
            name="ck_community_publish_attempts_currency",
        ),
        CheckConstraint(
            "(attempt_status <> 'succeeded' OR created_game_id IS NOT NULL)",
            name="ck_community_publish_attempts_succeeded_requires_game",
        ),
        UniqueConstraint("payment_id", name="uq_community_publish_attempts_payment_id"),
        UniqueConstraint(
            "created_game_id",
            name="uq_community_publish_attempts_created_game_id",
        ),
        Index(
            "ix_community_publish_attempts_host_user_id",
            "host_user_id",
        ),
        Index(
            "ix_community_publish_attempts_payment_id",
            "payment_id",
        ),
        Index(
            "ix_community_publish_attempts_created_game_id",
            "created_game_id",
        ),
        Index(
            "ix_community_publish_attempts_attempt_status",
            "attempt_status",
        ),
        Index(
            "ix_community_publish_attempts_host_date",
            "host_user_id",
            "starts_on_local",
        ),
        Index(
            "ux_community_publish_attempts_one_active_paid_per_host_date",
            "host_user_id",
            "starts_on_local",
            unique=True,
            postgresql_where=text(
                "attempt_status IN ("
                "'requires_payment_method', 'requires_action', 'processing'"
                ")"
            ),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
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
    created_game_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="RESTRICT"),
        nullable=True,
    )
    attempt_status: Mapped[str] = mapped_column(String(30), nullable=False)
    publish_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    payment_method_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_payment_methods.id", ondelete="SET NULL"),
        nullable=True,
    )
    starts_on_local: Mapped[date] = mapped_column(Date, nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(
        CHAR(3), nullable=False, server_default=text("'USD'")
    )
    failure_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    failure_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
