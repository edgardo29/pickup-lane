"""create payment events table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0020_payment_events"
down_revision = "0019_admin_actions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Twentieth schema migration: create payment_events as durable Stripe
    # webhook/event audit records separate from current payment state.
    op.create_table(
        "payment_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "provider",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'stripe'"),
        ),
        sa.Column("provider_event_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "processing_status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "provider IN ('stripe')",
            name="ck_payment_events_provider",
        ),
        sa.CheckConstraint(
            "processing_status IN ('pending', 'processed', 'failed', 'ignored')",
            name="ck_payment_events_processing_status",
        ),
        sa.CheckConstraint(
            "char_length(btrim(event_type)) > 0",
            name="ck_payment_events_event_type_not_empty",
        ),
        sa.CheckConstraint(
            "(processing_status <> 'processed' OR processed_at IS NOT NULL)",
            name="ck_payment_events_processed_requires_processed_at",
        ),
        sa.CheckConstraint(
            "(processing_status <> 'failed' OR processing_error IS NOT NULL)",
            name="ck_payment_events_failed_requires_processing_error",
        ),
        sa.ForeignKeyConstraint(
            ["payment_id"],
            ["payments.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider_event_id",
            name="uq_payment_events_provider_event_id",
        ),
    )
    op.create_index(
        "ix_payment_events_payment_id",
        "payment_events",
        ["payment_id"],
        unique=False,
    )
    op.create_index(
        "ix_payment_events_event_type",
        "payment_events",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        "ix_payment_events_processing_status",
        "payment_events",
        ["processing_status"],
        unique=False,
    )
    op.create_index(
        "ix_payment_events_created_at",
        "payment_events",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_payment_events_payment_id_created_at",
        "payment_events",
        ["payment_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_payment_events_processing_status_created_at",
        "payment_events",
        ["processing_status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    # Downgrade removes the payment_events table and indexes because this
    # migration only introduces that single webhook/event audit table.
    op.drop_index(
        "ix_payment_events_processing_status_created_at",
        table_name="payment_events",
    )
    op.drop_index(
        "ix_payment_events_payment_id_created_at",
        table_name="payment_events",
    )
    op.drop_index("ix_payment_events_created_at", table_name="payment_events")
    op.drop_index("ix_payment_events_processing_status", table_name="payment_events")
    op.drop_index("ix_payment_events_event_type", table_name="payment_events")
    op.drop_index("ix_payment_events_payment_id", table_name="payment_events")
    op.drop_table("payment_events")