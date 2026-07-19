"""create games table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0005_games"
down_revision = "0004_venues"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fifth schema migration: create the games table that captures the core
    # game listing, venue snapshot, and lifecycle state without bookings.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_table(
        "games",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_type", sa.String(length=20), nullable=False),
        sa.Column("payment_collection_type", sa.String(length=30), nullable=False),
        sa.Column(
            "publish_status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'draft'"),
        ),
        sa.Column(
            "game_status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column(
            "public_visibility_status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'visible'"),
        ),
        sa.Column(
            "join_enforcement_status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'open'"),
        ),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("venue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("venue_name_snapshot", sa.String(length=150), nullable=False),
        sa.Column("address_snapshot", sa.Text(), nullable=False),
        sa.Column("city_snapshot", sa.String(length=100), nullable=False),
        sa.Column("state_snapshot", sa.String(length=100), nullable=False),
        sa.Column("neighborhood_snapshot", sa.String(length=120), nullable=True),
        sa.Column("host_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("starts_on_local", sa.Date(), nullable=False),
        sa.Column(
            "timezone",
            sa.String(length=60),
            nullable=False,
            server_default=sa.text("'America/Chicago'"),
        ),
        sa.Column(
            "sport_type",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("'soccer'"),
        ),
        sa.Column("format_label", sa.String(length=20), nullable=False),
        sa.Column(
            "game_player_group",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'coed'"),
        ),
        sa.Column(
            "skill_level",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'any'"),
        ),
        sa.Column("environment_type", sa.String(length=20), nullable=False),
        sa.Column("total_spots", sa.Integer(), nullable=False),
        sa.Column("price_per_player_cents", sa.Integer(), nullable=False),
        sa.Column(
            "currency",
            sa.CHAR(length=3),
            nullable=False,
            server_default=sa.text("'USD'"),
        ),
        sa.Column("minimum_age", sa.Integer(), nullable=True),
        sa.Column(
            "allow_guests",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "max_guests_per_booking",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("2"),
        ),
        sa.Column(
            "host_guest_max",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "waitlist_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "is_chat_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("policy_mode", sa.String(length=30), nullable=False),
        sa.Column("custom_rules_text", sa.Text(), nullable=True),
        sa.Column("custom_cancellation_text", sa.Text(), nullable=True),
        sa.Column("game_notes", sa.Text(), nullable=True),
        sa.Column("parking_notes", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cancellation_source", sa.String(length=20), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
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
            "game_type IN ('official', 'community')",
            name="ck_games_game_type",
        ),
        sa.CheckConstraint(
            "payment_collection_type IN ('in_app', 'external_host', 'none')",
            name="ck_games_payment_collection_type",
        ),
        sa.CheckConstraint(
            "publish_status IN ('draft', 'published', 'archived')",
            name="ck_games_publish_status",
        ),
        sa.CheckConstraint(
            "game_status IN ('active', 'completed', 'cancelled', 'expired', 'removed')",
            name="ck_games_game_status",
        ),
        sa.CheckConstraint(
            "public_visibility_status IN ('visible', 'hidden')",
            name="ck_games_public_visibility_status",
        ),
        sa.CheckConstraint(
            "join_enforcement_status IN ('open', 'paused')",
            name="ck_games_join_enforcement_status",
        ),
        sa.CheckConstraint(
            (
                "cancellation_source IS NULL "
                "OR cancellation_source IN ('host', 'admin', 'system')"
            ),
            name="ck_games_cancellation_source",
        ),
        sa.CheckConstraint(
            "environment_type IN ('indoor', 'outdoor')",
            name="ck_games_environment_type",
        ),
        sa.CheckConstraint(
            "game_player_group IN ('men', 'women', 'coed')",
            name="ck_games_game_player_group",
        ),
        sa.CheckConstraint(
            (
                "skill_level IN ('any', 'beginner', 'recreational', "
                "'intermediate', 'advanced', 'competitive')"
            ),
            name="ck_games_skill_level",
        ),
        sa.CheckConstraint(
            "policy_mode IN ('official_standard', 'custom_hosted')",
            name="ck_games_policy_mode",
        ),
        sa.CheckConstraint(
            "currency = 'USD'",
            name="ck_games_currency",
        ),
        sa.CheckConstraint(
            "ends_at > starts_at",
            name="ck_games_ends_after_starts",
        ),
        sa.CheckConstraint(
            "total_spots > 0",
            name="ck_games_total_spots",
        ),
        sa.CheckConstraint(
            "price_per_player_cents >= 0",
            name="ck_games_price_per_player_cents",
        ),
        sa.CheckConstraint(
            "max_guests_per_booking >= 0",
            name="ck_games_max_guests_per_booking",
        ),
        sa.CheckConstraint(
            "host_guest_max >= 0",
            name="ck_games_host_guest_max",
        ),
        sa.CheckConstraint(
            "(minimum_age IS NULL OR minimum_age >= 13)",
            name="ck_games_minimum_age",
        ),
        sa.CheckConstraint(
            "(game_type <> 'official' OR minimum_age IS NULL)",
            name="ck_games_official_minimum_age_null",
        ),
        sa.CheckConstraint(
            "(game_type <> 'official' OR host_guest_max = 0)",
            name="ck_games_official_host_guest_max_zero",
        ),
        sa.CheckConstraint(
            "(game_type <> 'official' OR custom_rules_text IS NULL)",
            name="ck_games_official_no_custom_rules",
        ),
        sa.CheckConstraint(
            "(game_type <> 'official' OR custom_cancellation_text IS NULL)",
            name="ck_games_official_no_custom_cancellation",
        ),
        sa.CheckConstraint(
            "(game_type <> 'community' OR host_user_id IS NOT NULL)",
            name="ck_games_community_requires_host_user",
        ),
        sa.CheckConstraint(
            "(game_type <> 'official' OR payment_collection_type = 'in_app')",
            name="ck_games_official_payment_collection",
        ),
        sa.CheckConstraint(
            (
                "(game_type <> 'community' "
                "OR payment_collection_type IN ('external_host', 'none'))"
            ),
            name="ck_games_community_payment_collection",
        ),
        sa.CheckConstraint(
            "(payment_collection_type <> 'none' OR price_per_player_cents = 0)",
            name="ck_games_no_payment_requires_free",
        ),
        sa.CheckConstraint(
            "(game_type <> 'official' OR policy_mode = 'official_standard')",
            name="ck_games_official_policy_mode",
        ),
        sa.CheckConstraint(
            "(game_type <> 'community' OR policy_mode = 'custom_hosted')",
            name="ck_games_community_policy_mode",
        ),
        sa.CheckConstraint(
            "(publish_status <> 'published' OR published_at IS NOT NULL)",
            name="ck_games_published_requires_published_at",
        ),
        sa.CheckConstraint(
            "(game_status <> 'cancelled' OR cancelled_at IS NOT NULL)",
            name="ck_games_cancelled_requires_cancelled_at",
        ),
        sa.CheckConstraint(
            "(cancellation_source IS NULL OR game_status = 'cancelled')",
            name="ck_games_cancellation_source_requires_cancelled",
        ),
        sa.CheckConstraint(
            "(game_status <> 'completed' OR completed_at IS NOT NULL)",
            name="ck_games_completed_requires_completed_at",
        ),
        sa.ForeignKeyConstraint(
            ["venue_id"],
            ["venues.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["host_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["cancelled_by_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["completed_by_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_games_venue_id", "games", ["venue_id"], unique=False)
    op.create_index("ix_games_host_user_id", "games", ["host_user_id"], unique=False)
    op.create_index(
        "ix_games_created_by_user_id", "games", ["created_by_user_id"], unique=False
    )
    op.create_index("ix_games_starts_on_local", "games", ["starts_on_local"], unique=False)
    op.create_index("ix_games_starts_at", "games", ["starts_at"], unique=False)
    op.create_index(
        "ux_games_one_active_community_game_per_host_date",
        "games",
        ["host_user_id", "starts_on_local"],
        unique=True,
        postgresql_where=sa.text(
            "game_type = 'community' "
            "AND publish_status = 'published' "
            "AND game_status = 'active' "
            "AND deleted_at IS NULL"
        ),
    )
    op.create_index(
        "ix_games_browse_cards_local_starts_created_id",
        "games",
        ["starts_on_local", "starts_at", "created_at", "id"],
        unique=False,
        postgresql_where=sa.text(
            "publish_status = 'published' "
            "AND game_status = 'active' "
            "AND public_visibility_status = 'visible' "
            "AND deleted_at IS NULL"
        ),
    )
    op.create_index(
        "ix_games_host_cards_starts_created_id",
        "games",
        ["host_user_id", "starts_at", "created_at", "id"],
        unique=False,
        postgresql_where=sa.text(
            "publish_status = 'published' "
            "AND deleted_at IS NULL"
        ),
    )
    admin_official_index_where = sa.text(
        "game_type = 'official' "
        "AND publish_status = 'published' "
        "AND deleted_at IS NULL"
    )
    op.create_index(
        "ix_games_admin_official_status_starts_created_id",
        "games",
        ["game_status", "starts_at", "created_at", "id"],
        unique=False,
        postgresql_where=admin_official_index_where,
    )
    op.create_index(
        "ix_games_admin_official_status_local_starts_created_id",
        "games",
        ["game_status", "starts_on_local", "starts_at", "created_at", "id"],
        unique=False,
        postgresql_where=admin_official_index_where,
    )
    op.create_index(
        "ix_games_admin_official_title_trgm",
        "games",
        ["title"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"title": "gin_trgm_ops"},
        postgresql_where=admin_official_index_where,
    )
    op.create_index(
        "ix_games_admin_official_venue_name_trgm",
        "games",
        ["venue_name_snapshot"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"venue_name_snapshot": "gin_trgm_ops"},
        postgresql_where=admin_official_index_where,
    )
    op.create_index(
        "ix_games_admin_official_city_trgm",
        "games",
        ["city_snapshot"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"city_snapshot": "gin_trgm_ops"},
        postgresql_where=admin_official_index_where,
    )
    op.create_index(
        "ix_games_admin_official_state_trgm",
        "games",
        ["state_snapshot"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"state_snapshot": "gin_trgm_ops"},
        postgresql_where=admin_official_index_where,
    )
    admin_community_index_where = sa.text(
        "game_type = 'community' "
        "AND deleted_at IS NULL"
    )
    op.create_index(
        "ix_games_admin_community_status_local_starts_created_id",
        "games",
        [
            "game_status",
            "public_visibility_status",
            "join_enforcement_status",
            "publish_status",
            "starts_on_local",
            "starts_at",
            "created_at",
            "id",
        ],
        unique=False,
        postgresql_where=admin_community_index_where,
    )
    op.create_index(
        "ix_games_admin_community_title_trgm",
        "games",
        ["title"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"title": "gin_trgm_ops"},
        postgresql_where=admin_community_index_where,
    )
    op.create_index(
        "ix_games_admin_community_venue_name_trgm",
        "games",
        ["venue_name_snapshot"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"venue_name_snapshot": "gin_trgm_ops"},
        postgresql_where=admin_community_index_where,
    )
    op.create_index(
        "ix_games_admin_community_city_trgm",
        "games",
        ["city_snapshot"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"city_snapshot": "gin_trgm_ops"},
        postgresql_where=admin_community_index_where,
    )
    op.create_index(
        "ix_games_admin_community_state_trgm",
        "games",
        ["state_snapshot"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"state_snapshot": "gin_trgm_ops"},
        postgresql_where=admin_community_index_where,
    )


def downgrade() -> None:
    # Downgrade removes the games table and its indexes because this migration
    # only introduces that single table.
    op.drop_index(
        "ix_games_admin_community_state_trgm",
        table_name="games",
    )
    op.drop_index(
        "ix_games_admin_community_city_trgm",
        table_name="games",
    )
    op.drop_index(
        "ix_games_admin_community_venue_name_trgm",
        table_name="games",
    )
    op.drop_index(
        "ix_games_admin_community_title_trgm",
        table_name="games",
    )
    op.drop_index(
        "ix_games_admin_community_status_local_starts_created_id",
        table_name="games",
    )
    op.drop_index(
        "ix_games_admin_official_state_trgm",
        table_name="games",
    )
    op.drop_index(
        "ix_games_admin_official_city_trgm",
        table_name="games",
    )
    op.drop_index(
        "ix_games_admin_official_venue_name_trgm",
        table_name="games",
    )
    op.drop_index(
        "ix_games_admin_official_title_trgm",
        table_name="games",
    )
    op.drop_index(
        "ix_games_admin_official_status_local_starts_created_id",
        table_name="games",
    )
    op.drop_index(
        "ix_games_admin_official_status_starts_created_id",
        table_name="games",
    )
    op.drop_index(
        "ix_games_host_cards_starts_created_id",
        table_name="games",
    )
    op.drop_index(
        "ix_games_browse_cards_local_starts_created_id",
        table_name="games",
    )
    op.drop_index(
        "ux_games_one_active_community_game_per_host_date",
        table_name="games",
    )
    op.drop_index("ix_games_starts_at", table_name="games")
    op.drop_index("ix_games_starts_on_local", table_name="games")
    op.drop_index("ix_games_created_by_user_id", table_name="games")
    op.drop_index("ix_games_host_user_id", table_name="games")
    op.drop_index("ix_games_venue_id", table_name="games")
    op.drop_table("games")
