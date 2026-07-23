"""create game credit usage table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0036_game_credit_usage"
down_revision = "0035_game_credits"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "game_credit_usage",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_credit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("game_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("original_usage_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column(
            "currency",
            sa.CHAR(length=3),
            server_default=sa.text("'USD'"),
            nullable=False,
        ),
        sa.Column("usage_type", sa.String(length=30), nullable=False),
        sa.Column("usage_status", sa.String(length=30), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("reason_code", sa.String(length=80), nullable=True),
        sa.Column("reserved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "usage_type IN ('redeem', 'reverse', 'restore')",
            name="ck_game_credit_usage_usage_type",
        ),
        sa.CheckConstraint(
            (
                "usage_status IN ('reserved', 'redeemed', 'released', "
                "'reversed', 'restored')"
            ),
            name="ck_game_credit_usage_usage_status",
        ),
        sa.CheckConstraint(
            (
                "((usage_type = 'redeem' AND usage_status IN "
                "('reserved', 'redeemed', 'released')) OR "
                "(usage_type = 'reverse' AND usage_status = 'reversed') OR "
                "(usage_type = 'restore' AND usage_status = 'restored'))"
            ),
            name="ck_game_credit_usage_type_status_match",
        ),
        sa.CheckConstraint("currency = 'USD'", name="ck_game_credit_usage_currency"),
        sa.CheckConstraint(
            "amount_cents > 0",
            name="ck_game_credit_usage_amount_cents",
        ),
        sa.CheckConstraint(
            "(usage_type <> 'redeem' OR booking_id IS NOT NULL)",
            name="ck_game_credit_usage_redeem_requires_booking",
        ),
        sa.CheckConstraint(
            "(usage_status <> 'reserved' OR reserved_at IS NOT NULL)",
            name="ck_game_credit_usage_reserved_requires_reserved_at",
        ),
        sa.CheckConstraint(
            "(usage_status <> 'redeemed' OR redeemed_at IS NOT NULL)",
            name="ck_game_credit_usage_redeemed_requires_redeemed_at",
        ),
        sa.CheckConstraint(
            "(usage_status <> 'released' OR released_at IS NOT NULL)",
            name="ck_game_credit_usage_released_requires_released_at",
        ),
        sa.CheckConstraint(
            "(usage_type <> 'restore' OR original_usage_id IS NOT NULL)",
            name="ck_game_credit_usage_restore_requires_original_usage",
        ),
        sa.ForeignKeyConstraint(
            ["booking_id"],
            ["bookings.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["game_credit_id"],
            ["game_credits.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["original_usage_id"],
            ["game_credit_usage.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_game_credit_usage_idempotency_key",
        ),
    )
    op.create_index(
        "ix_game_credit_usage_booking_id",
        "game_credit_usage",
        ["booking_id"],
    )
    op.create_index(
        "ix_game_credit_usage_created_at",
        "game_credit_usage",
        ["created_at"],
    )
    op.create_index("ix_game_credit_usage_game_id", "game_credit_usage", ["game_id"])
    op.create_index(
        "ix_game_credit_usage_game_credit_id",
        "game_credit_usage",
        ["game_credit_id"],
    )
    op.create_index(
        "ix_game_credit_usage_credit_created",
        "game_credit_usage",
        ["game_credit_id", "created_at", "id"],
    )
    op.create_index(
        "ix_game_credit_usage_credit_status",
        "game_credit_usage",
        ["game_credit_id", "usage_status"],
    )
    op.create_index(
        "ix_game_credit_usage_payment_id",
        "game_credit_usage",
        ["payment_id"],
    )
    op.create_index(
        "ix_game_credit_usage_original_usage_id",
        "game_credit_usage",
        ["original_usage_id"],
    )
    op.create_index(
        "uq_game_credit_usage_one_restore_per_original",
        "game_credit_usage",
        ["original_usage_id"],
        unique=True,
        postgresql_where=sa.text(
            "usage_type = 'restore' "
            "AND usage_status = 'restored' "
            "AND original_usage_id IS NOT NULL"
        ),
    )
    op.create_index(
        "ix_game_credit_usage_usage_status",
        "game_credit_usage",
        ["usage_status"],
    )
    op.create_index(
        "ix_game_credit_usage_usage_type",
        "game_credit_usage",
        ["usage_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_game_credit_usage_usage_type", table_name="game_credit_usage")
    op.drop_index(
        "ix_game_credit_usage_usage_status",
        table_name="game_credit_usage",
    )
    op.drop_index("ix_game_credit_usage_payment_id", table_name="game_credit_usage")
    op.drop_index(
        "uq_game_credit_usage_one_restore_per_original",
        table_name="game_credit_usage",
    )
    op.drop_index("ix_game_credit_usage_original_usage_id", table_name="game_credit_usage")
    op.drop_index(
        "ix_game_credit_usage_game_credit_id",
        table_name="game_credit_usage",
    )
    op.drop_index(
        "ix_game_credit_usage_credit_status",
        table_name="game_credit_usage",
    )
    op.drop_index(
        "ix_game_credit_usage_credit_created",
        table_name="game_credit_usage",
    )
    op.drop_index("ix_game_credit_usage_game_id", table_name="game_credit_usage")
    op.drop_index("ix_game_credit_usage_created_at", table_name="game_credit_usage")
    op.drop_index("ix_game_credit_usage_booking_id", table_name="game_credit_usage")
    op.drop_table("game_credit_usage")
