"""create payment_confirmation_attempts table"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0063_payment_confirm_attempts"
down_revision = "0062_durable_worker_heartbeats"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_confirmation_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_customer_id", sa.String(length=255), nullable=False),
        sa.Column("provider_payment_method_id", sa.String(length=255), nullable=False),
        sa.Column("confirmation_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("confirmation_idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("outcome", sa.String(length=30), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("error_code", sa.String(length=100)),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("outcome IN ('pending', 'provider_unknown', 'succeeded', 'failed')", name="ck_payment_confirmation_attempts_outcome"),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_payment_confirmation_attempts_payment_created", "payment_confirmation_attempts", ["payment_id", "created_at", "id"])
    op.create_index("uq_payment_confirmation_attempts_fingerprint", "payment_confirmation_attempts", ["payment_id", "confirmation_fingerprint"], unique=True)
    op.create_index("uq_payment_confirmation_attempts_idempotency", "payment_confirmation_attempts", ["confirmation_idempotency_key"], unique=True)


def downgrade() -> None:
    op.drop_table("payment_confirmation_attempts")
