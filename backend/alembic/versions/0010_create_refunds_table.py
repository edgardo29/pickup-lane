"""create refunds table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0010_refunds"
down_revision = "0009_payments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tenth schema migration: create refunds as Stripe refund records linked to
    # payments, optionally scoped to a booking or participant.
    op.create_table(
        "refunds",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("participant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider_refund_id", sa.String(length=255), nullable=True),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column(
            "currency",
            sa.CHAR(length=3),
            nullable=False,
            server_default=sa.text("'USD'"),
        ),
        sa.Column("refund_reason", sa.String(length=40), nullable=False),
        sa.Column(
            "refund_status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
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
            (
                "refund_reason IN ("
                "'player_cancelled', 'late_cancel', 'host_cancelled', "
                "'game_cancelled', 'weather', 'admin_refund', "
                "'duplicate_payment', 'dispute_resolution'"
                ")"
            ),
            name="ck_refunds_refund_reason",
        ),
        sa.CheckConstraint(
            (
                "refund_status IN ("
                "'pending', 'approved', 'processing', 'succeeded', "
                "'failed', 'cancelled'"
                ")"
            ),
            name="ck_refunds_refund_status",
        ),
        sa.CheckConstraint(
            "currency = 'USD'",
            name="ck_refunds_currency",
        ),
        sa.CheckConstraint(
            "amount_cents > 0",
            name="ck_refunds_amount_cents",
        ),
        sa.CheckConstraint(
            "(refund_status <> 'approved' OR approved_at IS NOT NULL)",
            name="ck_refunds_approved_requires_approved_at",
        ),
        sa.CheckConstraint(
            "(refund_status <> 'succeeded' OR refunded_at IS NOT NULL)",
            name="ck_refunds_succeeded_requires_refunded_at",
        ),
        sa.CheckConstraint(
            "(booking_id IS NOT NULL OR participant_id IS NOT NULL)",
            name="ck_refunds_booking_or_participant_required",
        ),
        sa.ForeignKeyConstraint(
            ["payment_id"],
            ["payments.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["booking_id"],
            ["bookings.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["participant_id"],
            ["game_participants.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider_refund_id",
            name="uq_refunds_provider_refund_id",
        ),
    )
    op.create_index(
        "ix_refunds_payment_id",
        "refunds",
        ["payment_id"],
        unique=False,
    )
    op.create_index(
        "ix_refunds_booking_id",
        "refunds",
        ["booking_id"],
        unique=False,
    )
    op.create_index(
        "ix_refunds_participant_id",
        "refunds",
        ["participant_id"],
        unique=False,
    )
    op.create_index(
        "ix_refunds_refund_status",
        "refunds",
        ["refund_status"],
        unique=False,
    )
    op.create_index(
        "ix_refunds_refund_reason",
        "refunds",
        ["refund_reason"],
        unique=False,
    )
    op.create_index(
        "ix_refunds_requested_by_user_id",
        "refunds",
        ["requested_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_refunds_approved_by_user_id",
        "refunds",
        ["approved_by_user_id"],
        unique=False,
    )


def downgrade() -> None:
    # Downgrade removes the refunds table and indexes because this migration
    # only introduces that single table.
    op.drop_index("ix_refunds_approved_by_user_id", table_name="refunds")
    op.drop_index("ix_refunds_requested_by_user_id", table_name="refunds")
    op.drop_index("ix_refunds_refund_reason", table_name="refunds")
    op.drop_index("ix_refunds_refund_status", table_name="refunds")
    op.drop_index("ix_refunds_participant_id", table_name="refunds")
    op.drop_index("ix_refunds_booking_id", table_name="refunds")
    op.drop_index("ix_refunds_payment_id", table_name="refunds")
    op.drop_table("refunds")
