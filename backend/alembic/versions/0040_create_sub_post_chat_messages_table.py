"""create sub post chat messages table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0040_sub_post_chat_messages"
down_revision = "0039_sub_post_chats"
branch_labels = None
depends_on = None


CHAT_DETECTION_CATEGORIES = (
    "'phone_number', 'email', 'link', 'off_platform_contact', "
    "'payment_discussion', 'harassment_or_abuse', 'threat_or_safety', "
    "'slur_or_hate', 'spam_or_repeated_message'"
)


def _target_required_check(columns: tuple[str, ...]) -> str:
    return " OR ".join(f"{column} IS NOT NULL" for column in columns)


PREVIOUS_ADMIN_ACTION_TARGET_COLUMNS = (
    "target_user_id",
    "target_game_id",
    "target_booking_id",
    "target_participant_id",
    "target_payment_id",
    "target_refund_id",
    "target_venue_id",
    "target_message_id",
    "target_notification_id",
    "target_admin_action_id",
    "target_sub_post_id",
    "target_sub_post_position_id",
    "target_sub_post_request_id",
    "target_game_credit_id",
    "target_venue_image_id",
)
ADMIN_ACTION_TARGET_COLUMNS = (
    *PREVIOUS_ADMIN_ACTION_TARGET_COLUMNS,
    "target_sub_chat_message_id",
)
PREVIOUS_ADMIN_ACTION_TARGET_REQUIRED_CHECK = _target_required_check(
    PREVIOUS_ADMIN_ACTION_TARGET_COLUMNS
)
ADMIN_ACTION_TARGET_REQUIRED_CHECK = _target_required_check(
    ADMIN_ACTION_TARGET_COLUMNS
)


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
            "message_type IN ('text')",
            name="ck_sub_post_chat_messages_message_type",
        ),
        sa.CheckConstraint(
            "visibility_status IN ('visible', 'removed')",
            name="ck_sub_post_chat_messages_visibility_status",
        ),
        sa.CheckConstraint(
            "review_status IN ('clear', 'needs_review', 'reviewed')",
            name="ck_sub_post_chat_messages_review_status",
        ),
        sa.CheckConstraint(
            "removed_source IS NULL OR removed_source IN ('admin', 'sender', 'system')",
            name="ck_sub_post_chat_messages_removed_source",
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
            "(visibility_status <> 'removed' OR removed_at IS NOT NULL)",
            name="ck_sub_post_chat_messages_removed_requires_removed_at",
        ),
        sa.CheckConstraint(
            "(visibility_status <> 'removed' OR removed_source IS NOT NULL)",
            name="ck_sub_post_chat_messages_removed_requires_source",
        ),
        sa.CheckConstraint(
            "(review_status <> 'reviewed' OR reviewed_at IS NOT NULL)",
            name="ck_sub_post_chat_messages_reviewed_requires_reviewed_at",
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
        "ix_sub_post_chat_messages_removed_by_user_id",
        "sub_post_chat_messages",
        ["removed_by_user_id"],
    )
    op.create_index(
        "ix_sub_post_chat_messages_reviewed_by_user_id",
        "sub_post_chat_messages",
        ["reviewed_by_user_id"],
    )
    op.create_index(
        "ix_sub_post_chat_messages_restored_by_user_id",
        "sub_post_chat_messages",
        ["restored_by_user_id"],
    )
    op.create_index(
        "ix_sub_post_chat_messages_visibility_status",
        "sub_post_chat_messages",
        ["visibility_status"],
    )
    op.create_index(
        "ix_sub_post_chat_messages_review_status",
        "sub_post_chat_messages",
        ["review_status"],
    )
    op.create_index(
        "ix_sub_post_chat_messages_chat_id_created_at",
        "sub_post_chat_messages",
        ["chat_id", "created_at"],
    )
    op.create_index(
        "ix_sub_post_chat_messages_chat_id_review_status",
        "sub_post_chat_messages",
        ["chat_id", "review_status"],
    )
    op.create_index(
        "ix_sub_post_chat_messages_chat_id_visibility_status",
        "sub_post_chat_messages",
        ["chat_id", "visibility_status"],
    )
    op.create_foreign_key(
        "fk_sub_post_chats_latest_message_id",
        "sub_post_chats",
        "sub_post_chat_messages",
        ["latest_message_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "sub_post_chat_message_detections",
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
            name="ck_sub_post_chat_message_detections_category",
        ),
        sa.CheckConstraint(
            "severity IN ('low', 'medium', 'high')",
            name="ck_sub_post_chat_message_detections_severity",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["sub_post_chat_messages.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_sub_post_chat_message_detections_message_id",
        "sub_post_chat_message_detections",
        ["message_id"],
    )
    op.create_index(
        "ix_sub_post_chat_message_detections_category",
        "sub_post_chat_message_detections",
        ["category"],
    )
    op.create_index(
        "ix_sub_post_chat_message_detections_created_at",
        "sub_post_chat_message_detections",
        ["created_at"],
    )

    op.add_column(
        "admin_actions",
        sa.Column(
            "target_sub_chat_message_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_admin_actions_target_sub_chat_message_id",
        "admin_actions",
        ["target_sub_chat_message_id"],
    )
    for action_type, index_name in (
        (
            "mark_chat_message_reviewed",
            "uq_admin_actions_mark_reviewed_sub_chat_message_idempotency",
        ),
        (
            "remove_chat_message",
            "uq_admin_actions_remove_sub_chat_message_idempotency",
        ),
        (
            "restore_chat_message",
            "uq_admin_actions_restore_sub_chat_message_idempotency",
        ),
    ):
        op.create_index(
            index_name,
            "admin_actions",
            ["admin_user_id", "target_sub_chat_message_id", "idempotency_key"],
            unique=True,
            postgresql_where=sa.text(
                f"action_type = '{action_type}' "
                "AND target_sub_chat_message_id IS NOT NULL "
                "AND idempotency_key IS NOT NULL"
            ),
        )
    op.drop_constraint(
        "ck_admin_actions_target_required",
        "admin_actions",
        type_="check",
    )
    op.create_check_constraint(
        "ck_admin_actions_target_required",
        "admin_actions",
        ADMIN_ACTION_TARGET_REQUIRED_CHECK,
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
    op.execute(
        "DELETE FROM admin_actions WHERE target_sub_chat_message_id IS NOT NULL"
    )
    op.drop_constraint(
        "fk_notifications_related_sub_post_chat_message_id",
        "notifications",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_admin_actions_target_sub_chat_message_id",
        "admin_actions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "ck_admin_actions_target_required",
        "admin_actions",
        type_="check",
    )
    op.create_check_constraint(
        "ck_admin_actions_target_required",
        "admin_actions",
        PREVIOUS_ADMIN_ACTION_TARGET_REQUIRED_CHECK,
    )
    for index_name in (
        "uq_admin_actions_restore_sub_chat_message_idempotency",
        "uq_admin_actions_remove_sub_chat_message_idempotency",
        "uq_admin_actions_mark_reviewed_sub_chat_message_idempotency",
    ):
        op.drop_index(
            index_name,
            table_name="admin_actions",
        )
    op.drop_index(
        "ix_admin_actions_target_sub_chat_message_id",
        table_name="admin_actions",
    )
    op.drop_column("admin_actions", "target_sub_chat_message_id")

    op.drop_index(
        "ix_sub_post_chat_message_detections_created_at",
        table_name="sub_post_chat_message_detections",
    )
    op.drop_index(
        "ix_sub_post_chat_message_detections_category",
        table_name="sub_post_chat_message_detections",
    )
    op.drop_index(
        "ix_sub_post_chat_message_detections_message_id",
        table_name="sub_post_chat_message_detections",
    )
    op.drop_table("sub_post_chat_message_detections")
    op.drop_constraint(
        "fk_sub_post_chats_latest_message_id",
        "sub_post_chats",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_sub_post_chat_messages_chat_id_visibility_status",
        table_name="sub_post_chat_messages",
    )
    op.drop_index(
        "ix_sub_post_chat_messages_chat_id_review_status",
        table_name="sub_post_chat_messages",
    )
    op.drop_index(
        "ix_sub_post_chat_messages_chat_id_created_at",
        table_name="sub_post_chat_messages",
    )
    op.drop_index(
        "ix_sub_post_chat_messages_review_status",
        table_name="sub_post_chat_messages",
    )
    op.drop_index(
        "ix_sub_post_chat_messages_visibility_status",
        table_name="sub_post_chat_messages",
    )
    op.drop_index(
        "ix_sub_post_chat_messages_restored_by_user_id",
        table_name="sub_post_chat_messages",
    )
    op.drop_index(
        "ix_sub_post_chat_messages_reviewed_by_user_id",
        table_name="sub_post_chat_messages",
    )
    op.drop_index(
        "ix_sub_post_chat_messages_removed_by_user_id",
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
