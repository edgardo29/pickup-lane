"""create community hosting model"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0032_community_hosting_model"
down_revision = "0031_sub_post_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Old local dev DBs may still have the removed host_profiles table from
    # the earlier version of this branch. Keep clean rebuilds deterministic.
    op.execute("DROP TABLE IF EXISTS host_profiles CASCADE")

    # Create per-game community payment snapshots and paid/waived publish fees.
    op.create_table(
        "community_game_details",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "payment_methods_snapshot",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("payment_instructions_snapshot", sa.Text(), nullable=True),
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
            "jsonb_typeof(payment_methods_snapshot) = 'array'",
            name="ck_community_game_details_payment_methods_array",
        ),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["games.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("game_id", name="uq_community_game_details_game_id"),
    )
    op.create_index(
        "ix_community_game_details_game_id",
        "community_game_details",
        ["game_id"],
    )

    op.create_table(
        "host_publish_fees",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("host_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column(
            "currency",
            sa.CHAR(length=3),
            nullable=False,
            server_default=sa.text("'USD'"),
        ),
        sa.Column(
            "fee_status",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "waiver_reason",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'none'"),
        ),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
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
            "amount_cents >= 0",
            name="ck_host_publish_fees_amount_cents",
        ),
        sa.CheckConstraint(
            "currency = 'USD'",
            name="ck_host_publish_fees_currency",
        ),
        sa.CheckConstraint(
            "fee_status IN ('paid', 'waived')",
            name="ck_host_publish_fees_fee_status",
        ),
        sa.CheckConstraint(
            "waiver_reason IN ('none', 'first_game_free', 'admin_comp')",
            name="ck_host_publish_fees_waiver_reason",
        ),
        sa.CheckConstraint(
            (
                "fee_status <> 'paid' OR ("
                "payment_id IS NOT NULL AND paid_at IS NOT NULL "
                "AND amount_cents > 0)"
            ),
            name="ck_host_publish_fees_paid_requires_payment",
        ),
        sa.CheckConstraint(
            (
                "fee_status <> 'waived' OR ("
                "amount_cents = 0 AND waiver_reason <> 'none' "
                "AND payment_id IS NULL)"
            ),
            name="ck_host_publish_fees_waived_requirements",
        ),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["games.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["host_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["payment_id"],
            ["payments.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("game_id", name="uq_host_publish_fees_game_id"),
        sa.UniqueConstraint("payment_id", name="uq_host_publish_fees_payment_id"),
    )
    op.create_index("ix_host_publish_fees_game_id", "host_publish_fees", ["game_id"])
    op.create_index(
        "ix_host_publish_fees_host_user_id",
        "host_publish_fees",
        ["host_user_id"],
    )
    op.create_index(
        "ix_host_publish_fees_fee_status",
        "host_publish_fees",
        ["fee_status"],
    )
    op.create_index(
        "ix_host_publish_fees_payment_id",
        "host_publish_fees",
        ["payment_id"],
    )
    op.create_index(
        "ux_host_publish_fees_one_first_free_per_host",
        "host_publish_fees",
        ["host_user_id"],
        unique=True,
        postgresql_where=sa.text("waiver_reason = 'first_game_free'"),
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS host_profiles CASCADE")

    op.drop_index(
        "ux_host_publish_fees_one_first_free_per_host",
        table_name="host_publish_fees",
        postgresql_where=sa.text("waiver_reason = 'first_game_free'"),
    )
    op.drop_index("ix_host_publish_fees_payment_id", table_name="host_publish_fees")
    op.drop_index("ix_host_publish_fees_fee_status", table_name="host_publish_fees")
    op.drop_index("ix_host_publish_fees_host_user_id", table_name="host_publish_fees")
    op.drop_index("ix_host_publish_fees_game_id", table_name="host_publish_fees")
    op.drop_table("host_publish_fees")

    op.drop_index(
        "ix_community_game_details_game_id",
        table_name="community_game_details",
    )
    op.drop_table("community_game_details")
