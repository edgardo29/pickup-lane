"""create payment_method_operations table"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0065_payment_method_ops"
down_revision = "0064_payment_compensations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_method_operations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payment_method_id", postgresql.UUID(as_uuid=True)),
        sa.Column("operation_kind", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("provider_idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("provider_object_id", sa.String(length=255)),
        sa.Column("error_code", sa.String(length=100)),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("operation_kind IN ('setup_create', 'sync', 'set_default', 'detach', 'clear_default')", name="ck_payment_method_operations_kind"),
        sa.CheckConstraint("status IN ('pending', 'provider_unknown', 'succeeded', 'failed')", name="ck_payment_method_operations_status"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["payment_method_id"], ["user_payment_methods.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_payment_method_operations_user_created", "payment_method_operations", ["user_id", "created_at", "id"])
    op.create_index("uq_payment_method_operations_fingerprint", "payment_method_operations", ["user_id", "operation_kind", "request_fingerprint"], unique=True)
    op.create_index("uq_payment_method_operations_idempotency", "payment_method_operations", ["provider_idempotency_key"], unique=True)
    op.create_index(
        "uq_payment_method_operations_active_user",
        "payment_method_operations",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('pending', 'provider_unknown')"),
    )


def downgrade() -> None:
    op.drop_table("payment_method_operations")
