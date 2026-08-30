import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database_metadata import Base


# Durable worker heartbeats expose portable worker identity and liveness state.
class DurableWorkerHeartbeat(Base):
    __tablename__ = "durable_worker_heartbeats"
    __table_args__ = (
        CheckConstraint(
            "status IN ('starting', 'running', 'stopping', 'stopped')",
            name="ck_durable_worker_heartbeats_status",
        ),
        CheckConstraint(
            (
                "((status = 'stopped') AND stopped_at IS NOT NULL) "
                "OR ((status <> 'stopped') AND stopped_at IS NULL)"
            ),
            name="ck_durable_worker_heartbeats_stopped_at",
        ),
        Index("ix_durable_worker_heartbeats_status", "status", "last_heartbeat_at"),
        Index("ix_durable_worker_heartbeats_current_job_id", "current_job_id"),
    )

    worker_identity: Mapped[str] = mapped_column(String(120), primary_key=True)
    worker_version: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'starting'"),
    )
    current_job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("durable_jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    last_heartbeat_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    stopped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
