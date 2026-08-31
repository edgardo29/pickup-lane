"""create payment_compensations table"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0064_payment_compensations"
down_revision = "0063_payment_confirm_attempts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_compensations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=30), nullable=False, server_default=sa.text("'refund'")),
        sa.Column("reason", sa.String(length=50), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.CHAR(length=3), nullable=False, server_default=sa.text("'USD'")),
        sa.Column("status", sa.String(length=30), nullable=False, server_default=sa.text("'required'")),
        sa.Column("error_code", sa.String(length=100)),
        sa.Column("processing_started_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("action = 'refund'", name="ck_payment_compensations_action"),
        sa.CheckConstraint("reason IN ('reservation_expired', 'capacity_conflict', 'booking_cancelled')", name="ck_payment_compensations_reason"),
        sa.CheckConstraint("status IN ('required', 'processing', 'succeeded', 'failed', 'cancelled')", name="ck_payment_compensations_status"),
        sa.CheckConstraint("amount_cents > 0", name="ck_payment_compensations_amount"),
        sa.CheckConstraint("currency = 'USD'", name="ck_payment_compensations_currency"),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_payment_compensations_payment", "payment_compensations", ["payment_id", "created_at", "id"])
    op.create_index("ix_payment_compensations_booking", "payment_compensations", ["booking_id", "created_at", "id"])
    op.create_index("uq_payment_compensations_active", "payment_compensations", ["payment_id", "booking_id"], unique=True, postgresql_where=sa.text("status IN ('required', 'processing')"))


def downgrade() -> None:
    op.drop_table("payment_compensations")
