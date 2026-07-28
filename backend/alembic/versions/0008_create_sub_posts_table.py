"""create sub_posts table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0008_sub_posts'
down_revision = '0007_policy_acceptances'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'sub_posts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('owner_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('post_status', sa.String(length=30), nullable=False),
        sa.Column('public_visibility_status', sa.String(length=20), nullable=False, server_default=sa.text("'visible'")),
        sa.Column('sport_type', sa.String(length=50), nullable=False, server_default=sa.text("'soccer'")),
        sa.Column('format_label', sa.String(length=20), nullable=False),
        sa.Column('environment_type', sa.String(length=20), nullable=False),
        sa.Column('skill_level', sa.String(length=30), nullable=False),
        sa.Column('game_player_group', sa.String(length=30), nullable=False),
        sa.Column('team_name', sa.String(length=120)),
        sa.Column('starts_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ends_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('starts_on_local', sa.Date(), nullable=False),
        sa.Column('timezone', sa.String(length=60), nullable=False, server_default=sa.text("'America/Chicago'")),
        sa.Column('location_name', sa.String(length=150), nullable=False),
        sa.Column('address_line_1', sa.String(length=200), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('state', sa.String(length=100), nullable=False),
        sa.Column('postal_code', sa.String(length=20), nullable=False),
        sa.Column('country_code', sa.CHAR(length=2), nullable=False, server_default=sa.text("'US'")),
        sa.Column('neighborhood', sa.String(length=120)),
        sa.Column('subs_needed', sa.Integer(), nullable=False),
        sa.Column('price_due_at_venue_cents', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('currency', sa.CHAR(length=3), nullable=False, server_default=sa.text("'USD'")),
        sa.Column('payment_note', sa.Text()),
        sa.Column('notes', sa.Text()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('filled_at', sa.DateTime(timezone=True)),
        sa.Column('canceled_at', sa.DateTime(timezone=True)),
        sa.Column('canceled_by_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('cancel_reason', sa.Text()),
        sa.Column('removed_at', sa.DateTime(timezone=True)),
        sa.Column('removed_by_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('remove_reason', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("post_status != 'cancelled' OR canceled_at IS NOT NULL", name='ck_sub_posts_canceled_requires_canceled_at'),
        sa.CheckConstraint("post_status != 'completed' OR filled_at IS NOT NULL", name='ck_sub_posts_completed_requires_filled_at'),
        sa.CheckConstraint("currency = 'USD'", name='ck_sub_posts_currency'),
        sa.CheckConstraint("environment_type IN ('indoor', 'outdoor')", name='ck_sub_posts_environment_type'),
        sa.CheckConstraint('expires_at <= starts_at', name='ck_sub_posts_expires_not_after_starts'),
        sa.CheckConstraint("game_player_group IN ('men', 'women', 'coed')", name='ck_sub_posts_game_player_group'),
        sa.CheckConstraint("post_status IN ('active', 'completed', 'cancelled', 'expired', 'removed')", name='ck_sub_posts_post_status'),
        sa.CheckConstraint('price_due_at_venue_cents >= 0', name='ck_sub_posts_price_due_non_negative'),
        sa.CheckConstraint("public_visibility_status IN ('visible', 'hidden')", name='ck_sub_posts_public_visibility_status'),
        sa.CheckConstraint("post_status != 'removed' OR removed_at IS NOT NULL", name='ck_sub_posts_removed_requires_removed_at'),
        sa.CheckConstraint("skill_level IN ('any', 'beginner', 'recreational', 'intermediate', 'advanced', 'competitive')", name='ck_sub_posts_skill_level'),
        sa.CheckConstraint("sport_type IN ('soccer')", name='ck_sub_posts_sport_type'),
        sa.CheckConstraint('starts_at < ends_at', name='ck_sub_posts_starts_before_ends'),
        sa.CheckConstraint('subs_needed > 0', name='ck_sub_posts_subs_needed_positive'),
        sa.ForeignKeyConstraint(['canceled_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['owner_user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['removed_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sub_posts_admin_city_trgm', 'sub_posts', ['city'], unique=False, postgresql_using='gin', postgresql_ops={'city': 'gin_trgm_ops'})
    op.create_index('ix_sub_posts_admin_location_name_trgm', 'sub_posts', ['location_name'], unique=False, postgresql_using='gin', postgresql_ops={'location_name': 'gin_trgm_ops'})
    op.create_index('ix_sub_posts_admin_state_trgm', 'sub_posts', ['state'], unique=False, postgresql_using='gin', postgresql_ops={'state': 'gin_trgm_ops'})
    op.create_index('ix_sub_posts_admin_status_local_starts_created_id', 'sub_posts', ['post_status', 'starts_on_local', 'starts_at', 'created_at', 'id'], unique=False)
    op.create_index('ix_sub_posts_admin_team_name_trgm', 'sub_posts', ['team_name'], unique=False, postgresql_using='gin', postgresql_ops={'team_name': 'gin_trgm_ops'})
    op.create_index('ix_sub_posts_browse_active_starts_at', 'sub_posts', ['starts_at'], unique=False, postgresql_where=sa.text("post_status = 'active' AND public_visibility_status = 'visible'"))
    op.create_index('ix_sub_posts_cards_active_local_starts_created_id', 'sub_posts', ['starts_on_local', 'starts_at', 'created_at', 'id'], unique=False, postgresql_where=sa.text("post_status = 'active' AND public_visibility_status = 'visible'"))
    op.create_index('ix_sub_posts_city_state_starts_at', 'sub_posts', ['city', 'state', 'starts_at'], unique=False)
    op.create_index('ix_sub_posts_expires_at', 'sub_posts', ['expires_at'], unique=False)
    op.create_index('ix_sub_posts_owner_cards_active_local_starts_created_id', 'sub_posts', ['owner_user_id', 'starts_on_local', 'starts_at', 'created_at', 'id'], unique=False, postgresql_where=sa.text("post_status = 'active' AND public_visibility_status = 'visible'"))
    op.create_index('ix_sub_posts_owner_user_id', 'sub_posts', ['owner_user_id'], unique=False)
    op.create_index('ix_sub_posts_post_status', 'sub_posts', ['post_status'], unique=False)
    op.create_index('ix_sub_posts_post_status_starts_at', 'sub_posts', ['post_status', 'starts_at'], unique=False)
    op.create_index('ix_sub_posts_starts_at', 'sub_posts', ['starts_at'], unique=False)
    op.create_index('ix_sub_posts_starts_on_local', 'sub_posts', ['starts_on_local'], unique=False)
    op.create_index('ux_sub_posts_owner_active_starts_on_local', 'sub_posts', ['owner_user_id', 'starts_on_local'], unique=True, postgresql_where=sa.text("post_status = 'active'"))


def downgrade() -> None:
    op.drop_table('sub_posts')
