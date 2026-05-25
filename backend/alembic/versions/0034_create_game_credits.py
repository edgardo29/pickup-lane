"""create game credits tables"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0034_game_credits"
down_revision = "0033_game_chat_reads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "game_credits",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("remaining_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.CHAR(length=3), server_default=sa.text("'USD'"), nullable=False),
        sa.Column("credit_status", sa.String(length=30), server_default=sa.text("'active'"), nullable=False),
        sa.Column("credit_reason", sa.String(length=40), nullable=False),
        sa.Column("source_game_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_booking_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_payment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("issued_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reversed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("credit_status IN ('active', 'used', 'expired', 'reversed')", name="ck_game_credits_credit_status"),
        sa.CheckConstraint(
            "credit_reason IN ('official_game_cancelled', 'weather_cancelled', 'player_cancelled_on_time', 'admin_credit', 'support_adjustment')",
            name="ck_game_credits_credit_reason",
        ),
        sa.CheckConstraint("currency = 'USD'", name="ck_game_credits_currency"),
        sa.CheckConstraint("amount_cents > 0", name="ck_game_credits_amount_cents"),
        sa.CheckConstraint("remaining_cents >= 0", name="ck_game_credits_remaining_cents_non_negative"),
        sa.CheckConstraint("remaining_cents <= amount_cents", name="ck_game_credits_remaining_not_above_amount"),
        sa.CheckConstraint("(credit_status = 'active' OR remaining_cents = 0)", name="ck_game_credits_inactive_has_no_remaining"),
        sa.ForeignKeyConstraint(["issued_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reversed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_booking_id"], ["bookings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_game_id"], ["games.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_payment_id"], ["payments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_game_credits_idempotency_key"),
    )
    op.create_index("ix_game_credits_created_at", "game_credits", ["created_at"])
    op.create_index("ix_game_credits_credit_reason", "game_credits", ["credit_reason"])
    op.create_index("ix_game_credits_credit_status", "game_credits", ["credit_status"])
    op.create_index("ix_game_credits_source_booking_id", "game_credits", ["source_booking_id"])
    op.create_index("ix_game_credits_source_game_id", "game_credits", ["source_game_id"])
    op.create_index("ix_game_credits_user_id", "game_credits", ["user_id"])
    op.create_index("ix_game_credits_user_id_credit_status", "game_credits", ["user_id", "credit_status"])

    op.create_table(
        "game_credit_usage",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_credit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.CHAR(length=3), server_default=sa.text("'USD'"), nullable=False),
        sa.Column("usage_type", sa.String(length=30), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("usage_type IN ('redeem', 'reverse')", name="ck_game_credit_usage_usage_type"),
        sa.CheckConstraint("currency = 'USD'", name="ck_game_credit_usage_currency"),
        sa.CheckConstraint("amount_cents > 0", name="ck_game_credit_usage_amount_cents"),
        sa.CheckConstraint("(usage_type <> 'redeem' OR booking_id IS NOT NULL)", name="ck_game_credit_usage_redeem_requires_booking"),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["game_credit_id"], ["game_credits.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_game_credit_usage_idempotency_key"),
    )
    op.create_index("ix_game_credit_usage_booking_id", "game_credit_usage", ["booking_id"])
    op.create_index("ix_game_credit_usage_created_at", "game_credit_usage", ["created_at"])
    op.create_index("ix_game_credit_usage_game_credit_id", "game_credit_usage", ["game_credit_id"])
    op.create_index("ix_game_credit_usage_usage_type", "game_credit_usage", ["usage_type"])
    op.create_index("ix_game_credit_usage_user_id", "game_credit_usage", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_game_credit_usage_user_id", table_name="game_credit_usage")
    op.drop_index("ix_game_credit_usage_usage_type", table_name="game_credit_usage")
    op.drop_index("ix_game_credit_usage_game_credit_id", table_name="game_credit_usage")
    op.drop_index("ix_game_credit_usage_created_at", table_name="game_credit_usage")
    op.drop_index("ix_game_credit_usage_booking_id", table_name="game_credit_usage")
    op.drop_table("game_credit_usage")

    op.drop_index("ix_game_credits_user_id_credit_status", table_name="game_credits")
    op.drop_index("ix_game_credits_user_id", table_name="game_credits")
    op.drop_index("ix_game_credits_source_game_id", table_name="game_credits")
    op.drop_index("ix_game_credits_source_booking_id", table_name="game_credits")
    op.drop_index("ix_game_credits_credit_status", table_name="game_credits")
    op.drop_index("ix_game_credits_credit_reason", table_name="game_credits")
    op.drop_index("ix_game_credits_created_at", table_name="game_credits")
    op.drop_table("game_credits")
