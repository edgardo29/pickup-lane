"""create game images table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0026_game_images"
down_revision = "0025_venue_approval_requests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Twenty-sixth schema migration: create game_images for Browse page card
    # images and Game Details image galleries.
    op.create_table(
        "game_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("uploaded_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=False),
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
            server_default=sa.text("'active'"),
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
            name="ck_game_images_image_role",
        ),
        sa.CheckConstraint(
            "image_status IN ('active', 'hidden', 'removed')",
            name="ck_game_images_image_status",
        ),
        sa.CheckConstraint(
            "char_length(btrim(image_url)) > 0",
            name="ck_game_images_image_url_not_empty",
        ),
        sa.CheckConstraint(
            "sort_order >= 0",
            name="ck_game_images_sort_order_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["games.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_game_images_game_id",
        "game_images",
        ["game_id"],
        unique=False,
    )
    op.create_index(
        "ix_game_images_uploaded_by_user_id",
        "game_images",
        ["uploaded_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_game_images_image_status",
        "game_images",
        ["image_status"],
        unique=False,
    )
    op.create_index(
        "ix_game_images_sort_order",
        "game_images",
        ["sort_order"],
        unique=False,
    )
    op.create_index(
        "ix_game_images_game_id_image_status_sort_order",
        "game_images",
        ["game_id", "image_status", "sort_order"],
        unique=False,
    )
    op.create_index(
        "uq_game_images_one_active_primary_per_game",
        "game_images",
        ["game_id"],
        unique=True,
        postgresql_where=sa.text(
            "is_primary = true AND image_status = 'active' AND deleted_at IS NULL"
        ),
    )


def downgrade() -> None:
    # Downgrade removes the game_images table and indexes because this migration
    # only introduces that single game image table.
    op.drop_index(
        "uq_game_images_one_active_primary_per_game",
        table_name="game_images",
        postgresql_where=sa.text(
            "is_primary = true AND image_status = 'active' AND deleted_at IS NULL"
        ),
    )
    op.drop_index(
        "ix_game_images_game_id_image_status_sort_order",
        table_name="game_images",
    )
    op.drop_index("ix_game_images_sort_order", table_name="game_images")
    op.drop_index("ix_game_images_image_status", table_name="game_images")
    op.drop_index("ix_game_images_uploaded_by_user_id", table_name="game_images")
    op.drop_index("ix_game_images_game_id", table_name="game_images")
    op.drop_table("game_images")