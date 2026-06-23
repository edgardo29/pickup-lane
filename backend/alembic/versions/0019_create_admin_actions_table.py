"""create admin actions table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0019_admin_actions"
down_revision = "0018_user_stats"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nineteenth schema migration: create admin_actions as an audit trail for
    # important admin/support actions across users, games, payments, and chats.
    op.create_table(
        "admin_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("admin_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_type", sa.String(length=60), nullable=False),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_game_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_booking_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "target_participant_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("target_payment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_refund_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_game_credit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_venue_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_venue_image_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_sub_post_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "target_sub_post_request_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "target_sub_post_position_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "target_sub_chat_message_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("target_notification_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "target_platform_notice_campaign_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("target_admin_action_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_support_flag_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=160), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            (
                "action_type IN ("
                "'cancel_game', 'refund_booking', 'create_refund', "
                "'update_refund', 'mark_no_show', "
                "'create_payment', 'update_payment', "
                "'reverse_no_show', 'suspend_user', 'unsuspend_user', "
                "'restrict_hosting', 'restore_hosting', 'approve_venue', "
                "'delete_user', "
                "'reject_venue', 'create_venue_image', 'update_venue_image', "
                "'remove_venue_image', 'remove_chat_message', 'hide_chat_message', "
                "'update_game', 'create_game_chat', 'update_game_chat', "
                "'update_booking', "
                "'update_participant', 'issue_credit', 'reverse_credit', "
                "'create_official_game', 'update_official_game', "
                "'assign_official_host', 'remove_official_host', "
                "'admin_add_player', 'admin_remove_player', 'waive_payment', "
                "'remove_sub_post', 'hide_unsafe_community_payment_text', "
                "'create_notification', 'update_notification', "
                "'create_platform_notice_campaign', "
                "'update_platform_notice_campaign', "
                "'send_platform_notice_campaign', "
                "'retry_platform_notice_campaign', "
                "'change_staff_role', 'append_audit_note', "
                "'resolve_support_flag'"
                ")"
            ),
            name="ck_admin_actions_action_type",
        ),
        sa.CheckConstraint(
            (
                "target_user_id IS NOT NULL "
                "OR target_game_id IS NOT NULL "
                "OR target_booking_id IS NOT NULL "
                "OR target_participant_id IS NOT NULL "
                "OR target_payment_id IS NOT NULL "
                "OR target_refund_id IS NOT NULL "
                "OR target_game_credit_id IS NOT NULL "
                "OR target_venue_id IS NOT NULL "
                "OR target_venue_image_id IS NOT NULL "
                "OR target_message_id IS NOT NULL "
                "OR target_sub_post_id IS NOT NULL "
                "OR target_sub_post_request_id IS NOT NULL "
                "OR target_sub_post_position_id IS NOT NULL "
                "OR target_sub_chat_message_id IS NOT NULL "
                "OR target_notification_id IS NOT NULL "
                "OR target_platform_notice_campaign_id IS NOT NULL "
                "OR target_admin_action_id IS NOT NULL "
                "OR target_support_flag_id IS NOT NULL"
            ),
            name="ck_admin_actions_target_required",
        ),
        sa.ForeignKeyConstraint(
            ["admin_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_game_id"],
            ["games.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_booking_id"],
            ["bookings.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_participant_id"],
            ["game_participants.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_payment_id"],
            ["payments.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_refund_id"],
            ["refunds.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_venue_id"],
            ["venues.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_message_id"],
            ["chat_messages.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_notification_id"],
            ["notifications.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_admin_action_id"],
            ["admin_actions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_admin_actions_admin_user_id",
        "admin_actions",
        ["admin_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_action_type",
        "admin_actions",
        ["action_type"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_created_at",
        "admin_actions",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_user_id",
        "admin_actions",
        ["target_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_game_id",
        "admin_actions",
        ["target_game_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_booking_id",
        "admin_actions",
        ["target_booking_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_participant_id",
        "admin_actions",
        ["target_participant_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_payment_id",
        "admin_actions",
        ["target_payment_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_refund_id",
        "admin_actions",
        ["target_refund_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_game_credit_id",
        "admin_actions",
        ["target_game_credit_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_venue_id",
        "admin_actions",
        ["target_venue_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_venue_image_id",
        "admin_actions",
        ["target_venue_image_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_message_id",
        "admin_actions",
        ["target_message_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_sub_post_id",
        "admin_actions",
        ["target_sub_post_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_sub_post_request_id",
        "admin_actions",
        ["target_sub_post_request_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_sub_post_position_id",
        "admin_actions",
        ["target_sub_post_position_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_sub_chat_message_id",
        "admin_actions",
        ["target_sub_chat_message_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_notification_id",
        "admin_actions",
        ["target_notification_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_platform_notice_campaign_id",
        "admin_actions",
        ["target_platform_notice_campaign_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_admin_action_id",
        "admin_actions",
        ["target_admin_action_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_support_flag_id",
        "admin_actions",
        ["target_support_flag_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_idempotency_key",
        "admin_actions",
        ["idempotency_key"],
        unique=False,
    )
    op.create_index(
        "uq_admin_actions_audit_note_idempotency",
        "admin_actions",
        ["admin_user_id", "target_admin_action_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "action_type = 'append_audit_note' AND idempotency_key IS NOT NULL"
        ),
    )
    op.create_index(
        "uq_admin_actions_suspend_user_idempotency",
        "admin_actions",
        ["admin_user_id", "target_user_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "action_type = 'suspend_user' AND idempotency_key IS NOT NULL"
        ),
    )
    op.create_index(
        "uq_admin_actions_unsuspend_user_idempotency",
        "admin_actions",
        ["admin_user_id", "target_user_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "action_type = 'unsuspend_user' AND idempotency_key IS NOT NULL"
        ),
    )
    op.create_index(
        "uq_admin_actions_restrict_hosting_idempotency",
        "admin_actions",
        ["admin_user_id", "target_user_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "action_type = 'restrict_hosting' AND idempotency_key IS NOT NULL"
        ),
    )
    op.create_index(
        "uq_admin_actions_restore_hosting_idempotency",
        "admin_actions",
        ["admin_user_id", "target_user_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "action_type = 'restore_hosting' AND idempotency_key IS NOT NULL"
        ),
    )
    op.create_index(
        "uq_admin_actions_change_staff_role_idempotency",
        "admin_actions",
        ["admin_user_id", "target_user_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "action_type = 'change_staff_role' AND idempotency_key IS NOT NULL"
        ),
    )
    op.create_index(
        "uq_admin_actions_delete_user_idempotency",
        "admin_actions",
        ["admin_user_id", "target_user_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "action_type = 'delete_user' AND idempotency_key IS NOT NULL"
        ),
    )
    op.create_index(
        "uq_admin_actions_hide_unsafe_community_payment_text_idempotency",
        "admin_actions",
        ["admin_user_id", "target_game_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "action_type = 'hide_unsafe_community_payment_text' "
            "AND idempotency_key IS NOT NULL"
        ),
    )
    op.create_index(
        "uq_admin_actions_remove_sub_post_idempotency",
        "admin_actions",
        ["admin_user_id", "target_sub_post_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "action_type = 'remove_sub_post' AND idempotency_key IS NOT NULL"
        ),
    )
    op.create_index(
        "uq_admin_actions_hide_sub_chat_message_idempotency",
        "admin_actions",
        ["admin_user_id", "target_sub_chat_message_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "action_type = 'hide_chat_message' "
            "AND target_sub_chat_message_id IS NOT NULL "
            "AND idempotency_key IS NOT NULL"
        ),
    )
    op.create_index(
        "uq_admin_actions_remove_sub_chat_message_idempotency",
        "admin_actions",
        ["admin_user_id", "target_sub_chat_message_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "action_type = 'remove_chat_message' "
            "AND target_sub_chat_message_id IS NOT NULL "
            "AND idempotency_key IS NOT NULL"
        ),
    )
    op.create_index(
        "ix_admin_actions_admin_user_id_created_at",
        "admin_actions",
        ["admin_user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_action_type_created_at",
        "admin_actions",
        ["action_type", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    # Downgrade removes the admin_actions table and indexes because this
    # migration only introduces that single audit table.
    op.drop_index(
        "ix_admin_actions_action_type_created_at",
        table_name="admin_actions",
    )
    op.drop_index(
        "ix_admin_actions_admin_user_id_created_at",
        table_name="admin_actions",
    )
    op.drop_index(
        "uq_admin_actions_remove_sub_chat_message_idempotency",
        table_name="admin_actions",
        if_exists=True,
    )
    op.drop_index(
        "uq_admin_actions_hide_sub_chat_message_idempotency",
        table_name="admin_actions",
        if_exists=True,
    )
    op.drop_index(
        "uq_admin_actions_remove_sub_post_idempotency",
        table_name="admin_actions",
        if_exists=True,
    )
    op.drop_index(
        "uq_admin_actions_delete_user_idempotency",
        table_name="admin_actions",
        if_exists=True,
    )
    op.drop_index(
        "uq_admin_actions_hide_unsafe_community_payment_text_idempotency",
        table_name="admin_actions",
        if_exists=True,
    )
    op.drop_index(
        "uq_admin_actions_change_staff_role_idempotency",
        table_name="admin_actions",
        if_exists=True,
    )
    op.drop_index(
        "uq_admin_actions_restore_hosting_idempotency",
        table_name="admin_actions",
        if_exists=True,
    )
    op.drop_index(
        "uq_admin_actions_restrict_hosting_idempotency",
        table_name="admin_actions",
        if_exists=True,
    )
    op.drop_index(
        "uq_admin_actions_unsuspend_user_idempotency",
        table_name="admin_actions",
        if_exists=True,
    )
    op.drop_index(
        "uq_admin_actions_suspend_user_idempotency",
        table_name="admin_actions",
        if_exists=True,
    )
    op.drop_index(
        "uq_admin_actions_audit_note_idempotency",
        table_name="admin_actions",
        if_exists=True,
    )
    op.drop_index(
        "ix_admin_actions_idempotency_key",
        table_name="admin_actions",
        if_exists=True,
    )
    op.drop_index(
        "ix_admin_actions_target_support_flag_id",
        table_name="admin_actions",
        if_exists=True,
    )
    op.drop_index(
        "ix_admin_actions_target_admin_action_id",
        table_name="admin_actions",
        if_exists=True,
    )
    op.drop_index(
        "ix_admin_actions_target_platform_notice_campaign_id",
        table_name="admin_actions",
        if_exists=True,
    )
    op.drop_index(
        "ix_admin_actions_target_notification_id",
        table_name="admin_actions",
        if_exists=True,
    )
    op.drop_index(
        "ix_admin_actions_target_sub_chat_message_id",
        table_name="admin_actions",
        if_exists=True,
    )
    op.drop_index(
        "ix_admin_actions_target_sub_post_position_id",
        table_name="admin_actions",
        if_exists=True,
    )
    op.drop_index(
        "ix_admin_actions_target_sub_post_request_id",
        table_name="admin_actions",
        if_exists=True,
    )
    op.drop_index(
        "ix_admin_actions_target_sub_post_id",
        table_name="admin_actions",
        if_exists=True,
    )
    op.drop_index("ix_admin_actions_target_message_id", table_name="admin_actions")
    op.drop_index(
        "ix_admin_actions_target_venue_image_id",
        table_name="admin_actions",
        if_exists=True,
    )
    op.drop_index("ix_admin_actions_target_venue_id", table_name="admin_actions")
    op.drop_index(
        "ix_admin_actions_target_game_credit_id",
        table_name="admin_actions",
        if_exists=True,
    )
    op.drop_index(
        "ix_admin_actions_target_refund_id",
        table_name="admin_actions",
        if_exists=True,
    )
    op.drop_index("ix_admin_actions_target_payment_id", table_name="admin_actions")
    op.drop_index(
        "ix_admin_actions_target_participant_id",
        table_name="admin_actions",
    )
    op.drop_index("ix_admin_actions_target_booking_id", table_name="admin_actions")
    op.drop_index("ix_admin_actions_target_game_id", table_name="admin_actions")
    op.drop_index("ix_admin_actions_target_user_id", table_name="admin_actions")
    op.drop_index("ix_admin_actions_created_at", table_name="admin_actions")
    op.drop_index("ix_admin_actions_action_type", table_name="admin_actions")
    op.drop_index("ix_admin_actions_admin_user_id", table_name="admin_actions")
    op.drop_table("admin_actions")
