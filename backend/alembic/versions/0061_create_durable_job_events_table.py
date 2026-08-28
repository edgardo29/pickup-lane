"""create durable_job_events table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0061_durable_job_events"
down_revision = "0060_durable_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "durable_job_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=60), nullable=False),
        sa.Column("previous_status", sa.String(length=20), nullable=True),
        sa.Column("new_status", sa.String(length=20), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=True),
        sa.Column("lease_owner", sa.String(length=120), nullable=True),
        sa.Column("lease_token", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("safe_error_code", sa.String(length=80), nullable=True),
        sa.Column(
            "event_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "event_type IN ('enqueued', 'claimed', 'heartbeat', 'lease_recovered', 'lease_expired_exhausted', 'succeeded', 'retry_scheduled', 'exhausted', 'cancelled', 'released', 'repair_requeued', 'repair_cancelled')",
            name="ck_durable_job_events_event_type",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(event_metadata) = 'object'",
            name="ck_durable_job_events_metadata_object",
        ),
        sa.ForeignKeyConstraint(["job_id"], ["durable_jobs.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_durable_job_events_job_id",
        "durable_job_events",
        ["job_id"],
        unique=False,
    )
    op.create_index(
        "ix_durable_job_events_job_occurred_id",
        "durable_job_events",
        ["job_id", "occurred_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_durable_job_events_event_type",
        "durable_job_events",
        ["event_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("durable_job_events")
