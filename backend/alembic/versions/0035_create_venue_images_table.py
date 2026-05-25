"""create venue images table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0035_venue_images"
down_revision = "0034_game_credits"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "venue_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("venue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("blob_name", sa.Text(), nullable=False),
        sa.Column("container_name", sa.String(length=120), nullable=False),
        sa.Column("storage_account_name", sa.String(length=120), nullable=False),
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
            "char_length(btrim(blob_name)) > 0",
            name="ck_venue_images_blob_name_not_empty",
        ),
        sa.CheckConstraint(
            "char_length(btrim(container_name)) > 0",
            name="ck_venue_images_container_name_not_empty",
        ),
        sa.CheckConstraint(
            "char_length(btrim(storage_account_name)) > 0",
            name="ck_venue_images_storage_account_name_not_empty",
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
        "uq_venue_images_blob_name",
        "venue_images",
        ["blob_name"],
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


def downgrade() -> None:
    op.drop_index(
        "uq_venue_images_one_active_primary_per_venue",
        table_name="venue_images",
        postgresql_where=sa.text(
            "is_primary = true AND image_status = 'active' AND deleted_at IS NULL"
        ),
    )
    op.drop_index("uq_venue_images_blob_name", table_name="venue_images")
    op.drop_index(
        "ix_venue_images_venue_id_image_status_sort_order",
        table_name="venue_images",
    )
    op.drop_index("ix_venue_images_sort_order", table_name="venue_images")
    op.drop_index("ix_venue_images_image_status", table_name="venue_images")
    op.drop_index("ix_venue_images_uploaded_by_user_id", table_name="venue_images")
    op.drop_index("ix_venue_images_venue_id", table_name="venue_images")
    op.drop_table("venue_images")
