"""create host deposits table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0011_host_deposits"
down_revision = "0010_refunds"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Eleventh schema migration: create host_deposits for community-hosted game
    # deposit lifecycle tracking.
    op.create_table(
        "host_deposits",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("host_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("required_amount_cents", sa.Integer(), nullable=False),
        sa.Column(
            "currency",
            sa.CHAR(length=3),
            nullable=False,
            server_default=sa.text("'USD'"),
        ),
        sa.Column(
            "deposit_status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'required'"),
        ),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("refund_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("forfeited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "decision_by_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("decision_reason", sa.Text(), nullable=True),
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
                "deposit_status IN ("
                "'required', 'payment_pending', 'paid', 'held', 'released', "
                "'refunded', 'forfeited', 'waived'"
                ")"
            ),
            name="ck_host_deposits_deposit_status",
        ),
        sa.CheckConstraint(
            "currency = 'USD'",
            name="ck_host_deposits_currency",
        ),
        sa.CheckConstraint(
            "required_amount_cents >= 0",
            name="ck_host_deposits_required_amount_cents",
        ),
        sa.CheckConstraint(
            (
                "(deposit_status NOT IN "
                "('paid', 'held', 'released', 'refunded', 'forfeited') "
                "OR payment_id IS NOT NULL)"
            ),
            name="ck_host_deposits_payment_statuses_require_payment",
        ),
        sa.CheckConstraint(
            "(deposit_status <> 'paid' OR paid_at IS NOT NULL)",
            name="ck_host_deposits_paid_requires_paid_at",
        ),
        sa.CheckConstraint(
            "(deposit_status <> 'held' OR paid_at IS NOT NULL)",
            name="ck_host_deposits_held_requires_paid_at",
        ),
        sa.CheckConstraint(
            "(deposit_status <> 'released' OR released_at IS NOT NULL)",
            name="ck_host_deposits_released_requires_released_at",
        ),
        sa.CheckConstraint(
            "(deposit_status <> 'refunded' OR refunded_at IS NOT NULL)",
            name="ck_host_deposits_refunded_requires_refunded_at",
        ),
        sa.CheckConstraint(
            "(deposit_status <> 'refunded' OR refund_id IS NOT NULL)",
            name="ck_host_deposits_refunded_requires_refund",
        ),
        sa.CheckConstraint(
            "(deposit_status <> 'forfeited' OR forfeited_at IS NOT NULL)",
            name="ck_host_deposits_forfeited_requires_forfeited_at",
        ),
        sa.CheckConstraint(
            "(deposit_status <> 'forfeited' OR decision_reason IS NOT NULL)",
            name="ck_host_deposits_forfeited_requires_decision_reason",
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
        sa.ForeignKeyConstraint(
            ["refund_id"],
            ["refunds.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["decision_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("game_id", name="uq_host_deposits_game_id"),
        sa.UniqueConstraint("payment_id", name="uq_host_deposits_payment_id"),
        sa.UniqueConstraint("refund_id", name="uq_host_deposits_refund_id"),
    )
    op.create_index(
        "ix_host_deposits_host_user_id",
        "host_deposits",
        ["host_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_host_deposits_deposit_status",
        "host_deposits",
        ["deposit_status"],
        unique=False,
    )
    op.create_index(
        "ix_host_deposits_decision_by_user_id",
        "host_deposits",
        ["decision_by_user_id"],
        unique=False,
    )


def downgrade() -> None:
    # Downgrade removes the host_deposits table and indexes because this
    # migration only introduces that single table.
    op.drop_index("ix_host_deposits_decision_by_user_id", table_name="host_deposits")
    op.drop_index("ix_host_deposits_deposit_status", table_name="host_deposits")
    op.drop_index("ix_host_deposits_host_user_id", table_name="host_deposits")
    op.drop_table("host_deposits")
