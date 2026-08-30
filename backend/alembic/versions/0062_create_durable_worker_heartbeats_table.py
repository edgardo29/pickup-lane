"""create durable_worker_heartbeats table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0062_durable_worker_heartbeats"
down_revision = "0061_durable_job_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "durable_worker_heartbeats",
        sa.Column("worker_identity", sa.String(length=120), primary_key=True),
        sa.Column("worker_version", sa.String(length=80), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'starting'"),
        ),
        sa.Column("current_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "last_started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "last_heartbeat_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
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
            "status IN ('starting', 'running', 'stopping', 'stopped')",
            name="ck_durable_worker_heartbeats_status",
        ),
        sa.CheckConstraint(
            "((status = 'stopped') AND stopped_at IS NOT NULL) OR ((status <> 'stopped') AND stopped_at IS NULL)",
            name="ck_durable_worker_heartbeats_stopped_at",
        ),
        sa.ForeignKeyConstraint(["current_job_id"], ["durable_jobs.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_durable_worker_heartbeats_status",
        "durable_worker_heartbeats",
        ["status", "last_heartbeat_at"],
        unique=False,
    )
    op.create_index(
        "ix_durable_worker_heartbeats_current_job_id",
        "durable_worker_heartbeats",
        ["current_job_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("durable_worker_heartbeats")
