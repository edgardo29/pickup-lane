import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


# Host deposit events store append-only audit rows for host deposit status
# changes without duplicating payment or refund provider details.
class HostDepositEvent(Base):
    __tablename__ = "host_deposit_events"
    __table_args__ = (
        CheckConstraint(
            (
                "(old_status IS NULL OR old_status IN ("
                "'required', 'payment_pending', 'paid', 'held', 'released', "
                "'refunded', 'forfeited', 'waived'))"
            ),
            name="ck_host_deposit_events_old_status",
        ),
        CheckConstraint(
            (
                "new_status IN ("
                "'required', 'payment_pending', 'paid', 'held', 'released', "
                "'refunded', 'forfeited', 'waived'"
                ")"
            ),
            name="ck_host_deposit_events_new_status",
        ),
        CheckConstraint(
            (
                "change_source IN ("
                "'user', 'host', 'admin', 'system', 'payment_webhook', "
                "'scheduled_job'"
                ")"
            ),
            name="ck_host_deposit_events_change_source",
        ),
        CheckConstraint(
            "(new_status <> 'forfeited' OR reason IS NOT NULL)",
            name="ck_host_deposit_events_forfeited_requires_reason",
        ),
        CheckConstraint(
            "(new_status <> 'waived' OR reason IS NOT NULL)",
            name="ck_host_deposit_events_waived_requires_reason",
        ),
        Index("ix_host_deposit_events_host_deposit_id", "host_deposit_id"),
        Index("ix_host_deposit_events_changed_by_user_id", "changed_by_user_id"),
        Index("ix_host_deposit_events_change_source", "change_source"),
        Index("ix_host_deposit_events_created_at", "created_at"),
        Index(
            "ix_host_deposit_events_host_deposit_id_created_at",
            "host_deposit_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)

    host_deposit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("host_deposits.id", ondelete="CASCADE"),
        nullable=False,
    )

    old_status: Mapped[str | None] = mapped_column(String(30), nullable=True)

    new_status: Mapped[str] = mapped_column(String(30), nullable=False)

    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    change_source: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'system'")
    )

    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
