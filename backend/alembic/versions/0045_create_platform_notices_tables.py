"""create platform notices tables"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0045_platform_notices"
down_revision = "0044_admin_rejected_attempts"
branch_labels = None
depends_on = None


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
    "'user_role_changed', 'append_audit_note', "
    "'resolve_support_flag'"
    ")"
)

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
    "'publish_platform_notice', 'cancel_platform_notice', "
    "'user_role_changed', 'append_audit_note', "
    "'resolve_support_flag'"
    ")"
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

ADMIN_ACTION_TARGET_REQUIRED_CHECK = (
    PREVIOUS_ADMIN_ACTION_TARGET_REQUIRED_CHECK
    + " OR target_platform_notice_id IS NOT NULL"
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_index(
        "ix_users_platform_notice_active_id",
        "users",
        ["id"],
        postgresql_where=sa.text("account_status = 'active' AND deleted_at IS NULL"),
    )

    op.execute("CREATE SEQUENCE platform_notice_global_sequence_seq")
    op.create_table(
        "platform_notices",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("audience_type", sa.String(length=30), nullable=False),
        sa.Column("global_sequence", sa.BigInteger(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_admin_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("idempotency_key_hash", sa.String(length=64), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by_admin_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
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
            "audience_type IN ('all_eligible_users', 'selected_users')",
            name="ck_platform_notices_audience_type",
        ),
        sa.CheckConstraint(
            (
                "(audience_type = 'all_eligible_users' AND global_sequence IS NOT NULL) "
                "OR (audience_type = 'selected_users' AND global_sequence IS NULL)"
            ),
            name="ck_platform_notices_global_sequence_scope",
        ),
        sa.CheckConstraint(
            "char_length(btrim(title)) > 0",
            name="ck_platform_notices_title_not_empty",
        ),
        sa.CheckConstraint(
            "char_length(btrim(message)) > 0",
            name="ck_platform_notices_message_not_empty",
        ),
        sa.CheckConstraint(
            (
                "(cancelled_at IS NULL AND cancelled_by_admin_id IS NULL "
                "AND cancellation_reason IS NULL) "
                "OR (cancelled_at IS NOT NULL AND cancelled_by_admin_id IS NOT NULL "
                "AND cancellation_reason IS NOT NULL)"
            ),
            name="ck_platform_notices_cancellation_integrity",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_admin_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["cancelled_by_admin_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_platform_notices_admin_idempotency_key",
        "platform_notices",
        ["created_by_admin_id", "idempotency_key_hash"],
        unique=True,
    )
    op.create_index(
        "uq_platform_notices_global_sequence",
        "platform_notices",
        ["global_sequence"],
        unique=True,
        postgresql_where=sa.text("global_sequence IS NOT NULL"),
    )
    op.create_index(
        "ix_platform_notices_audience_cancelled_published_id",
        "platform_notices",
        ["audience_type", "cancelled_at", "published_at", "id"],
    )
    op.create_index(
        "ix_platform_notices_created_by_admin_id",
        "platform_notices",
        ["created_by_admin_id"],
    )
    op.execute(
        """
        CREATE INDEX ix_platform_notices_history_order
        ON platform_notices (published_at DESC, id DESC)
        """
    )
    op.create_index(
        "ix_platform_notices_cancelled_at",
        "platform_notices",
        ["cancelled_at"],
    )
    op.execute(
        """
        CREATE INDEX ix_platform_notices_history_search_trgm
        ON platform_notices
        USING gin ((coalesce(title, '') || ' ' || coalesce(message, '')) gin_trgm_ops)
        """
    )

    op.create_table(
        "platform_notice_recipients",
        sa.Column("notice_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["notice_id"],
            ["platform_notices.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("notice_id", "user_id"),
    )
    op.create_index(
        "ix_platform_notice_recipients_user_notice",
        "platform_notice_recipients",
        ["user_id", "notice_id"],
    )

    op.create_table(
        "platform_notice_selected_reads",
        sa.Column("notice_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["notice_id"],
            ["platform_notices.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("notice_id", "user_id"),
    )
    op.create_index(
        "ix_platform_notice_selected_reads_user_notice",
        "platform_notice_selected_reads",
        ["user_id", "notice_id"],
    )

    op.create_table(
        "platform_notice_global_seen_states",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("last_seen_global_sequence", sa.BigInteger(), nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.add_column(
        "admin_actions",
        sa.Column("target_platform_notice_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_admin_actions_target_platform_notice_id",
        "admin_actions",
        ["target_platform_notice_id"],
    )
    op.create_foreign_key(
        "fk_admin_actions_target_platform_notice_id",
        "admin_actions",
        "platform_notices",
        ["target_platform_notice_id"],
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


def downgrade() -> None:
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
        "fk_admin_actions_target_platform_notice_id",
        "admin_actions",
        type_="foreignkey",
    )
    op.drop_index("ix_admin_actions_target_platform_notice_id", table_name="admin_actions")
    op.drop_column("admin_actions", "target_platform_notice_id")

    op.drop_table("platform_notice_global_seen_states")
    op.drop_index(
        "ix_platform_notice_selected_reads_user_notice",
        table_name="platform_notice_selected_reads",
    )
    op.drop_table("platform_notice_selected_reads")
    op.drop_index(
        "ix_platform_notice_recipients_user_notice",
        table_name="platform_notice_recipients",
    )
    op.drop_table("platform_notice_recipients")
    op.drop_index("ix_platform_notices_cancelled_at", table_name="platform_notices")
    op.drop_index(
        "ix_platform_notices_history_search_trgm",
        table_name="platform_notices",
    )
    op.drop_index("ix_platform_notices_history_order", table_name="platform_notices")
    op.drop_index(
        "ix_platform_notices_created_by_admin_id",
        table_name="platform_notices",
    )
    op.drop_index(
        "ix_platform_notices_audience_cancelled_published_id",
        table_name="platform_notices",
    )
    op.drop_index("uq_platform_notices_global_sequence", table_name="platform_notices")
    op.drop_index(
        "uq_platform_notices_admin_idempotency_key",
        table_name="platform_notices",
    )
    op.drop_table("platform_notices")
    op.execute("DROP SEQUENCE platform_notice_global_sequence_seq")
    op.drop_index("ix_users_platform_notice_active_id", table_name="users")
