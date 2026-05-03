"""create chat messages table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0013_chat_messages"
down_revision = "0012_game_chats"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Thirteenth schema migration: create chat_messages as the message-level
    # records stored inside each game chat room.
    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chat_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "message_type",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'text'"),
        ),
        sa.Column("message_body", sa.Text(), nullable=False),
        sa.Column(
            "is_pinned",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("pinned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pinned_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "moderation_status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'visible'"),
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
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint(
            "message_type IN ('text', 'system', 'pinned_update')",
            name="ck_chat_messages_message_type",
        ),
        sa.CheckConstraint(
            (
                "moderation_status IN ("
                "'visible', 'hidden_by_admin', 'deleted_by_sender', 'flagged'"
                ")"
            ),
            name="ck_chat_messages_moderation_status",
        ),
        sa.CheckConstraint(
            "char_length(btrim(message_body)) > 0",
            name="ck_chat_messages_message_body_not_empty",
        ),
        sa.CheckConstraint(
            "(is_pinned = false OR pinned_at IS NOT NULL)",
            name="ck_chat_messages_pinned_requires_pinned_at",
        ),
        sa.CheckConstraint(
            "(is_pinned = false OR pinned_by_user_id IS NOT NULL)",
            name="ck_chat_messages_pinned_requires_pinned_by_user",
        ),
        sa.CheckConstraint(
            (
                "(moderation_status <> 'deleted_by_sender' "
                "OR deleted_at IS NOT NULL)"
            ),
            name="ck_chat_messages_deleted_by_sender_requires_deleted_at",
        ),
        sa.CheckConstraint(
            (
                "(moderation_status <> 'hidden_by_admin' "
                "OR deleted_at IS NOT NULL)"
            ),
            name="ck_chat_messages_hidden_by_admin_requires_deleted_at",
        ),
        sa.CheckConstraint(
            (
                "(message_type NOT IN ('text', 'pinned_update') "
                "OR sender_user_id IS NOT NULL)"
            ),
            name="ck_chat_messages_user_messages_require_sender",
        ),
        sa.ForeignKeyConstraint(
            ["chat_id"],
            ["game_chats.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["sender_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["pinned_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["deleted_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_chat_messages_chat_id",
        "chat_messages",
        ["chat_id"],
        unique=False,
    )
    op.create_index(
        "ix_chat_messages_sender_user_id",
        "chat_messages",
        ["sender_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_chat_messages_pinned_by_user_id",
        "chat_messages",
        ["pinned_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_chat_messages_deleted_by_user_id",
        "chat_messages",
        ["deleted_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_chat_messages_moderation_status",
        "chat_messages",
        ["moderation_status"],
        unique=False,
    )
    op.create_index(
        "ix_chat_messages_chat_id_created_at",
        "chat_messages",
        ["chat_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_chat_messages_chat_id_is_pinned",
        "chat_messages",
        ["chat_id", "is_pinned"],
        unique=False,
    )


def downgrade() -> None:
    # Downgrade removes the chat_messages table and indexes because this
    # migration only introduces that single table.
    op.drop_index("ix_chat_messages_chat_id_is_pinned", table_name="chat_messages")
    op.drop_index("ix_chat_messages_chat_id_created_at", table_name="chat_messages")
    op.drop_index("ix_chat_messages_moderation_status", table_name="chat_messages")
    op.drop_index("ix_chat_messages_deleted_by_user_id", table_name="chat_messages")
    op.drop_index("ix_chat_messages_pinned_by_user_id", table_name="chat_messages")
    op.drop_index("ix_chat_messages_sender_user_id", table_name="chat_messages")
    op.drop_index("ix_chat_messages_chat_id", table_name="chat_messages")
    op.drop_table("chat_messages")