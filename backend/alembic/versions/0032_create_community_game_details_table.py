"""create community game details table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0032_community_game_details"
down_revision = "0031_sub_post_history"
branch_labels = None
depends_on = None


def _in_check(column_name: str, values: tuple[str, ...]) -> str:
    quoted_values = ", ".join(f"'{value}'" for value in values)
    return f"{column_name} IN ({quoted_values})"


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
    "remove_chat_message",
    "hide_chat_message",
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
)
ADMIN_ACTION_TYPES = (
    *PREVIOUS_ADMIN_ACTION_TYPES,
    "hide_unsafe_community_payment_text",
)
PREVIOUS_ADMIN_ACTION_TYPE_CHECK = _in_check(
    "action_type",
    PREVIOUS_ADMIN_ACTION_TYPES,
)
ADMIN_ACTION_TYPE_CHECK = _in_check("action_type", ADMIN_ACTION_TYPES)


def upgrade() -> None:
    op.create_table(
        "community_game_details",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "payment_methods_snapshot",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("payment_instructions_snapshot", sa.Text(), nullable=True),
        sa.Column(
            "payment_text_moderation_status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'visible'"),
        ),
        sa.Column(
            "payment_text_hidden_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "payment_text_hidden_by_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("payment_text_hidden_reason", sa.Text(), nullable=True),
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
            "jsonb_typeof(payment_methods_snapshot) = 'array'",
            name="ck_community_game_details_payment_methods_array",
        ),
        sa.CheckConstraint(
            "payment_text_moderation_status IN ('visible', 'hidden')",
            name="ck_community_game_details_payment_text_moderation_status",
        ),
        sa.CheckConstraint(
            (
                "payment_text_moderation_status != 'hidden' "
                "OR (payment_text_hidden_at IS NOT NULL "
                "AND NULLIF(BTRIM(payment_text_hidden_reason), '') IS NOT NULL)"
            ),
            name="ck_community_game_details_hidden_requires_metadata",
        ),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["games.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["payment_text_hidden_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("game_id", name="uq_community_game_details_game_id"),
    )
    op.create_index(
        "ix_community_game_details_game_id",
        "community_game_details",
        ["game_id"],
    )
    op.create_index(
        "ix_community_game_details_payment_text_moderation_status",
        "community_game_details",
        ["payment_text_moderation_status"],
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
        "uq_admin_actions_hide_unsafe_community_payment_text_idempotency",
        "admin_actions",
        ["admin_user_id", "target_game_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "action_type = 'hide_unsafe_community_payment_text' "
            "AND idempotency_key IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM admin_actions "
        "WHERE action_type = 'hide_unsafe_community_payment_text'"
    )
    op.drop_index(
        "uq_admin_actions_hide_unsafe_community_payment_text_idempotency",
        table_name="admin_actions",
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
    op.drop_index(
        "ix_community_game_details_payment_text_moderation_status",
        table_name="community_game_details",
    )
    op.drop_index(
        "ix_community_game_details_game_id",
        table_name="community_game_details",
    )
    op.drop_table("community_game_details")
