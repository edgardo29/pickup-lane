"""create payments table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0009_payments"
down_revision = "0008_waitlist_entries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ninth schema migration: create payments as the Stripe-backed payment
    # record for booking payments and game-related host deposit payments.
    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payer_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("game_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payment_type", sa.String(length=30), nullable=False),
        sa.Column(
            "provider",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'stripe'"),
        ),
        sa.Column(
            "provider_payment_intent_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column("provider_charge_id", sa.String(length=255), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column(
            "currency",
            sa.CHAR(length=3),
            nullable=False,
            server_default=sa.text("'USD'"),
        ),
        sa.Column("payment_status", sa.String(length=30), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
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
                "payment_type IN ("
                "'booking', 'host_deposit', 'refund_adjustment', 'admin_charge'"
                ")"
            ),
            name="ck_payments_payment_type",
        ),
        sa.CheckConstraint(
            "provider IN ('stripe')",
            name="ck_payments_provider",
        ),
        sa.CheckConstraint(
            (
                "payment_status IN ("
                "'processing', 'requires_action', 'succeeded', 'failed', "
                "'canceled', 'refunded', 'partially_refunded', 'disputed'"
                ")"
            ),
            name="ck_payments_payment_status",
        ),
        sa.CheckConstraint(
            "currency = 'USD'",
            name="ck_payments_currency",
        ),
        sa.CheckConstraint(
            "amount_cents >= 0",
            name="ck_payments_amount_cents",
        ),
        sa.CheckConstraint(
            "(payment_type <> 'booking' OR booking_id IS NOT NULL)",
            name="ck_payments_booking_requires_booking_id",
        ),
        sa.CheckConstraint(
            "(payment_type <> 'host_deposit' OR game_id IS NOT NULL)",
            name="ck_payments_host_deposit_requires_game_id",
        ),
        sa.CheckConstraint(
            "(payment_status <> 'succeeded' OR paid_at IS NOT NULL)",
            name="ck_payments_succeeded_requires_paid_at",
        ),
        sa.ForeignKeyConstraint(
            ["payer_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["booking_id"],
            ["bookings.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["games.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider_payment_intent_id",
            name="uq_payments_provider_payment_intent_id",
        ),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_payments_idempotency_key",
        ),
    )
    op.create_index(
        "ix_payments_payer_user_id",
        "payments",
        ["payer_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_payments_booking_id",
        "payments",
        ["booking_id"],
        unique=False,
    )
    op.create_index(
        "ix_payments_game_id",
        "payments",
        ["game_id"],
        unique=False,
    )
    op.create_index(
        "ix_payments_payment_type",
        "payments",
        ["payment_type"],
        unique=False,
    )
    op.create_index(
        "ix_payments_payment_status",
        "payments",
        ["payment_status"],
        unique=False,
    )


def downgrade() -> None:
    # Downgrade removes the payments table and its indexes because this
    # migration only introduces that single table.
    op.drop_index("ix_payments_payment_status", table_name="payments")
    op.drop_index("ix_payments_payment_type", table_name="payments")
    op.drop_index("ix_payments_game_id", table_name="payments")
    op.drop_index("ix_payments_booking_id", table_name="payments")
    op.drop_index("ix_payments_payer_user_id", table_name="payments")
    op.drop_table("payments")
