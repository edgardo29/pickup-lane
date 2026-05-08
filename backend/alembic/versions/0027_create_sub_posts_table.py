"""create sub posts table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0027_sub_posts"
down_revision = "0026_game_images"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Twenty-seventh schema migration: create the main Need a Sub post table.
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
        sa.Column("skill_level", sa.String(length=30), nullable=False),
        sa.Column("game_player_group", sa.String(length=30), nullable=False),
        sa.Column("team_name", sa.String(length=120), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
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
            "post_status IN ('draft', 'active', 'filled', 'expired', 'canceled', 'removed')",
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
            "game_player_group IN ('open', 'men', 'women', 'coed')",
            name="ck_sub_posts_game_player_group",
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
            "post_status != 'filled' OR filled_at IS NOT NULL",
            name="ck_sub_posts_filled_requires_filled_at",
        ),
        sa.CheckConstraint(
            "post_status != 'canceled' OR canceled_at IS NOT NULL",
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
        "ix_sub_posts_browse_active_filled_starts_at",
        "sub_posts",
        ["starts_at"],
        postgresql_where=sa.text("post_status IN ('active', 'filled')"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_sub_posts_browse_active_filled_starts_at",
        table_name="sub_posts",
        postgresql_where=sa.text("post_status IN ('active', 'filled')"),
    )
    op.drop_index("ix_sub_posts_post_status_starts_at", table_name="sub_posts")
    op.drop_index("ix_sub_posts_city_state_starts_at", table_name="sub_posts")
    op.drop_index("ix_sub_posts_expires_at", table_name="sub_posts")
    op.drop_index("ix_sub_posts_starts_at", table_name="sub_posts")
    op.drop_index("ix_sub_posts_post_status", table_name="sub_posts")
    op.drop_index("ix_sub_posts_owner_user_id", table_name="sub_posts")
    op.drop_table("sub_posts")
