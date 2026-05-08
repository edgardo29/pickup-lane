"""create sub post status history table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0031_sub_post_history"
down_revision = "0030_sub_req_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Thirty-first schema migration: create the audit trail for Need a Sub
    # post status changes.
    op.create_table(
        "sub_post_status_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sub_post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("old_status", sa.String(length=30), nullable=True),
        sa.Column("new_status", sa.String(length=30), nullable=False),
        sa.Column("changed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("change_source", sa.String(length=30), nullable=False),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "new_status IN ('draft', 'active', 'filled', 'expired', 'canceled', 'removed')",
            name="ck_sub_post_status_history_new_status",
        ),
        sa.CheckConstraint(
            (
                "old_status IS NULL OR old_status IN ('draft', 'active', "
                "'filled', 'expired', 'canceled', 'removed')"
            ),
            name="ck_sub_post_status_history_old_status",
        ),
        sa.CheckConstraint(
            "change_source IN ('owner', 'admin', 'system', 'scheduled_job')",
            name="ck_sub_post_status_history_change_source",
        ),
        sa.ForeignKeyConstraint(
            ["sub_post_id"],
            ["sub_posts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["changed_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_sub_post_status_history_post_created",
        "sub_post_status_history",
        ["sub_post_id", "created_at"],
    )
    op.create_index(
        "ix_sub_post_status_history_changed_by_user_id",
        "sub_post_status_history",
        ["changed_by_user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_sub_post_status_history_changed_by_user_id",
        table_name="sub_post_status_history",
    )
    op.drop_index(
        "ix_sub_post_status_history_post_created",
        table_name="sub_post_status_history",
    )
    op.drop_table("sub_post_status_history")
