import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database_metadata import Base


# Durable jobs are the generic PostgreSQL-backed work queue used by WS05.
class DurableJob(Base):
    __tablename__ = "durable_jobs"
    __table_args__ = (
        CheckConstraint(
            (
                "status IN ("
                "'pending', 'retry_waiting', 'leased', "
                "'succeeded', 'exhausted', 'cancelled'"
                ")"
            ),
            name="ck_durable_jobs_status",
        ),
        CheckConstraint(
            "payload_version >= 1",
            name="ck_durable_jobs_payload_version",
        ),
        CheckConstraint("priority >= 0", name="ck_durable_jobs_priority"),
        CheckConstraint("attempt_count >= 0", name="ck_durable_jobs_attempt_count"),
        CheckConstraint("maximum_attempts >= 1", name="ck_durable_jobs_maximum_attempts"),
        CheckConstraint(
            "attempt_count <= maximum_attempts",
            name="ck_durable_jobs_attempt_count_within_maximum",
        ),
        CheckConstraint(
            "jsonb_typeof(payload) = 'object'",
            name="ck_durable_jobs_payload_object",
        ),
        CheckConstraint(
            "jsonb_typeof(protected_identity) = 'object'",
            name="ck_durable_jobs_protected_identity_object",
        ),
        CheckConstraint(
            "jsonb_typeof(result_metadata) = 'object'",
            name="ck_durable_jobs_result_metadata_object",
        ),
        CheckConstraint(
            (
                "((status = 'leased') "
                "AND lease_token IS NOT NULL "
                "AND lease_owner IS NOT NULL "
                "AND lease_expires_at IS NOT NULL "
                "AND heartbeat_at IS NOT NULL) "
                "OR ((status <> 'leased') "
                "AND lease_token IS NULL "
                "AND lease_owner IS NULL "
                "AND lease_expires_at IS NULL "
                "AND heartbeat_at IS NULL)"
            ),
            name="ck_durable_jobs_lease_fields_match_status",
        ),
        CheckConstraint(
            (
                "((status = 'succeeded') "
                "AND completed_at IS NOT NULL "
                "AND exhausted_at IS NULL "
                "AND cancelled_at IS NULL) "
                "OR ((status = 'exhausted') "
                "AND exhausted_at IS NOT NULL "
                "AND completed_at IS NULL "
                "AND cancelled_at IS NULL) "
                "OR ((status = 'cancelled') "
                "AND cancelled_at IS NOT NULL "
                "AND completed_at IS NULL "
                "AND exhausted_at IS NULL) "
                "OR ((status NOT IN ('succeeded', 'exhausted', 'cancelled')) "
                "AND completed_at IS NULL "
                "AND exhausted_at IS NULL "
                "AND cancelled_at IS NULL)"
            ),
            name="ck_durable_jobs_terminal_fields_match_status",
        ),
        UniqueConstraint("idempotency_key", name="uq_durable_jobs_idempotency_key"),
        Index(
            "ix_durable_jobs_claimable",
            "status",
            "available_at",
            "priority",
            "created_at",
            "id",
        ),
        Index(
            "ix_durable_jobs_type_version_status",
            "job_type",
            "payload_version",
            "status",
        ),
        Index("ix_durable_jobs_lease_expiry", "status", "lease_expires_at", "id"),
        Index("ix_durable_jobs_correlation_id", "correlation_id"),
        Index("ix_durable_jobs_origin_reference", "origin_reference_type", "origin_reference_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    job_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload_version: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    protected_identity: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'pending'"),
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    maximum_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    lease_token: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    lease_owner: Mapped[str | None] = mapped_column(String(120), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    correlation_id: Mapped[str] = mapped_column(String(120), nullable=False)
    origin_reference_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    origin_reference_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    last_error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    result_metadata: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    exhausted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
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

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        super().__init__(**kwargs)
