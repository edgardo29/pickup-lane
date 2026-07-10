"""create venue images table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0037_venue_images"
down_revision = "0036_game_credit_usage"
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
    "issue_credit",
    "reverse_credit",
)
ADMIN_ACTION_TYPES = (
    *PREVIOUS_ADMIN_ACTION_TYPES,
    "create_venue_image",
    "update_venue_image",
    "remove_venue_image",
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
    "target_game_credit_id",
)
ADMIN_ACTION_TARGET_COLUMNS = (
    *PREVIOUS_ADMIN_ACTION_TARGET_COLUMNS,
    "target_venue_image_id",
)
PREVIOUS_ADMIN_ACTION_TARGET_REQUIRED_CHECK = _target_required_check(
    PREVIOUS_ADMIN_ACTION_TARGET_COLUMNS
)
ADMIN_ACTION_TARGET_REQUIRED_CHECK = _target_required_check(
    ADMIN_ACTION_TARGET_COLUMNS
)


def upgrade() -> None:
    op.create_table(
        "venue_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("venue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "storage_provider",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'r2'"),
        ),
        sa.Column("storage_object_key", sa.Text(), nullable=False),
        sa.Column("storage_bucket", sa.String(length=120), nullable=False),
        sa.Column("storage_account_id", sa.String(length=120), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("etag", sa.String(length=255), nullable=True),
        sa.Column(
            "image_role",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'gallery'"),
        ),
        sa.Column(
            "image_status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'pending_upload'"),
        ),
        sa.Column(
            "is_primary",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("alt_text", sa.String(length=280), nullable=True),
        sa.Column("caption", sa.String(length=280), nullable=True),
        sa.Column(
            "upload_requested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("upload_completed_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "image_role IN ('card', 'gallery')",
            name="ck_venue_images_image_role",
        ),
        sa.CheckConstraint(
            "image_status IN ('pending_upload', 'active', 'hidden', 'removed')",
            name="ck_venue_images_image_status",
        ),
        sa.CheckConstraint(
            "char_length(btrim(storage_provider)) > 0",
            name="ck_venue_images_storage_provider_not_empty",
        ),
        sa.CheckConstraint(
            "char_length(btrim(storage_object_key)) > 0",
            name="ck_venue_images_storage_object_key_not_empty",
        ),
        sa.CheckConstraint(
            "char_length(btrim(storage_bucket)) > 0",
            name="ck_venue_images_storage_bucket_not_empty",
        ),
        sa.CheckConstraint(
            "char_length(btrim(storage_account_id)) > 0",
            name="ck_venue_images_storage_account_id_not_empty",
        ),
        sa.CheckConstraint(
            "char_length(btrim(content_type)) > 0",
            name="ck_venue_images_content_type_not_empty",
        ),
        sa.CheckConstraint(
            "size_bytes > 0",
            name="ck_venue_images_size_bytes_positive",
        ),
        sa.CheckConstraint(
            "sort_order >= 0",
            name="ck_venue_images_sort_order_non_negative",
        ),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["venue_id"], ["venues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_venue_images_venue_id", "venue_images", ["venue_id"])
    op.create_index(
        "ix_venue_images_uploaded_by_user_id",
        "venue_images",
        ["uploaded_by_user_id"],
    )
    op.create_index(
        "ix_venue_images_image_status",
        "venue_images",
        ["image_status"],
    )
    op.create_index("ix_venue_images_sort_order", "venue_images", ["sort_order"])
    op.create_index(
        "ix_venue_images_venue_id_image_status_sort_order",
        "venue_images",
        ["venue_id", "image_status", "sort_order"],
    )
    op.create_index(
        "uq_venue_images_storage_object_key",
        "venue_images",
        ["storage_object_key"],
        unique=True,
    )
    op.create_index(
        "uq_venue_images_one_active_primary_per_venue",
        "venue_images",
        ["venue_id"],
        unique=True,
        postgresql_where=sa.text(
            "is_primary = true AND image_status = 'active' AND deleted_at IS NULL"
        ),
    )
    op.add_column(
        "admin_actions",
        sa.Column("target_venue_image_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_admin_actions_target_venue_image_id",
        "admin_actions",
        ["target_venue_image_id"],
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
        "fk_admin_actions_target_venue_image_id",
        "admin_actions",
        "venue_images",
        ["target_venue_image_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM admin_actions "
        "WHERE action_type IN ("
        "'create_venue_image', 'update_venue_image', 'remove_venue_image'"
        ") OR target_venue_image_id IS NOT NULL"
    )
    op.drop_constraint(
        "fk_admin_actions_target_venue_image_id",
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
    op.drop_index("ix_admin_actions_target_venue_image_id", table_name="admin_actions")
    op.drop_column("admin_actions", "target_venue_image_id")
    op.drop_index(
        "uq_venue_images_one_active_primary_per_venue",
        table_name="venue_images",
        postgresql_where=sa.text(
            "is_primary = true AND image_status = 'active' AND deleted_at IS NULL"
        ),
    )
    op.drop_index("uq_venue_images_storage_object_key", table_name="venue_images")
    op.drop_index(
        "ix_venue_images_venue_id_image_status_sort_order",
        table_name="venue_images",
    )
    op.drop_index("ix_venue_images_sort_order", table_name="venue_images")
    op.drop_index("ix_venue_images_image_status", table_name="venue_images")
    op.drop_index("ix_venue_images_uploaded_by_user_id", table_name="venue_images")
    op.drop_index("ix_venue_images_venue_id", table_name="venue_images")
    op.drop_table("venue_images")
