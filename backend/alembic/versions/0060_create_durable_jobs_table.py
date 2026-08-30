"""create durable_jobs table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0060_durable_jobs"
down_revision = "0059_admin_review_case_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "durable_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_type", sa.String(length=100), nullable=False),
        sa.Column("payload_version", sa.Integer(), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "protected_identity",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("maximum_attempts", sa.Integer(), nullable=False),
        sa.Column("lease_token", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lease_owner", sa.String(length=120), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("correlation_id", sa.String(length=120), nullable=False),
        sa.Column("origin_reference_type", sa.String(length=80), nullable=True),
        sa.Column("origin_reference_id", sa.String(length=120), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("last_error_code", sa.String(length=80), nullable=True),
        sa.Column(
            "result_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exhausted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'retry_waiting', 'leased', 'succeeded', 'exhausted', 'cancelled')",
            name="ck_durable_jobs_status",
        ),
        sa.CheckConstraint("payload_version >= 1", name="ck_durable_jobs_payload_version"),
        sa.CheckConstraint("priority >= 0", name="ck_durable_jobs_priority"),
        sa.CheckConstraint("attempt_count >= 0", name="ck_durable_jobs_attempt_count"),
        sa.CheckConstraint("maximum_attempts >= 1", name="ck_durable_jobs_maximum_attempts"),
        sa.CheckConstraint(
            "attempt_count <= maximum_attempts",
            name="ck_durable_jobs_attempt_count_within_maximum",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(payload) = 'object'",
            name="ck_durable_jobs_payload_object",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(protected_identity) = 'object'",
            name="ck_durable_jobs_protected_identity_object",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(result_metadata) = 'object'",
            name="ck_durable_jobs_result_metadata_object",
        ),
        sa.CheckConstraint(
            "((status = 'leased') AND lease_token IS NOT NULL AND lease_owner IS NOT NULL AND lease_expires_at IS NOT NULL AND heartbeat_at IS NOT NULL) OR ((status <> 'leased') AND lease_token IS NULL AND lease_owner IS NULL AND lease_expires_at IS NULL AND heartbeat_at IS NULL)",
            name="ck_durable_jobs_lease_fields_match_status",
        ),
        sa.CheckConstraint(
            "((status = 'succeeded') AND completed_at IS NOT NULL AND exhausted_at IS NULL AND cancelled_at IS NULL) OR ((status = 'exhausted') AND exhausted_at IS NOT NULL AND completed_at IS NULL AND cancelled_at IS NULL) OR ((status = 'cancelled') AND cancelled_at IS NOT NULL AND completed_at IS NULL AND exhausted_at IS NULL) OR ((status NOT IN ('succeeded', 'exhausted', 'cancelled')) AND completed_at IS NULL AND exhausted_at IS NULL AND cancelled_at IS NULL)",
            name="ck_durable_jobs_terminal_fields_match_status",
        ),
        sa.UniqueConstraint("idempotency_key", name="uq_durable_jobs_idempotency_key"),
    )
    op.create_index(
        "ix_durable_jobs_claimable",
        "durable_jobs",
        ["status", "available_at", "priority", "created_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_durable_jobs_type_version_status",
        "durable_jobs",
        ["job_type", "payload_version", "status"],
        unique=False,
    )
    op.create_index(
        "ix_durable_jobs_lease_expiry",
        "durable_jobs",
        ["status", "lease_expires_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_durable_jobs_correlation_id",
        "durable_jobs",
        ["correlation_id"],
        unique=False,
    )
    op.create_index(
        "ix_durable_jobs_origin_reference",
        "durable_jobs",
        ["origin_reference_type", "origin_reference_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("durable_jobs")
