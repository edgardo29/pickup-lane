import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database_metadata import Base


# Durable job events store append-only lifecycle and repair history.
class DurableJobEvent(Base):
    __tablename__ = "durable_job_events"
    __table_args__ = (
        CheckConstraint(
            (
                "event_type IN ("
                "'enqueued', 'claimed', 'heartbeat', 'lease_recovered', "
                "'lease_expired_exhausted', 'succeeded', 'retry_scheduled', "
                "'exhausted', 'cancelled', 'released', 'repair_requeued', "
                "'repair_cancelled'"
                ")"
            ),
            name="ck_durable_job_events_event_type",
        ),
        CheckConstraint(
            "jsonb_typeof(event_metadata) = 'object'",
            name="ck_durable_job_events_metadata_object",
        ),
        Index("ix_durable_job_events_job_id", "job_id"),
        Index("ix_durable_job_events_job_occurred_id", "job_id", "occurred_at", "id"),
        Index("ix_durable_job_events_event_type", "event_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("durable_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    previous_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    new_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    attempt_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lease_owner: Mapped[str | None] = mapped_column(String(120), nullable=True)
    lease_token: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    safe_error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    event_metadata: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)
