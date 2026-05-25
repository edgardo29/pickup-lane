"""create game chat reads"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0033_game_chat_reads"
down_revision = "0032_community_hosting_model"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "game_chat_reads",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chat_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "last_read_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("last_read_message_id", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.ForeignKeyConstraint(["chat_id"], ["game_chats.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["last_read_message_id"],
            ["chat_messages.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chat_id", "user_id", name="uq_game_chat_reads_chat_user"),
    )
    op.create_index("ix_game_chat_reads_chat_id", "game_chat_reads", ["chat_id"])
    op.create_index("ix_game_chat_reads_user_id", "game_chat_reads", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_game_chat_reads_user_id", table_name="game_chat_reads")
    op.drop_index("ix_game_chat_reads_chat_id", table_name="game_chat_reads")
    op.drop_table("game_chat_reads")
