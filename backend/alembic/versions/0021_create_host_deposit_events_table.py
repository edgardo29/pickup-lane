"""create host deposit events table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0021_host_deposit_events"
down_revision = "0020_payment_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Twenty-first schema migration: create host_deposit_events as an
    # append-only audit trail for host deposit status changes.
    op.create_table(
        "host_deposit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("host_deposit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("old_status", sa.String(length=30), nullable=True),
        sa.Column("new_status", sa.String(length=30), nullable=False),
        sa.Column("changed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "change_source",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'system'"),
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            (
                "(old_status IS NULL OR old_status IN ("
                "'required', 'payment_pending', 'paid', 'held', 'released', "
                "'refunded', 'forfeited', 'waived'))"
            ),
            name="ck_host_deposit_events_old_status",
        ),
        sa.CheckConstraint(
            (
                "new_status IN ("
                "'required', 'payment_pending', 'paid', 'held', 'released', "
                "'refunded', 'forfeited', 'waived'"
                ")"
            ),
            name="ck_host_deposit_events_new_status",
        ),
        sa.CheckConstraint(
            (
                "change_source IN ("
                "'user', 'host', 'admin', 'system', 'payment_webhook', "
                "'scheduled_job'"
                ")"
            ),
            name="ck_host_deposit_events_change_source",
        ),
        sa.CheckConstraint(
            "(new_status <> 'forfeited' OR reason IS NOT NULL)",
            name="ck_host_deposit_events_forfeited_requires_reason",
        ),
        sa.CheckConstraint(
            "(new_status <> 'waived' OR reason IS NOT NULL)",
            name="ck_host_deposit_events_waived_requires_reason",
        ),
        sa.ForeignKeyConstraint(
            ["host_deposit_id"],
            ["host_deposits.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["changed_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_host_deposit_events_host_deposit_id",
        "host_deposit_events",
        ["host_deposit_id"],
        unique=False,
    )
    op.create_index(
        "ix_host_deposit_events_changed_by_user_id",
        "host_deposit_events",
        ["changed_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_host_deposit_events_change_source",
        "host_deposit_events",
        ["change_source"],
        unique=False,
    )
    op.create_index(
        "ix_host_deposit_events_created_at",
        "host_deposit_events",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_host_deposit_events_host_deposit_id_created_at",
        "host_deposit_events",
        ["host_deposit_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    # Downgrade removes the host_deposit_events table and indexes because this
    # migration only introduces that single host deposit audit table.
    op.drop_index(
        "ix_host_deposit_events_host_deposit_id_created_at",
        table_name="host_deposit_events",
    )
    op.drop_index("ix_host_deposit_events_created_at", table_name="host_deposit_events")
    op.drop_index(
        "ix_host_deposit_events_change_source",
        table_name="host_deposit_events",
    )
    op.drop_index(
        "ix_host_deposit_events_changed_by_user_id",
        table_name="host_deposit_events",
    )
    op.drop_index(
        "ix_host_deposit_events_host_deposit_id",
        table_name="host_deposit_events",
    )
    op.drop_table("host_deposit_events")
