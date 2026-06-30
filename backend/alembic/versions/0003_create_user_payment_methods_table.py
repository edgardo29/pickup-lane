"""create user payment methods table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0003_user_payment_methods"
down_revision = "0002_create_user_settings_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Third schema migration: create the payment-method reference table for
    # storing Stripe-linked saved card records per user.
    op.create_table(
        "user_payment_methods",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "stripe_customer_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "stripe_payment_method_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column("card_fingerprint", sa.String(length=255), nullable=False),
        sa.Column("card_brand", sa.String(length=50), nullable=False),
        sa.Column("card_last4", sa.String(length=4), nullable=False),
        sa.Column("exp_month", sa.SmallInteger(), nullable=False),
        sa.Column("exp_year", sa.SmallInteger(), nullable=False),
        sa.Column(
            "method_status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column(
            "is_default",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
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
        sa.Column("detached_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "method_status IN ('active', 'detached', 'expired')",
            name="ck_user_payment_methods_method_status",
        ),
        sa.CheckConstraint(
            "exp_month BETWEEN 1 AND 12",
            name="ck_user_payment_methods_exp_month",
        ),
        sa.CheckConstraint(
            "char_length(card_last4) = 4",
            name="ck_user_payment_methods_card_last4",
        ),
        sa.CheckConstraint(
            "(is_default = false OR method_status = 'active')",
            name="ck_user_payment_methods_default_requires_active",
        ),
        sa.CheckConstraint(
            "(method_status = 'detached' OR detached_at IS NULL)",
            name="ck_user_payment_methods_detached_at_status",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "stripe_payment_method_id",
            name="uq_user_payment_methods_stripe_payment_method_id",
        ),
    )
    op.create_index(
        "ix_user_payment_methods_user_id",
        "user_payment_methods",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_payment_methods_one_active_default_per_user",
        "user_payment_methods",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text(
            "is_default = true AND method_status = 'active'"
        ),
    )
    op.create_index(
        "ix_user_payment_methods_user_status",
        "user_payment_methods",
        ["user_id", "method_status"],
        unique=False,
    )
    op.create_index(
        "ix_user_payment_methods_user_card_fingerprint",
        "user_payment_methods",
        ["user_id", "card_fingerprint"],
        unique=True,
    )


def downgrade() -> None:
    # Downgrade removes the payment-method table and its indexes because this
    # migration only introduces that single table.
    op.drop_index(
        "ix_user_payment_methods_user_card_fingerprint",
        table_name="user_payment_methods",
    )
    op.drop_index(
        "ix_user_payment_methods_one_active_default_per_user",
        table_name="user_payment_methods",
    )
    op.drop_index(
        "ix_user_payment_methods_user_status",
        table_name="user_payment_methods",
    )
    op.drop_index(
        "ix_user_payment_methods_user_id",
        table_name="user_payment_methods",
    )
    op.drop_table("user_payment_methods")
