"""create admin_actions table"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_admin_actions"
down_revision = "0003_users"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("admin_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_type", sa.String(length=60), nullable=False),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("target_game_id", postgresql.UUID(as_uuid=True)),
        sa.Column("target_booking_id", postgresql.UUID(as_uuid=True)),
        sa.Column("target_participant_id", postgresql.UUID(as_uuid=True)),
        sa.Column("target_payment_id", postgresql.UUID(as_uuid=True)),
        sa.Column("target_refund_id", postgresql.UUID(as_uuid=True)),
        sa.Column("target_game_credit_id", postgresql.UUID(as_uuid=True)),
        sa.Column("target_credit_usage_id", postgresql.UUID(as_uuid=True)),
        sa.Column("target_venue_id", postgresql.UUID(as_uuid=True)),
        sa.Column("target_venue_image_id", postgresql.UUID(as_uuid=True)),
        sa.Column("target_message_id", postgresql.UUID(as_uuid=True)),
        sa.Column("target_sub_post_id", postgresql.UUID(as_uuid=True)),
        sa.Column("target_sub_post_request_id", postgresql.UUID(as_uuid=True)),
        sa.Column("target_sub_post_position_id", postgresql.UUID(as_uuid=True)),
        sa.Column("target_sub_chat_message_id", postgresql.UUID(as_uuid=True)),
        sa.Column("target_notification_id", postgresql.UUID(as_uuid=True)),
        sa.Column("target_platform_notice_id", postgresql.UUID(as_uuid=True)),
        sa.Column("target_admin_action_id", postgresql.UUID(as_uuid=True)),
        sa.Column("target_support_flag_id", postgresql.UUID(as_uuid=True)),
        sa.Column("target_money_issue_id", postgresql.UUID(as_uuid=True)),
        sa.Column("target_review_case_id", postgresql.UUID(as_uuid=True)),
        sa.Column("target_financial_outcome_id", postgresql.UUID(as_uuid=True)),
        sa.Column("target_host_publish_fee_id", postgresql.UUID(as_uuid=True)),
        sa.Column("target_host_publish_entitlement_id", postgresql.UUID(as_uuid=True)),
        sa.Column("reason", sa.Text()),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("idempotency_key", sa.String(length=160)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "action_type IN ('cancel_game', 'refund_booking', 'create_refund', 'update_refund', 'mark_no_show', 'create_payment', 'update_payment', 'reverse_no_show', 'suspend_user', 'unsuspend_user', 'restrict_hosting', 'restore_hosting', 'approve_venue', 'delete_user', 'reject_venue', 'create_venue_image', 'update_venue_image', 'remove_venue_image', 'mark_chat_message_reviewed', 'remove_chat_message', 'restore_chat_message', 'update_game', 'create_game_chat', 'update_game_chat', 'update_booking', 'update_participant', 'issue_credit', 'reverse_credit', 'create_financial_outcome', 'apply_financial_outcome', 'create_official_game', 'update_official_game', 'assign_official_host', 'remove_official_host', 'admin_add_player', 'admin_remove_player', 'waive_payment', 'remove_sub_post', 'hide_unsafe_community_payment_text', 'hide_need_sub_post', 'restore_need_sub_post', 'hide_community_game', 'restore_community_game', 'pause_community_game_joining', 'resume_community_game_joining', 'admin_cancel_community_game', 'restore_community_payment_text', 'create_notification', 'update_notification', 'publish_platform_notice', 'cancel_platform_notice', 'user_role_changed', 'append_audit_note', 'resolve_support_flag', 'resolve_money_issue', 'retry_money_issue_credit', 'reconcile_refund', 'create_review_case', 'close_review_case', 'add_review_case_note', 'assign_review_case', 'reopen_review_case', 'merge_review_case')",
            name="ck_admin_actions_action_type",
        ),
        sa.CheckConstraint(
            "target_user_id IS NOT NULL OR target_game_id IS NOT NULL OR target_booking_id IS NOT NULL OR target_participant_id IS NOT NULL OR target_payment_id IS NOT NULL OR target_refund_id IS NOT NULL OR target_game_credit_id IS NOT NULL OR target_credit_usage_id IS NOT NULL OR target_venue_id IS NOT NULL OR target_venue_image_id IS NOT NULL OR target_message_id IS NOT NULL OR target_sub_post_id IS NOT NULL OR target_sub_post_request_id IS NOT NULL OR target_sub_post_position_id IS NOT NULL OR target_sub_chat_message_id IS NOT NULL OR target_notification_id IS NOT NULL OR target_platform_notice_id IS NOT NULL OR target_admin_action_id IS NOT NULL OR target_support_flag_id IS NOT NULL OR target_money_issue_id IS NOT NULL OR target_review_case_id IS NOT NULL OR target_financial_outcome_id IS NOT NULL OR target_host_publish_fee_id IS NOT NULL OR target_host_publish_entitlement_id IS NOT NULL",
            name="ck_admin_actions_target_required",
        ),
        sa.ForeignKeyConstraint(["admin_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_admin_actions_action_type", "admin_actions", ["action_type"], unique=False
    )
    op.create_index(
        "ix_admin_actions_admin_user_id",
        "admin_actions",
        ["admin_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_idempotency_key",
        "admin_actions",
        ["idempotency_key"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_log_action_created_id",
        "admin_actions",
        ["action_type", sa.text("created_at DESC"), sa.text("id DESC")],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_log_admin_action_created_id",
        "admin_actions",
        [
            "admin_user_id",
            "action_type",
            sa.text("created_at DESC"),
            sa.text("id DESC"),
        ],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_log_admin_created_id",
        "admin_actions",
        ["admin_user_id", sa.text("created_at DESC"), sa.text("id DESC")],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_log_created_id",
        "admin_actions",
        [sa.text("created_at DESC"), sa.text("id DESC")],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_admin_action_id",
        "admin_actions",
        ["target_admin_action_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_booking_id",
        "admin_actions",
        ["target_booking_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_credit_usage_id",
        "admin_actions",
        ["target_credit_usage_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_financial_outcome_id",
        "admin_actions",
        ["target_financial_outcome_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_game_credit_id",
        "admin_actions",
        ["target_game_credit_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_game_id",
        "admin_actions",
        ["target_game_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_host_publish_entitlement_id",
        "admin_actions",
        ["target_host_publish_entitlement_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_host_publish_fee_id",
        "admin_actions",
        ["target_host_publish_fee_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_message_id",
        "admin_actions",
        ["target_message_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_money_issue_id",
        "admin_actions",
        ["target_money_issue_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_notification_id",
        "admin_actions",
        ["target_notification_id"],
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
        "ix_admin_actions_target_platform_notice_id",
        "admin_actions",
        ["target_platform_notice_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_refund_id",
        "admin_actions",
        ["target_refund_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_review_case_id",
        "admin_actions",
        ["target_review_case_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_sub_chat_message_id",
        "admin_actions",
        ["target_sub_chat_message_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_sub_post_id",
        "admin_actions",
        ["target_sub_post_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_sub_post_position_id",
        "admin_actions",
        ["target_sub_post_position_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_sub_post_request_id",
        "admin_actions",
        ["target_sub_post_request_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_support_flag_id",
        "admin_actions",
        ["target_support_flag_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_user_id",
        "admin_actions",
        ["target_user_id"],
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
        "uq_admin_actions_audit_note_idempotency",
        "admin_actions",
        ["admin_user_id", "target_admin_action_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "action_type = 'append_audit_note' AND idempotency_key IS NOT NULL"
        ),
    )
    op.create_index(
        "uq_admin_actions_community_game_enforcement_idempotency",
        "admin_actions",
        ["admin_user_id", "target_game_id", "action_type", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "action_type IN ('hide_community_game', 'restore_community_game', 'pause_community_game_joining', 'resume_community_game_joining', 'admin_cancel_community_game', 'restore_community_payment_text') AND idempotency_key IS NOT NULL"
        ),
    )
    op.create_index(
        "uq_admin_actions_create_financial_outcome_idempotency",
        "admin_actions",
        ["admin_user_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "action_type = 'create_financial_outcome' AND idempotency_key IS NOT NULL"
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
            "action_type = 'hide_unsafe_community_payment_text' AND idempotency_key IS NOT NULL"
        ),
    )
    op.create_index(
        "uq_admin_actions_mark_reviewed_chat_message_idempotency",
        "admin_actions",
        ["admin_user_id", "target_message_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "action_type = 'mark_chat_message_reviewed' AND target_message_id IS NOT NULL AND idempotency_key IS NOT NULL"
        ),
    )
    op.create_index(
        "uq_admin_actions_mark_reviewed_sub_chat_message_idempotency",
        "admin_actions",
        ["admin_user_id", "target_sub_chat_message_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "action_type = 'mark_chat_message_reviewed' AND target_sub_chat_message_id IS NOT NULL AND idempotency_key IS NOT NULL"
        ),
    )
    op.create_index(
        "uq_admin_actions_money_issue_idempotency",
        "admin_actions",
        ["admin_user_id", "target_money_issue_id", "action_type", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "action_type IN ('resolve_money_issue', 'retry_money_issue_credit') AND idempotency_key IS NOT NULL"
        ),
    )
    op.create_index(
        "uq_admin_actions_need_sub_enforcement_idempotency",
        "admin_actions",
        ["admin_user_id", "target_sub_post_id", "action_type", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "action_type IN ('hide_need_sub_post', 'restore_need_sub_post') AND idempotency_key IS NOT NULL"
        ),
    )
    op.create_index(
        "uq_admin_actions_reconcile_refund_idempotency",
        "admin_actions",
        ["admin_user_id", "target_refund_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "action_type = 'reconcile_refund' AND idempotency_key IS NOT NULL"
        ),
    )
    op.create_index(
        "uq_admin_actions_remove_chat_message_idempotency",
        "admin_actions",
        ["admin_user_id", "target_message_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "action_type = 'remove_chat_message' AND target_message_id IS NOT NULL AND idempotency_key IS NOT NULL"
        ),
    )
    op.create_index(
        "uq_admin_actions_remove_sub_chat_message_idempotency",
        "admin_actions",
        ["admin_user_id", "target_sub_chat_message_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "action_type = 'remove_chat_message' AND target_sub_chat_message_id IS NOT NULL AND idempotency_key IS NOT NULL"
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
        "uq_admin_actions_restore_chat_message_idempotency",
        "admin_actions",
        ["admin_user_id", "target_message_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "action_type = 'restore_chat_message' AND target_message_id IS NOT NULL AND idempotency_key IS NOT NULL"
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
        "uq_admin_actions_restore_sub_chat_message_idempotency",
        "admin_actions",
        ["admin_user_id", "target_sub_chat_message_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "action_type = 'restore_chat_message' AND target_sub_chat_message_id IS NOT NULL AND idempotency_key IS NOT NULL"
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
        "uq_admin_actions_review_case_idempotency",
        "admin_actions",
        ["admin_user_id", "target_review_case_id", "action_type", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "action_type IN ('create_review_case', 'close_review_case', 'add_review_case_note', 'assign_review_case', 'reopen_review_case', 'merge_review_case') AND idempotency_key IS NOT NULL"
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
        "uq_admin_actions_update_refund_idempotency",
        "admin_actions",
        ["admin_user_id", "target_refund_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "action_type = 'update_refund' AND idempotency_key IS NOT NULL"
        ),
    )
    op.create_index(
        "uq_admin_actions_user_role_changed_idempotency",
        "admin_actions",
        ["admin_user_id", "target_user_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "action_type = 'user_role_changed' AND idempotency_key IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.drop_table("admin_actions")
