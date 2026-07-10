"""create chat messages table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0013_chat_messages"
down_revision = "0012_game_chats"
branch_labels = None
depends_on = None


CHAT_DETECTION_CATEGORIES = (
    "'phone_number', 'email', 'link', 'off_platform_contact', "
    "'payment_discussion', 'harassment_or_abuse', 'threat_or_safety', "
    "'slur_or_hate', 'spam_or_repeated_message'"
)


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
            "visibility_status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'visible'"),
        ),
        sa.Column(
            "review_status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'clear'"),
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
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("removed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("removed_source", sa.String(length=30), nullable=True),
        sa.Column("removed_reason", sa.Text(), nullable=True),
        sa.Column("restored_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("restored_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("restored_reason", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "message_type IN ('text', 'system', 'pinned_update')",
            name="ck_chat_messages_message_type",
        ),
        sa.CheckConstraint(
            "visibility_status IN ('visible', 'removed')",
            name="ck_chat_messages_visibility_status",
        ),
        sa.CheckConstraint(
            "review_status IN ('clear', 'needs_review', 'reviewed')",
            name="ck_chat_messages_review_status",
        ),
        sa.CheckConstraint(
            "removed_source IS NULL OR removed_source IN ('admin', 'sender', 'system')",
            name="ck_chat_messages_removed_source",
        ),
        sa.CheckConstraint(
            "char_length(btrim(message_body)) > 0",
            name="ck_chat_messages_message_body_not_empty",
        ),
        sa.CheckConstraint(
            "char_length(message_body) <= 300",
            name="ck_chat_messages_message_body_max_length",
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
            "(visibility_status <> 'removed' OR removed_at IS NOT NULL)",
            name="ck_chat_messages_removed_requires_removed_at",
        ),
        sa.CheckConstraint(
            "(visibility_status <> 'removed' OR removed_source IS NOT NULL)",
            name="ck_chat_messages_removed_requires_source",
        ),
        sa.CheckConstraint(
            "(review_status <> 'reviewed' OR reviewed_at IS NOT NULL)",
            name="ck_chat_messages_reviewed_requires_reviewed_at",
        ),
        sa.CheckConstraint(
            (
                "(message_type NOT IN ('text', 'pinned_update') "
                "OR sender_user_id IS NOT NULL)"
            ),
            name="ck_chat_messages_user_messages_require_sender",
        ),
        sa.ForeignKeyConstraint(["chat_id"], ["game_chats.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["pinned_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["removed_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["restored_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_messages_chat_id", "chat_messages", ["chat_id"])
    op.create_index(
        "ix_chat_messages_sender_user_id",
        "chat_messages",
        ["sender_user_id"],
    )
    op.create_index(
        "ix_chat_messages_pinned_by_user_id",
        "chat_messages",
        ["pinned_by_user_id"],
    )
    op.create_index(
        "ix_chat_messages_removed_by_user_id",
        "chat_messages",
        ["removed_by_user_id"],
    )
    op.create_index(
        "ix_chat_messages_reviewed_by_user_id",
        "chat_messages",
        ["reviewed_by_user_id"],
    )
    op.create_index(
        "ix_chat_messages_restored_by_user_id",
        "chat_messages",
        ["restored_by_user_id"],
    )
    op.create_index(
        "ix_chat_messages_visibility_status",
        "chat_messages",
        ["visibility_status"],
    )
    op.create_index(
        "ix_chat_messages_review_status",
        "chat_messages",
        ["review_status"],
    )
    op.create_index(
        "ix_chat_messages_chat_id_created_at",
        "chat_messages",
        ["chat_id", "created_at"],
    )
    op.create_index(
        "ix_chat_messages_chat_id_review_status",
        "chat_messages",
        ["chat_id", "review_status"],
    )
    op.create_index(
        "ix_chat_messages_chat_id_visibility_status",
        "chat_messages",
        ["chat_id", "visibility_status"],
    )
    op.create_index(
        "ix_chat_messages_chat_id_is_pinned",
        "chat_messages",
        ["chat_id", "is_pinned"],
    )
    op.create_foreign_key(
        "fk_game_chats_latest_message_id",
        "game_chats",
        "chat_messages",
        ["latest_message_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "game_chat_message_detections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("rule_key", sa.String(length=80), nullable=False),
        sa.Column("matched_preview", sa.String(length=240), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            f"category IN ({CHAT_DETECTION_CATEGORIES})",
            name="ck_game_chat_message_detections_category",
        ),
        sa.CheckConstraint(
            "severity IN ('low', 'medium', 'high')",
            name="ck_game_chat_message_detections_severity",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["chat_messages.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_game_chat_message_detections_message_id",
        "game_chat_message_detections",
        ["message_id"],
    )
    op.create_index(
        "ix_game_chat_message_detections_category",
        "game_chat_message_detections",
        ["category"],
    )
    op.create_index(
        "ix_game_chat_message_detections_created_at",
        "game_chat_message_detections",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_game_chat_message_detections_created_at",
        table_name="game_chat_message_detections",
    )
    op.drop_index(
        "ix_game_chat_message_detections_category",
        table_name="game_chat_message_detections",
    )
    op.drop_index(
        "ix_game_chat_message_detections_message_id",
        table_name="game_chat_message_detections",
    )
    op.drop_table("game_chat_message_detections")
    op.drop_constraint(
        "fk_game_chats_latest_message_id",
        "game_chats",
        type_="foreignkey",
    )
    op.drop_index("ix_chat_messages_chat_id_is_pinned", table_name="chat_messages")
    op.drop_index(
        "ix_chat_messages_chat_id_visibility_status",
        table_name="chat_messages",
    )
    op.drop_index(
        "ix_chat_messages_chat_id_review_status",
        table_name="chat_messages",
    )
    op.drop_index("ix_chat_messages_chat_id_created_at", table_name="chat_messages")
    op.drop_index("ix_chat_messages_review_status", table_name="chat_messages")
    op.drop_index("ix_chat_messages_visibility_status", table_name="chat_messages")
    op.drop_index("ix_chat_messages_restored_by_user_id", table_name="chat_messages")
    op.drop_index("ix_chat_messages_reviewed_by_user_id", table_name="chat_messages")
    op.drop_index("ix_chat_messages_removed_by_user_id", table_name="chat_messages")
    op.drop_index("ix_chat_messages_pinned_by_user_id", table_name="chat_messages")
    op.drop_index("ix_chat_messages_sender_user_id", table_name="chat_messages")
    op.drop_index("ix_chat_messages_chat_id", table_name="chat_messages")
    op.drop_table("chat_messages")
