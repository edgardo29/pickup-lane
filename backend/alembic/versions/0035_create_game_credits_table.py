"""create game credits table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0035_game_credits"
down_revision = "0034_game_chat_reads"
branch_labels = None
depends_on = None


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
    "change_staff_role",
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
)
ADMIN_ACTION_TYPES = (
    *PREVIOUS_ADMIN_ACTION_TYPES,
    "issue_credit",
    "reverse_credit",
)
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
)
ADMIN_ACTION_TARGET_COLUMNS = (
    *PREVIOUS_ADMIN_ACTION_TARGET_COLUMNS,
    "target_game_credit_id",
)
PREVIOUS_ADMIN_ACTION_TARGET_REQUIRED_CHECK = _target_required_check(
    PREVIOUS_ADMIN_ACTION_TARGET_COLUMNS
)
ADMIN_ACTION_TARGET_REQUIRED_CHECK = _target_required_check(
    ADMIN_ACTION_TARGET_COLUMNS
)


def upgrade() -> None:
    op.create_table(
        "game_credits",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("remaining_cents", sa.Integer(), nullable=False),
        sa.Column(
            "currency",
            sa.CHAR(length=3),
            server_default=sa.text("'USD'"),
            nullable=False,
        ),
        sa.Column(
            "credit_status",
            sa.String(length=30),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column("credit_reason", sa.String(length=40), nullable=False),
        sa.Column("source_game_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_booking_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_payment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("issued_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reversed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reversed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "credit_status IN ('active', 'used', 'expired', 'reversed')",
            name="ck_game_credits_credit_status",
        ),
        sa.CheckConstraint(
            (
                "credit_reason IN ('official_game_cancelled', "
                "'weather_cancelled', 'player_cancelled_on_time', "
                "'admin_credit', 'support_adjustment')"
            ),
            name="ck_game_credits_credit_reason",
        ),
        sa.CheckConstraint("currency = 'USD'", name="ck_game_credits_currency"),
        sa.CheckConstraint("amount_cents > 0", name="ck_game_credits_amount_cents"),
        sa.CheckConstraint(
            "remaining_cents >= 0",
            name="ck_game_credits_remaining_cents_non_negative",
        ),
        sa.CheckConstraint(
            "remaining_cents <= amount_cents",
            name="ck_game_credits_remaining_not_above_amount",
        ),
        sa.CheckConstraint(
            "(credit_status = 'active' OR remaining_cents = 0)",
            name="ck_game_credits_inactive_has_no_remaining",
        ),
        sa.ForeignKeyConstraint(
            ["issued_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["reversed_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_booking_id"],
            ["bookings.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_game_id"],
            ["games.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_payment_id"],
            ["payments.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "idempotency_key",
            name="uq_game_credits_idempotency_key",
        ),
    )
    op.create_index("ix_game_credits_created_at", "game_credits", ["created_at"])
    op.create_index("ix_game_credits_credit_reason", "game_credits", ["credit_reason"])
    op.create_index("ix_game_credits_credit_status", "game_credits", ["credit_status"])
    op.create_index(
        "ix_game_credits_source_booking_id",
        "game_credits",
        ["source_booking_id"],
    )
    op.create_index(
        "ix_game_credits_source_game_id",
        "game_credits",
        ["source_game_id"],
    )
    op.create_index(
        "ix_game_credits_source_payment_id",
        "game_credits",
        ["source_payment_id"],
    )
    op.create_index("ix_game_credits_user_id", "game_credits", ["user_id"])
    op.create_index(
        "ix_game_credits_user_id_credit_status",
        "game_credits",
        ["user_id", "credit_status"],
    )
    op.add_column(
        "admin_actions",
        sa.Column("target_game_credit_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_admin_actions_target_game_credit_id",
        "admin_actions",
        ["target_game_credit_id"],
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
        "fk_admin_actions_target_game_credit_id",
        "admin_actions",
        "game_credits",
        ["target_game_credit_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM admin_actions "
        "WHERE action_type IN ('issue_credit', 'reverse_credit') "
        "OR target_game_credit_id IS NOT NULL"
    )
    op.drop_constraint(
        "fk_admin_actions_target_game_credit_id",
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
    op.drop_index("ix_admin_actions_target_game_credit_id", table_name="admin_actions")
    op.drop_column("admin_actions", "target_game_credit_id")
    op.drop_index("ix_game_credits_user_id_credit_status", table_name="game_credits")
    op.drop_index("ix_game_credits_user_id", table_name="game_credits")
    op.drop_index("ix_game_credits_source_payment_id", table_name="game_credits")
    op.drop_index("ix_game_credits_source_game_id", table_name="game_credits")
    op.drop_index("ix_game_credits_source_booking_id", table_name="game_credits")
    op.drop_index("ix_game_credits_credit_status", table_name="game_credits")
    op.drop_index("ix_game_credits_credit_reason", table_name="game_credits")
    op.drop_index("ix_game_credits_created_at", table_name="game_credits")
    op.drop_table("game_credits")
