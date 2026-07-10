"""create sub posts table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0027_sub_posts"
down_revision = "0026_game_images"
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
)
ADMIN_ACTION_TYPES = (*PREVIOUS_ADMIN_ACTION_TYPES, "remove_sub_post")
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
)
ADMIN_ACTION_TARGET_COLUMNS = (
    *PREVIOUS_ADMIN_ACTION_TARGET_COLUMNS,
    "target_sub_post_id",
)
PREVIOUS_ADMIN_ACTION_TARGET_REQUIRED_CHECK = _target_required_check(
    PREVIOUS_ADMIN_ACTION_TARGET_COLUMNS
)
ADMIN_ACTION_TARGET_REQUIRED_CHECK = _target_required_check(
    ADMIN_ACTION_TARGET_COLUMNS
)


def upgrade() -> None:
    # Twenty-seventh schema migration: create the main Need a Sub post table.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_table(
        "sub_posts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("post_status", sa.String(length=30), nullable=False),
        sa.Column(
            "sport_type",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'soccer'"),
        ),
        sa.Column("format_label", sa.String(length=20), nullable=False),
        sa.Column("environment_type", sa.String(length=20), nullable=False),
        sa.Column("skill_level", sa.String(length=30), nullable=False),
        sa.Column("game_player_group", sa.String(length=30), nullable=False),
        sa.Column("team_name", sa.String(length=120), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("starts_on_local", sa.Date(), nullable=False),
        sa.Column(
            "timezone",
            sa.String(length=60),
            nullable=False,
            server_default=sa.text("'America/Chicago'"),
        ),
        sa.Column("location_name", sa.String(length=150), nullable=False),
        sa.Column("address_line_1", sa.String(length=200), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=100), nullable=False),
        sa.Column("postal_code", sa.String(length=20), nullable=False),
        sa.Column(
            "country_code",
            sa.CHAR(length=2),
            nullable=False,
            server_default=sa.text("'US'"),
        ),
        sa.Column("neighborhood", sa.String(length=120), nullable=True),
        sa.Column("subs_needed", sa.Integer(), nullable=False),
        sa.Column(
            "price_due_at_venue_cents",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "currency",
            sa.CHAR(length=3),
            nullable=False,
            server_default=sa.text("'USD'"),
        ),
        sa.Column("payment_note", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("filled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canceled_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("removed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("remove_reason", sa.Text(), nullable=True),
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
            "post_status IN ('active', 'completed', 'cancelled', 'expired', 'removed')",
            name="ck_sub_posts_post_status",
        ),
        sa.CheckConstraint(
            "sport_type IN ('soccer')",
            name="ck_sub_posts_sport_type",
        ),
        sa.CheckConstraint(
            (
                "skill_level IN ('any', 'beginner', 'recreational', "
                "'intermediate', 'advanced', 'competitive')"
            ),
            name="ck_sub_posts_skill_level",
        ),
        sa.CheckConstraint(
            "game_player_group IN ('men', 'women', 'coed')",
            name="ck_sub_posts_game_player_group",
        ),
        sa.CheckConstraint(
            "environment_type IN ('indoor', 'outdoor')",
            name="ck_sub_posts_environment_type",
        ),
        sa.CheckConstraint("subs_needed > 0", name="ck_sub_posts_subs_needed_positive"),
        sa.CheckConstraint(
            "price_due_at_venue_cents >= 0",
            name="ck_sub_posts_price_due_non_negative",
        ),
        sa.CheckConstraint("currency = 'USD'", name="ck_sub_posts_currency"),
        sa.CheckConstraint("starts_at < ends_at", name="ck_sub_posts_starts_before_ends"),
        sa.CheckConstraint(
            "expires_at <= starts_at",
            name="ck_sub_posts_expires_not_after_starts",
        ),
        sa.CheckConstraint(
            "post_status != 'completed' OR filled_at IS NOT NULL",
            name="ck_sub_posts_completed_requires_filled_at",
        ),
        sa.CheckConstraint(
            "post_status != 'cancelled' OR canceled_at IS NOT NULL",
            name="ck_sub_posts_canceled_requires_canceled_at",
        ),
        sa.CheckConstraint(
            "post_status != 'removed' OR removed_at IS NOT NULL",
            name="ck_sub_posts_removed_requires_removed_at",
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["canceled_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["removed_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sub_posts_owner_user_id", "sub_posts", ["owner_user_id"])
    op.create_index("ix_sub_posts_post_status", "sub_posts", ["post_status"])
    op.create_index(
        "ix_sub_posts_starts_on_local",
        "sub_posts",
        ["starts_on_local"],
    )
    op.create_index("ix_sub_posts_starts_at", "sub_posts", ["starts_at"])
    op.create_index("ix_sub_posts_expires_at", "sub_posts", ["expires_at"])
    op.create_index(
        "ix_sub_posts_city_state_starts_at",
        "sub_posts",
        ["city", "state", "starts_at"],
    )
    op.create_index(
        "ix_sub_posts_post_status_starts_at",
        "sub_posts",
        ["post_status", "starts_at"],
    )
    op.create_index(
        "ix_sub_posts_browse_active_starts_at",
        "sub_posts",
        ["starts_at"],
        postgresql_where=sa.text("post_status = 'active'"),
    )
    op.create_index(
        "ix_sub_posts_cards_active_local_starts_created_id",
        "sub_posts",
        ["starts_on_local", "starts_at", "created_at", "id"],
        postgresql_where=sa.text("post_status = 'active'"),
    )
    op.create_index(
        "ix_sub_posts_owner_cards_active_local_starts_created_id",
        "sub_posts",
        ["owner_user_id", "starts_on_local", "starts_at", "created_at", "id"],
        postgresql_where=sa.text("post_status = 'active'"),
    )
    op.create_index(
        "ux_sub_posts_owner_active_starts_on_local",
        "sub_posts",
        ["owner_user_id", "starts_on_local"],
        unique=True,
        postgresql_where=sa.text("post_status = 'active'"),
    )
    op.create_index(
        "ix_sub_posts_admin_status_local_starts_created_id",
        "sub_posts",
        ["post_status", "starts_on_local", "starts_at", "created_at", "id"],
    )
    op.create_index(
        "ix_sub_posts_admin_location_name_trgm",
        "sub_posts",
        ["location_name"],
        postgresql_using="gin",
        postgresql_ops={"location_name": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_sub_posts_admin_team_name_trgm",
        "sub_posts",
        ["team_name"],
        postgresql_using="gin",
        postgresql_ops={"team_name": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_sub_posts_admin_city_trgm",
        "sub_posts",
        ["city"],
        postgresql_using="gin",
        postgresql_ops={"city": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_sub_posts_admin_state_trgm",
        "sub_posts",
        ["state"],
        postgresql_using="gin",
        postgresql_ops={"state": "gin_trgm_ops"},
    )
    op.add_column(
        "admin_actions",
        sa.Column("target_sub_post_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_admin_actions_target_sub_post_id",
        "admin_actions",
        ["target_sub_post_id"],
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
        "fk_admin_actions_target_sub_post_id",
        "admin_actions",
        "sub_posts",
        ["target_sub_post_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM admin_actions "
        "WHERE action_type = 'remove_sub_post' "
        "OR target_sub_post_id IS NOT NULL"
    )
    op.drop_constraint(
        "fk_admin_actions_target_sub_post_id",
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
    op.drop_index(
        "uq_admin_actions_remove_sub_post_idempotency",
        table_name="admin_actions",
    )
    op.drop_index("ix_admin_actions_target_sub_post_id", table_name="admin_actions")
    op.drop_column("admin_actions", "target_sub_post_id")
    op.drop_index(
        "ux_sub_posts_owner_active_starts_on_local",
        table_name="sub_posts",
    )
    op.drop_index("ix_sub_posts_admin_state_trgm", table_name="sub_posts")
    op.drop_index("ix_sub_posts_admin_city_trgm", table_name="sub_posts")
    op.drop_index("ix_sub_posts_admin_team_name_trgm", table_name="sub_posts")
    op.drop_index("ix_sub_posts_admin_location_name_trgm", table_name="sub_posts")
    op.drop_index(
        "ix_sub_posts_admin_status_local_starts_created_id",
        table_name="sub_posts",
    )
    op.drop_index(
        "ix_sub_posts_browse_active_starts_at",
        table_name="sub_posts",
        postgresql_where=sa.text("post_status = 'active'"),
    )
    op.drop_index(
        "ix_sub_posts_owner_cards_active_local_starts_created_id",
        table_name="sub_posts",
        postgresql_where=sa.text("post_status = 'active'"),
    )
    op.drop_index(
        "ix_sub_posts_cards_active_local_starts_created_id",
        table_name="sub_posts",
        postgresql_where=sa.text("post_status = 'active'"),
    )
    op.drop_index(
        "ix_sub_posts_post_status_starts_at",
        table_name="sub_posts",
    )
    op.drop_index(
        "ix_sub_posts_city_state_starts_at",
        table_name="sub_posts",
    )
    op.drop_index("ix_sub_posts_expires_at", table_name="sub_posts")
    op.drop_index("ix_sub_posts_starts_at", table_name="sub_posts")
    op.drop_index(
        "ix_sub_posts_starts_on_local",
        table_name="sub_posts",
    )
    op.drop_index("ix_sub_posts_post_status", table_name="sub_posts")
    op.drop_index("ix_sub_posts_owner_user_id", table_name="sub_posts")
    op.drop_table("sub_posts")
