import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


# Refund events store sparse semantic refund/provider history, not raw Stripe
# payloads.
class RefundEvent(Base):
    __tablename__ = "refund_events"
    __table_args__ = (
        CheckConstraint(
            (
                "event_type IN ("
                "'provider_result_recorded', 'reconciliation_checked', "
                "'local_status_changed', 'provider_outcome_unknown'"
                ")"
            ),
            name="ck_refund_events_event_type",
        ),
        CheckConstraint(
            "event_source IN ('system', 'webhook', 'reconciliation', 'admin')",
            name="ck_refund_events_event_source",
        ),
        CheckConstraint(
            "(provider IS NULL OR provider IN ('stripe'))",
            name="ck_refund_events_provider",
        ),
        CheckConstraint(
            (
                "provider_status IS NULL OR provider_status IN ("
                "'processing', 'succeeded', 'failed', 'cancelled', 'unknown'"
                ")"
            ),
            name="ck_refund_events_provider_status",
        ),
        Index("ix_refund_events_refund_id", "refund_id"),
        Index(
            "ix_refund_events_refund_id_occurred_id",
            "refund_id",
            "occurred_at",
            "id",
        ),
        Index("ix_refund_events_provider_refund_id", "provider_refund_id"),
        Index("ix_refund_events_provider_charge_id", "provider_charge_id"),
        Index(
            "uq_refund_events_provider_event_id",
            "provider",
            "provider_event_id",
            unique=True,
            postgresql_where=text("provider_event_id IS NOT NULL"),
        ),
        Index(
            "uq_refund_events_idempotency_key",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    refund_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("refunds.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    event_source: Mapped[str] = mapped_column(String(30), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    admin_action_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_actions.id", ondelete="SET NULL"),
        nullable=True,
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(20), nullable=True)
    provider_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_refund_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_charge_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    previous_refund_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    new_refund_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    reason_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_metadata: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
