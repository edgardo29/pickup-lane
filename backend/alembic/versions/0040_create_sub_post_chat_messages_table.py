"""create sub post chat messages table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0040_sub_post_chat_messages"
down_revision = "0039_sub_post_chats"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sub_post_chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chat_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "sender_display_name_snapshot",
            sa.String(length=120),
            nullable=False,
        ),
        sa.Column(
            "sender_initials_snapshot",
            sa.String(length=8),
            nullable=False,
        ),
        sa.Column(
            "message_type",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'text'"),
        ),
        sa.Column("message_body", sa.Text(), nullable=False),
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
            "message_type IN ('text')",
            name="ck_sub_post_chat_messages_message_type",
        ),
        sa.CheckConstraint(
            (
                "moderation_status IN ("
                "'visible', 'hidden_by_admin', 'deleted_by_sender', 'flagged'"
                ")"
            ),
            name="ck_sub_post_chat_messages_moderation_status",
        ),
        sa.CheckConstraint(
            "char_length(btrim(message_body)) > 0",
            name="ck_sub_post_chat_messages_body_not_empty",
        ),
        sa.CheckConstraint(
            "char_length(message_body) <= 300",
            name="ck_sub_post_chat_messages_body_max_length",
        ),
        sa.CheckConstraint(
            "char_length(btrim(sender_display_name_snapshot)) > 0",
            name="ck_sub_post_chat_messages_sender_name_not_empty",
        ),
        sa.CheckConstraint(
            "char_length(btrim(sender_initials_snapshot)) > 0",
            name="ck_sub_post_chat_messages_sender_initials_not_empty",
        ),
        sa.CheckConstraint(
            (
                "(moderation_status <> 'deleted_by_sender' "
                "OR deleted_at IS NOT NULL)"
            ),
            name="ck_sub_post_chat_messages_deleted_requires_deleted_at",
        ),
        sa.CheckConstraint(
            (
                "(moderation_status <> 'hidden_by_admin' "
                "OR deleted_at IS NOT NULL)"
            ),
            name="ck_sub_post_chat_messages_hidden_requires_deleted_at",
        ),
        sa.ForeignKeyConstraint(
            ["chat_id"],
            ["sub_post_chats.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["sender_user_id"],
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
        "ix_sub_post_chat_messages_chat_id",
        "sub_post_chat_messages",
        ["chat_id"],
    )
    op.create_index(
        "ix_sub_post_chat_messages_sender_user_id",
        "sub_post_chat_messages",
        ["sender_user_id"],
    )
    op.create_index(
        "ix_sub_post_chat_messages_deleted_by_user_id",
        "sub_post_chat_messages",
        ["deleted_by_user_id"],
    )
    op.create_index(
        "ix_sub_post_chat_messages_moderation_status",
        "sub_post_chat_messages",
        ["moderation_status"],
    )
    op.create_index(
        "ix_sub_post_chat_messages_chat_id_created_at",
        "sub_post_chat_messages",
        ["chat_id", "created_at"],
    )
    op.create_foreign_key(
        "fk_admin_actions_target_sub_chat_message_id",
        "admin_actions",
        "sub_post_chat_messages",
        ["target_sub_chat_message_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_notifications_related_sub_post_chat_message_id",
        "notifications",
        "sub_post_chat_messages",
        ["related_sub_post_chat_message_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_notifications_related_sub_post_chat_message_id",
        "notifications",
        type_="foreignkey",
    )
    op.execute(
        "ALTER TABLE admin_actions "
        "DROP CONSTRAINT IF EXISTS fk_admin_actions_target_sub_chat_message_id"
    )
    op.drop_index(
        "ix_sub_post_chat_messages_chat_id_created_at",
        table_name="sub_post_chat_messages",
    )
    op.drop_index(
        "ix_sub_post_chat_messages_moderation_status",
        table_name="sub_post_chat_messages",
    )
    op.drop_index(
        "ix_sub_post_chat_messages_deleted_by_user_id",
        table_name="sub_post_chat_messages",
    )
    op.drop_index(
        "ix_sub_post_chat_messages_sender_user_id",
        table_name="sub_post_chat_messages",
    )
    op.drop_index(
        "ix_sub_post_chat_messages_chat_id",
        table_name="sub_post_chat_messages",
    )
    op.drop_table("sub_post_chat_messages")
