"""create platform notice campaigns table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0045_platform_notice_campaigns"
down_revision = "0044_admin_rejected_attempts"
branch_labels = None
depends_on = None


ADMIN_ACTION_TYPE_CHECK = (
    "action_type IN ("
    "'cancel_game', 'refund_booking', 'create_refund', "
    "'update_refund', 'mark_no_show', "
    "'create_payment', 'update_payment', "
    "'reverse_no_show', 'suspend_user', 'unsuspend_user', "
    "'restrict_hosting', 'restore_hosting', 'approve_venue', "
    "'delete_user', "
    "'reject_venue', 'create_venue_image', 'update_venue_image', "
    "'remove_venue_image', 'mark_chat_message_reviewed', "
    "'remove_chat_message', 'restore_chat_message', "
    "'update_game', 'create_game_chat', 'update_game_chat', "
    "'update_booking', "
    "'update_participant', 'issue_credit', 'reverse_credit', "
    "'create_financial_outcome', 'apply_financial_outcome', "
    "'create_official_game', 'update_official_game', "
    "'assign_official_host', 'remove_official_host', "
    "'admin_add_player', 'admin_remove_player', 'waive_payment', "
    "'remove_sub_post', 'hide_unsafe_community_payment_text', "
    "'hide_need_sub_post', 'restore_need_sub_post', "
    "'hide_community_game', 'restore_community_game', "
    "'pause_community_game_joining', "
    "'resume_community_game_joining', "
    "'admin_cancel_community_game', "
    "'restore_community_payment_text', "
    "'create_notification', 'update_notification', "
    "'create_platform_notice_campaign', "
    "'update_platform_notice_campaign', "
    "'send_platform_notice_campaign', "
    "'retry_platform_notice_campaign', "
    "'change_staff_role', 'append_audit_note', "
    "'resolve_support_flag'"
    ")"
)

PREVIOUS_ADMIN_ACTION_TYPE_CHECK = (
    "action_type IN ("
    "'cancel_game', 'refund_booking', 'create_refund', "
    "'update_refund', 'mark_no_show', "
    "'create_payment', 'update_payment', "
    "'reverse_no_show', 'suspend_user', 'unsuspend_user', "
    "'restrict_hosting', 'restore_hosting', 'approve_venue', "
    "'delete_user', "
    "'reject_venue', 'create_venue_image', 'update_venue_image', "
    "'remove_venue_image', 'mark_chat_message_reviewed', "
    "'remove_chat_message', 'restore_chat_message', "
    "'update_game', 'create_game_chat', 'update_game_chat', "
    "'update_booking', "
    "'update_participant', 'issue_credit', 'reverse_credit', "
    "'create_financial_outcome', 'apply_financial_outcome', "
    "'create_official_game', 'update_official_game', "
    "'assign_official_host', 'remove_official_host', "
    "'admin_add_player', 'admin_remove_player', 'waive_payment', "
    "'remove_sub_post', 'hide_unsafe_community_payment_text', "
    "'hide_need_sub_post', 'restore_need_sub_post', "
    "'hide_community_game', 'restore_community_game', "
    "'pause_community_game_joining', "
    "'resume_community_game_joining', "
    "'admin_cancel_community_game', "
    "'restore_community_payment_text', "
    "'create_notification', 'update_notification', "
    "'change_staff_role', 'append_audit_note', "
    "'resolve_support_flag'"
    ")"
)

ADMIN_ACTION_TARGET_REQUIRED_CHECK = (
    "target_user_id IS NOT NULL "
    "OR target_game_id IS NOT NULL "
    "OR target_booking_id IS NOT NULL "
    "OR target_participant_id IS NOT NULL "
    "OR target_payment_id IS NOT NULL "
    "OR target_refund_id IS NOT NULL "
    "OR target_game_credit_id IS NOT NULL "
    "OR target_financial_outcome_id IS NOT NULL "
    "OR target_host_publish_fee_id IS NOT NULL "
    "OR target_host_publish_entitlement_id IS NOT NULL "
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
)

PREVIOUS_ADMIN_ACTION_TARGET_REQUIRED_CHECK = (
    "target_user_id IS NOT NULL "
    "OR target_game_id IS NOT NULL "
    "OR target_booking_id IS NOT NULL "
    "OR target_participant_id IS NOT NULL "
    "OR target_payment_id IS NOT NULL "
    "OR target_refund_id IS NOT NULL "
    "OR target_game_credit_id IS NOT NULL "
    "OR target_financial_outcome_id IS NOT NULL "
    "OR target_host_publish_fee_id IS NOT NULL "
    "OR target_host_publish_entitlement_id IS NOT NULL "
    "OR target_venue_id IS NOT NULL "
    "OR target_venue_image_id IS NOT NULL "
    "OR target_message_id IS NOT NULL "
    "OR target_sub_post_id IS NOT NULL "
    "OR target_sub_post_request_id IS NOT NULL "
    "OR target_sub_post_position_id IS NOT NULL "
    "OR target_sub_chat_message_id IS NOT NULL "
    "OR target_notification_id IS NOT NULL "
    "OR target_admin_action_id IS NOT NULL "
    "OR target_support_flag_id IS NOT NULL"
)


def upgrade() -> None:
    op.create_table(
        "platform_notice_campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "campaign_status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'draft'"),
        ),
        sa.Column("audience_type", sa.String(length=30), nullable=False),
        sa.Column("delivery_class", sa.String(length=30), nullable=False),
        sa.Column("internal_name", sa.String(length=160), nullable=False),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("creation_idempotency_key", sa.String(length=160), nullable=False),
        sa.Column(
            "creation_request_fingerprint",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "first_sent_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "last_attempt_at",
            sa.DateTime(timezone=True),
            nullable=True,
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
        sa.CheckConstraint(
            (
                "campaign_status IN ("
                "'draft', 'sending', 'completed', "
                "'completed_with_failures', 'failed', 'cancelled'"
                ")"
            ),
            name="ck_platform_notice_campaigns_status",
        ),
        sa.CheckConstraint(
            "audience_type IN ('all_active_users', 'selected_users')",
            name="ck_platform_notice_campaigns_audience_type",
        ),
        sa.CheckConstraint(
            "delivery_class IN ('mandatory', 'preference_controlled')",
            name="ck_platform_notice_campaigns_delivery_class",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "created_by_user_id",
            "creation_idempotency_key",
            name="uq_platform_notice_campaigns_creator_idempotency",
        ),
    )
    op.create_index(
        "ix_platform_notice_campaigns_status",
        "platform_notice_campaigns",
        ["campaign_status"],
    )
    op.create_index(
        "ix_platform_notice_campaigns_audience_type",
        "platform_notice_campaigns",
        ["audience_type"],
    )
    op.create_index(
        "ix_platform_notice_campaigns_delivery_class",
        "platform_notice_campaigns",
        ["delivery_class"],
    )
    op.create_index(
        "ix_platform_notice_campaigns_created_by_user_id",
        "platform_notice_campaigns",
        ["created_by_user_id"],
    )
    op.create_index(
        "ix_platform_notice_campaigns_created_at",
        "platform_notice_campaigns",
        ["created_at"],
    )
    op.create_index(
        "ix_platform_notice_campaigns_first_sent_at",
        "platform_notice_campaigns",
        ["first_sent_at"],
    )

    op.create_table(
        "platform_notice_campaign_target_users",
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["platform_notice_campaigns.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("campaign_id", "user_id"),
    )
    op.create_index(
        "ix_platform_notice_campaign_target_users_user_id",
        "platform_notice_campaign_target_users",
        ["user_id"],
    )

    op.create_table(
        "platform_notice_campaign_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attempt_type", sa.String(length=30), nullable=False),
        sa.Column("attempt_status", sa.String(length=40), nullable=False),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column(
            "targeted_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "delivered_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "skipped_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "failed_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "attempt_type IN ('initial_send', 'retry_failed')",
            name="ck_platform_notice_campaign_attempts_type",
        ),
        sa.CheckConstraint(
            (
                "attempt_status IN ("
                "'in_progress', 'completed', 'completed_with_failures', 'failed'"
                ")"
            ),
            name="ck_platform_notice_campaign_attempts_status",
        ),
        sa.CheckConstraint(
            (
                "targeted_count >= 0 AND delivered_count >= 0 "
                "AND skipped_count >= 0 AND failed_count >= 0"
            ),
            name="ck_platform_notice_campaign_attempts_counts_nonnegative",
        ),
        sa.CheckConstraint(
            (
                "attempt_status = 'in_progress' OR "
                "targeted_count = delivered_count + skipped_count + failed_count"
            ),
            name="ck_platform_notice_campaign_attempts_counts_match",
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["platform_notice_campaigns.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "campaign_id",
            "idempotency_key",
            name="uq_platform_notice_campaign_attempts_idempotency",
        ),
    )
    op.create_index(
        "ix_platform_notice_campaign_attempts_campaign_id",
        "platform_notice_campaign_attempts",
        ["campaign_id"],
    )
    op.create_index(
        "ix_platform_notice_campaign_attempts_created_at",
        "platform_notice_campaign_attempts",
        ["created_at"],
    )

    op.create_table(
        "platform_notice_campaign_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "recipient_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "recipient_user_id_snapshot",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "delivery_status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("skip_reason", sa.String(length=60), nullable=True),
        sa.Column("failure_code", sa.String(length=80), nullable=True),
        sa.Column(
            "notification_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "attempt_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "last_attempt_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "delivered_at",
            sa.DateTime(timezone=True),
            nullable=True,
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
        sa.CheckConstraint(
            "delivery_status IN ('pending', 'delivered', 'skipped', 'failed')",
            name="ck_platform_notice_campaign_deliveries_status",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name="ck_platform_notice_campaign_deliveries_attempt_count",
        ),
        sa.CheckConstraint(
            (
                "(delivery_status = 'delivered' "
                "AND delivered_at IS NOT NULL "
                "AND skip_reason IS NULL "
                "AND failure_code IS NULL) "
                "OR (delivery_status = 'skipped' "
                "AND notification_id IS NULL "
                "AND delivered_at IS NULL "
                "AND skip_reason IS NOT NULL "
                "AND failure_code IS NULL) "
                "OR (delivery_status = 'failed' "
                "AND notification_id IS NULL "
                "AND delivered_at IS NULL "
                "AND skip_reason IS NULL "
                "AND failure_code IS NOT NULL) "
                "OR (delivery_status = 'pending' "
                "AND notification_id IS NULL "
                "AND delivered_at IS NULL "
                "AND skip_reason IS NULL "
                "AND failure_code IS NULL)"
            ),
            name="ck_platform_notice_campaign_deliveries_state",
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["platform_notice_campaigns.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recipient_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["notification_id"],
            ["notifications.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "campaign_id",
            "recipient_user_id_snapshot",
            name="uq_platform_notice_campaign_deliveries_recipient",
        ),
    )
    op.create_index(
        "ix_platform_notice_campaign_deliveries_campaign_id",
        "platform_notice_campaign_deliveries",
        ["campaign_id"],
    )
    op.create_index(
        "ix_platform_notice_campaign_deliveries_recipient_user_id",
        "platform_notice_campaign_deliveries",
        ["recipient_user_id"],
    )
    op.create_index(
        "ix_platform_notice_campaign_deliveries_status",
        "platform_notice_campaign_deliveries",
        ["delivery_status"],
    )
    op.create_index(
        "ix_platform_notice_campaign_deliveries_notification_id",
        "platform_notice_campaign_deliveries",
        ["notification_id"],
    )

    op.create_table(
        "admin_target_notices",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipient_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_game_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_sub_post_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "target_sub_post_request_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("admin_action_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notice_type", sa.String(length=60), nullable=False),
        sa.Column(
            "notice_status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("user_safe_reason", sa.Text(), nullable=True),
        sa.Column("notice_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            (
                "notice_type IN ("
                "'community_game_hidden', 'community_game_restored', "
                "'community_game_joining_paused', "
                "'community_game_joining_resumed', "
                "'community_game_payment_info_hidden', "
                "'community_game_payment_info_restored', "
                "'community_game_cancelled', 'need_sub_post_hidden', "
                "'need_sub_post_restored', 'need_sub_post_removed', "
                "'publish_fee_refunded', 'publish_credit_added'"
                ")"
            ),
            name="ck_admin_target_notices_notice_type",
        ),
        sa.CheckConstraint(
            "notice_status IN ('active', 'dismissed')",
            name="ck_admin_target_notices_notice_status",
        ),
        sa.CheckConstraint(
            (
                "target_game_id IS NOT NULL "
                "OR target_sub_post_id IS NOT NULL "
                "OR target_sub_post_request_id IS NOT NULL "
                "OR target_user_id IS NOT NULL"
            ),
            name="ck_admin_target_notices_target_required",
        ),
        sa.ForeignKeyConstraint(
            ["recipient_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_game_id"],
            ["games.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_sub_post_id"],
            ["sub_posts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_sub_post_request_id"],
            ["sub_post_requests.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["admin_action_id"],
            ["admin_actions.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_admin_target_notices_recipient_user_id",
        "admin_target_notices",
        ["recipient_user_id"],
    )
    op.create_index(
        "ix_admin_target_notices_target_user_id",
        "admin_target_notices",
        ["target_user_id"],
    )
    op.create_index(
        "ix_admin_target_notices_target_game_id",
        "admin_target_notices",
        ["target_game_id"],
    )
    op.create_index(
        "ix_admin_target_notices_target_sub_post_id",
        "admin_target_notices",
        ["target_sub_post_id"],
    )
    op.create_index(
        "ix_admin_target_notices_target_sub_post_request_id",
        "admin_target_notices",
        ["target_sub_post_request_id"],
    )
    op.create_index(
        "ix_admin_target_notices_admin_action_id",
        "admin_target_notices",
        ["admin_action_id"],
    )
    op.create_index(
        "ix_admin_target_notices_notice_type",
        "admin_target_notices",
        ["notice_type"],
    )
    op.create_index(
        "ix_admin_target_notices_created_at",
        "admin_target_notices",
        ["created_at"],
    )

    op.add_column(
        "admin_actions",
        sa.Column(
            "target_platform_notice_campaign_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_admin_actions_target_platform_notice_campaign_id",
        "admin_actions",
        ["target_platform_notice_campaign_id"],
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
        "fk_admin_actions_target_platform_notice_campaign_id",
        "admin_actions",
        "platform_notice_campaigns",
        ["target_platform_notice_campaign_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_constraint(
        "ck_admin_actions_action_type",
        "admin_actions",
        type_="check",
    )
    op.create_check_constraint(
        "ck_admin_actions_action_type",
        "admin_actions",
        ADMIN_ACTION_TYPE_CHECK,
    )
    op.create_index(
        "uq_admin_actions_community_game_enforcement_idempotency",
        "admin_actions",
        ["admin_user_id", "target_game_id", "action_type", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "action_type IN ("
            "'hide_community_game', 'restore_community_game', "
            "'pause_community_game_joining', "
            "'resume_community_game_joining', "
            "'admin_cancel_community_game', "
            "'restore_community_payment_text'"
            ") AND idempotency_key IS NOT NULL"
        ),
    )
    op.create_index(
        "uq_admin_actions_need_sub_enforcement_idempotency",
        "admin_actions",
        ["admin_user_id", "target_sub_post_id", "action_type", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "action_type IN ('hide_need_sub_post', 'restore_need_sub_post') "
            "AND idempotency_key IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_admin_actions_need_sub_enforcement_idempotency",
        table_name="admin_actions",
    )
    op.drop_index(
        "uq_admin_actions_community_game_enforcement_idempotency",
        table_name="admin_actions",
    )
    op.execute(
        "DELETE FROM admin_actions "
        "WHERE action_type IN ("
        "'create_platform_notice_campaign', "
        "'update_platform_notice_campaign', "
        "'send_platform_notice_campaign', "
        "'retry_platform_notice_campaign'"
        ") OR target_platform_notice_campaign_id IS NOT NULL"
    )
    op.drop_constraint(
        "ck_admin_actions_action_type",
        "admin_actions",
        type_="check",
    )
    op.create_check_constraint(
        "ck_admin_actions_action_type",
        "admin_actions",
        PREVIOUS_ADMIN_ACTION_TYPE_CHECK,
    )
    op.drop_constraint(
        "fk_admin_actions_target_platform_notice_campaign_id",
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
    op.drop_index(
        "ix_admin_actions_target_platform_notice_campaign_id",
        table_name="admin_actions",
    )
    op.drop_column("admin_actions", "target_platform_notice_campaign_id")
    op.drop_index(
        "ix_admin_target_notices_created_at",
        table_name="admin_target_notices",
    )
    op.drop_index(
        "ix_admin_target_notices_notice_type",
        table_name="admin_target_notices",
    )
    op.drop_index(
        "ix_admin_target_notices_admin_action_id",
        table_name="admin_target_notices",
    )
    op.drop_index(
        "ix_admin_target_notices_target_sub_post_request_id",
        table_name="admin_target_notices",
    )
    op.drop_index(
        "ix_admin_target_notices_target_sub_post_id",
        table_name="admin_target_notices",
    )
    op.drop_index(
        "ix_admin_target_notices_target_game_id",
        table_name="admin_target_notices",
    )
    op.drop_index(
        "ix_admin_target_notices_target_user_id",
        table_name="admin_target_notices",
    )
    op.drop_index(
        "ix_admin_target_notices_recipient_user_id",
        table_name="admin_target_notices",
    )
    op.drop_table("admin_target_notices")
    op.drop_index(
        "ix_platform_notice_campaign_deliveries_notification_id",
        table_name="platform_notice_campaign_deliveries",
    )
    op.drop_index(
        "ix_platform_notice_campaign_deliveries_status",
        table_name="platform_notice_campaign_deliveries",
    )
    op.drop_index(
        "ix_platform_notice_campaign_deliveries_recipient_user_id",
        table_name="platform_notice_campaign_deliveries",
    )
    op.drop_index(
        "ix_platform_notice_campaign_deliveries_campaign_id",
        table_name="platform_notice_campaign_deliveries",
    )
    op.drop_table("platform_notice_campaign_deliveries")
    op.drop_index(
        "ix_platform_notice_campaign_attempts_created_at",
        table_name="platform_notice_campaign_attempts",
    )
    op.drop_index(
        "ix_platform_notice_campaign_attempts_campaign_id",
        table_name="platform_notice_campaign_attempts",
    )
    op.drop_table("platform_notice_campaign_attempts")
    op.drop_index(
        "ix_platform_notice_campaign_target_users_user_id",
        table_name="platform_notice_campaign_target_users",
    )
    op.drop_table("platform_notice_campaign_target_users")
    op.drop_index(
        "ix_platform_notice_campaigns_first_sent_at",
        table_name="platform_notice_campaigns",
    )
    op.drop_index(
        "ix_platform_notice_campaigns_created_at",
        table_name="platform_notice_campaigns",
    )
    op.drop_index(
        "ix_platform_notice_campaigns_created_by_user_id",
        table_name="platform_notice_campaigns",
    )
    op.drop_index(
        "ix_platform_notice_campaigns_delivery_class",
        table_name="platform_notice_campaigns",
    )
    op.drop_index(
        "ix_platform_notice_campaigns_audience_type",
        table_name="platform_notice_campaigns",
    )
    op.drop_index(
        "ix_platform_notice_campaigns_status",
        table_name="platform_notice_campaigns",
    )
    op.drop_table("platform_notice_campaigns")
