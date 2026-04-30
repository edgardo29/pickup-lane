"""create venues table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0004_venues"
down_revision = "0003_user_payment_methods"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fourth schema migration: create the venues table for reviewable location
    # records that can later be linked to other booking or host features.
    op.create_table(
        "venues",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
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
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("external_place_id", sa.String(length=255), nullable=True),
        sa.Column(
            "venue_status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'pending_review'"),
        ),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
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
            "venue_status IN ('pending_review', 'approved', 'rejected', 'inactive')",
            name="ck_venues_venue_status",
        ),
        sa.CheckConstraint(
            "char_length(country_code) = 2",
            name="ck_venues_country_code",
        ),
        sa.CheckConstraint(
            "(latitude IS NULL OR latitude BETWEEN -90 AND 90)",
            name="ck_venues_latitude",
        ),
        sa.CheckConstraint(
            "(longitude IS NULL OR longitude BETWEEN -180 AND 180)",
            name="ck_venues_longitude",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_venues_city_state", "venues", ["city", "state"], unique=False)
    op.create_index(
        "ix_venues_venue_status", "venues", ["venue_status"], unique=False
    )
    op.create_index("ix_venues_is_active", "venues", ["is_active"], unique=False)
    op.create_index(
        "ix_venues_external_place_id", "venues", ["external_place_id"], unique=False
    )
    op.create_index(
        "ix_venues_created_by_user_id", "venues", ["created_by_user_id"], unique=False
    )
    op.create_index(
        "ix_venues_approved_by_user_id",
        "venues",
        ["approved_by_user_id"],
        unique=False,
    )


def downgrade() -> None:
    # Downgrade removes the venues table and its indexes because this migration
    # only introduces that single table.
    op.drop_index("ix_venues_approved_by_user_id", table_name="venues")
    op.drop_index("ix_venues_created_by_user_id", table_name="venues")
    op.drop_index("ix_venues_external_place_id", table_name="venues")
    op.drop_index("ix_venues_is_active", table_name="venues")
    op.drop_index("ix_venues_venue_status", table_name="venues")
    op.drop_index("ix_venues_city_state", table_name="venues")
    op.drop_table("venues")
