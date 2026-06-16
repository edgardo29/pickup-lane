"""create sub post chats table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0039_sub_post_chats"
down_revision = "0038_paid_waitlist_auto_charge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sub_post_chats",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sub_post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "chat_status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'active'"),
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
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "chat_status IN ('active', 'closed', 'archived')",
            name="ck_sub_post_chats_chat_status",
        ),
        sa.CheckConstraint(
            "(chat_status = 'active' OR closed_at IS NOT NULL)",
            name="ck_sub_post_chats_closed_requires_closed_at",
        ),
        sa.ForeignKeyConstraint(
            ["sub_post_id"],
            ["sub_posts.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sub_post_id", name="uq_sub_post_chats_sub_post_id"),
    )
    op.create_index(
        "ix_sub_post_chats_sub_post_id",
        "sub_post_chats",
        ["sub_post_id"],
    )
    op.create_index(
        "ix_sub_post_chats_chat_status",
        "sub_post_chats",
        ["chat_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_sub_post_chats_chat_status", table_name="sub_post_chats")
    op.drop_index("ix_sub_post_chats_sub_post_id", table_name="sub_post_chats")
    op.drop_table("sub_post_chats")
