"""create booking status history table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0016_booking_status_history"
down_revision = "0015_game_status_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Sixteenth schema migration: create booking_status_history as append-only
    # audit rows for booking and payment lifecycle changes.
    op.create_table(
        "booking_status_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("old_booking_status", sa.String(length=30), nullable=True),
        sa.Column("new_booking_status", sa.String(length=30), nullable=False),
        sa.Column("old_payment_status", sa.String(length=30), nullable=True),
        sa.Column("new_payment_status", sa.String(length=30), nullable=True),
        sa.Column("changed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "change_source",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'system'"),
        ),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            (
                "(old_booking_status IS NULL OR old_booking_status IN "
                "('pending_payment', 'confirmed', 'partially_cancelled', "
                "'cancelled', 'expired', 'failed'))"
            ),
            name="ck_booking_status_history_old_booking_status",
        ),
        sa.CheckConstraint(
            (
                "new_booking_status IN ("
                "'pending_payment', 'confirmed', 'partially_cancelled', "
                "'cancelled', 'expired', 'failed'"
                ")"
            ),
            name="ck_booking_status_history_new_booking_status",
        ),
        sa.CheckConstraint(
            (
                "(old_payment_status IS NULL OR old_payment_status IN ("
                "'unpaid', 'requires_action', 'processing', 'paid', 'failed', "
                "'partially_refunded', 'refunded', 'disputed'))"
            ),
            name="ck_booking_status_history_old_payment_status",
        ),
        sa.CheckConstraint(
            (
                "(new_payment_status IS NULL OR new_payment_status IN ("
                "'unpaid', 'requires_action', 'processing', 'paid', 'failed', "
                "'partially_refunded', 'refunded', 'disputed'))"
            ),
            name="ck_booking_status_history_new_payment_status",
        ),
        sa.CheckConstraint(
            (
                "change_source IN ("
                "'user', 'host', 'admin', 'system', 'payment_webhook', "
                "'scheduled_job'"
                ")"
            ),
            name="ck_booking_status_history_change_source",
        ),
        sa.ForeignKeyConstraint(
            ["booking_id"],
            ["bookings.id"],
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
        "ix_booking_status_history_booking_id",
        "booking_status_history",
        ["booking_id"],
        unique=False,
    )
    op.create_index(
        "ix_booking_status_history_changed_by_user_id",
        "booking_status_history",
        ["changed_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_booking_status_history_change_source",
        "booking_status_history",
        ["change_source"],
        unique=False,
    )
    op.create_index(
        "ix_booking_status_history_created_at",
        "booking_status_history",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_booking_status_history_booking_id_created_at",
        "booking_status_history",
        ["booking_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    # Downgrade removes the booking_status_history table and indexes because
    # this migration only introduces that single table.
    op.drop_index(
        "ix_booking_status_history_booking_id_created_at",
        table_name="booking_status_history",
    )
    op.drop_index(
        "ix_booking_status_history_created_at",
        table_name="booking_status_history",
    )
    op.drop_index(
        "ix_booking_status_history_change_source",
        table_name="booking_status_history",
    )
    op.drop_index(
        "ix_booking_status_history_changed_by_user_id",
        table_name="booking_status_history",
    )
    op.drop_index(
        "ix_booking_status_history_booking_id",
        table_name="booking_status_history",
    )
    op.drop_table("booking_status_history")
