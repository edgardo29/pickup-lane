"""create support flags table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0043_support_flags"
down_revision = "0041_sub_post_chat_reads"
branch_labels = None
depends_on = None


SUPPORT_FLAG_TYPE_CHECK = (
    "flag_type IN ("
    "'venue_image_upload_failed', 'venue_image_readiness_failed', "
    "'account_delete_partial_failure', 'community_game_review_required'"
    ")"
)


SUPPORT_FLAG_TARGET_REQUIRED_CHECK = (
    "target_user_id IS NOT NULL "
    "OR target_game_id IS NOT NULL "
    "OR target_booking_id IS NOT NULL "
    "OR target_payment_id IS NOT NULL "
    "OR target_refund_id IS NOT NULL "
    "OR target_game_credit_id IS NOT NULL "
    "OR target_venue_id IS NOT NULL "
    "OR target_venue_image_id IS NOT NULL "
    "OR target_notification_id IS NOT NULL"
)


SUPPORT_FLAG_RESOLUTION_STATE_CHECK = (
    "(flag_status = 'open' "
    "AND resolved_at IS NULL "
    "AND resolved_by_user_id IS NULL "
    "AND resolution_outcome IS NULL "
    "AND resolution_reason IS NULL) "
    "OR "
    "(flag_status = 'resolved' "
    "AND resolved_at IS NOT NULL "
    "AND resolved_by_user_id IS NOT NULL "
    "AND resolution_outcome IS NOT NULL "
    "AND resolution_reason IS NOT NULL)"
)


def _in_check(column_name: str, values: tuple[str, ...]) -> str:
    quoted_values = ", ".join(f"'{value}'" for value in values)
    return f"{column_name} IN ({quoted_values})"


def _target_required_check(columns: tuple[str, ...]) -> str:
    return " OR ".join(f"{column} IS NOT NULL" for column in columns)


PREVIOUS_ADMIN_ACTION_TYPES = (
    "cancel_game",
    "refund_booking",
    "create_refund",
    "update_refund",
    "mark_no_show",
    "create_payment",
    "update_payment",
    "reverse_no_show",
    "suspend_user",
    "unsuspend_user",
    "restrict_hosting",
    "restore_hosting",
    "approve_venue",
    "delete_user",
    "reject_venue",
    "mark_chat_message_reviewed",
    "remove_chat_message",
    "restore_chat_message",
    "update_game",
    "create_game_chat",
    "update_game_chat",
    "update_booking",
    "update_participant",
    "create_official_game",
    "update_official_game",
    "assign_official_host",
    "remove_official_host",
    "admin_add_player",
    "admin_remove_player",
    "waive_payment",
    "create_notification",
    "update_notification",
    "user_role_changed",
    "append_audit_note",
    "remove_sub_post",
    "hide_unsafe_community_payment_text",
    "restore_community_payment_text",
    "hide_community_game",
    "restore_community_game",
    "pause_community_game_joining",
    "resume_community_game_joining",
    "admin_cancel_community_game",
    "hide_need_sub_post",
    "restore_need_sub_post",
    "create_financial_outcome",
    "apply_financial_outcome",
    "issue_credit",
    "reverse_credit",
    "create_venue_image",
    "update_venue_image",
    "remove_venue_image",
)
ADMIN_ACTION_TYPES = (*PREVIOUS_ADMIN_ACTION_TYPES, "resolve_support_flag")
PREVIOUS_ADMIN_ACTION_TYPE_CHECK = _in_check(
    "action_type",
    PREVIOUS_ADMIN_ACTION_TYPES,
)
ADMIN_ACTION_TYPE_CHECK = _in_check("action_type", ADMIN_ACTION_TYPES)

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
    "target_financial_outcome_id",
    "target_host_publish_fee_id",
    "target_host_publish_entitlement_id",
    "target_game_credit_id",
    "target_venue_image_id",
    "target_sub_chat_message_id",
)
ADMIN_ACTION_TARGET_COLUMNS = (
    *PREVIOUS_ADMIN_ACTION_TARGET_COLUMNS,
    "target_support_flag_id",
)
PREVIOUS_ADMIN_ACTION_TARGET_REQUIRED_CHECK = _target_required_check(
    PREVIOUS_ADMIN_ACTION_TARGET_COLUMNS
)
ADMIN_ACTION_TARGET_REQUIRED_CHECK = _target_required_check(
    ADMIN_ACTION_TARGET_COLUMNS
)


def upgrade() -> None:
    op.create_table(
        "support_flags",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("flag_type", sa.String(length=80), nullable=False),
        sa.Column(
            "flag_status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'open'"),
        ),
        sa.Column(
            "severity",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'attention'"),
        ),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_game_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_booking_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_payment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_refund_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "target_game_credit_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("target_venue_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "target_venue_image_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "target_notification_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=160), nullable=True),
        sa.Column(
            "source_admin_action_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolution_outcome", sa.String(length=60), nullable=True),
        sa.Column("resolution_reason", sa.Text(), nullable=True),
        sa.Column(
            "resolution_admin_action_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint(SUPPORT_FLAG_TYPE_CHECK, name="ck_support_flags_flag_type"),
        sa.CheckConstraint(
            "flag_status IN ('open', 'resolved')",
            name="ck_support_flags_flag_status",
        ),
        sa.CheckConstraint(
            "severity IN ('attention', 'urgent', 'critical')",
            name="ck_support_flags_severity",
        ),
        sa.CheckConstraint(
            "source IN ('system', 'admin', 'stripe', 'venue_image', 'account', 'official_game')",
            name="ck_support_flags_source",
        ),
        sa.CheckConstraint(
            (
                "resolution_outcome IS NULL OR resolution_outcome IN ("
                "'handled_externally', 'retried_successfully', "
                "'no_action_needed', 'duplicate', 'invalid_flag'"
                ")"
            ),
            name="ck_support_flags_resolution_outcome",
        ),
        sa.CheckConstraint(
            SUPPORT_FLAG_TARGET_REQUIRED_CHECK,
            name="ck_support_flags_target_required",
        ),
        sa.CheckConstraint(
            SUPPORT_FLAG_RESOLUTION_STATE_CHECK,
            name="ck_support_flags_resolution_state",
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
            ["target_game_credit_id"],
            ["game_credits.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_venue_id"],
            ["venues.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_venue_image_id"],
            ["venue_images.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_notification_id"],
            ["notifications.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_admin_action_id"],
            ["admin_actions.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["resolution_admin_action_id"],
            ["admin_actions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_support_flags_flag_type", "support_flags", ["flag_type"])
    op.create_index("ix_support_flags_flag_status", "support_flags", ["flag_status"])
    op.create_index("ix_support_flags_created_at", "support_flags", ["created_at"])
    op.create_index("ix_support_flags_resolved_at", "support_flags", ["resolved_at"])
    op.create_index("ix_support_flags_target_user_id", "support_flags", ["target_user_id"])
    op.create_index("ix_support_flags_target_game_id", "support_flags", ["target_game_id"])
    op.create_index(
        "ix_support_flags_target_booking_id",
        "support_flags",
        ["target_booking_id"],
    )
    op.create_index(
        "ix_support_flags_target_payment_id",
        "support_flags",
        ["target_payment_id"],
    )
    op.create_index(
        "ix_support_flags_target_refund_id",
        "support_flags",
        ["target_refund_id"],
    )
    op.create_index(
        "ix_support_flags_target_game_credit_id",
        "support_flags",
        ["target_game_credit_id"],
    )
    op.create_index("ix_support_flags_target_venue_id", "support_flags", ["target_venue_id"])
    op.create_index(
        "ix_support_flags_target_venue_image_id",
        "support_flags",
        ["target_venue_image_id"],
    )
    op.create_index(
        "ix_support_flags_target_notification_id",
        "support_flags",
        ["target_notification_id"],
    )
    op.create_index(
        "ix_support_flags_source_admin_action_id",
        "support_flags",
        ["source_admin_action_id"],
    )
    op.create_index(
        "ix_support_flags_resolution_admin_action_id",
        "support_flags",
        ["resolution_admin_action_id"],
    )
    op.create_index(
        "uq_support_flags_flag_type_idempotency_key",
        "support_flags",
        ["flag_type", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )
    op.add_column(
        "admin_actions",
        sa.Column("target_support_flag_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_admin_actions_target_support_flag_id",
        "admin_actions",
        ["target_support_flag_id"],
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
    op.create_foreign_key(
        "fk_admin_actions_target_support_flag_id",
        "admin_actions",
        "support_flags",
        ["target_support_flag_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM admin_actions "
        "WHERE action_type = 'resolve_support_flag' "
        "OR target_support_flag_id IS NOT NULL"
    )
    op.drop_constraint(
        "fk_admin_actions_target_support_flag_id",
        "admin_actions",
        type_="foreignkey",
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
        "ck_admin_actions_target_required",
        "admin_actions",
        type_="check",
    )
    op.create_check_constraint(
        "ck_admin_actions_target_required",
        "admin_actions",
        PREVIOUS_ADMIN_ACTION_TARGET_REQUIRED_CHECK,
    )
    op.drop_index("ix_admin_actions_target_support_flag_id", table_name="admin_actions")
    op.drop_column("admin_actions", "target_support_flag_id")
    op.drop_table("support_flags")
