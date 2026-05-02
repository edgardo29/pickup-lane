"""create game chats table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0012_game_chats"
down_revision = "0011_host_deposits"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Twelfth schema migration: create game_chats as the one room-level chat
    # record attached to each game.
    op.create_table(
        "game_chats",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_id", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "chat_status IN ('active', 'locked', 'archived')",
            name="ck_game_chats_chat_status",
        ),
        sa.CheckConstraint(
            "(chat_status <> 'locked' OR locked_at IS NOT NULL)",
            name="ck_game_chats_locked_requires_locked_at",
        ),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["games.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("game_id", name="uq_game_chats_game_id"),
    )
    op.create_index(
        "ix_game_chats_chat_status",
        "game_chats",
        ["chat_status"],
        unique=False,
    )


def downgrade() -> None:
    # Downgrade removes the game_chats table and index because this migration
    # only introduces that single table.
    op.drop_index("ix_game_chats_chat_status", table_name="game_chats")
    op.drop_table("game_chats")
