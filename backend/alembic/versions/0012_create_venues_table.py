"""create venues table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0012_venues'
down_revision = '0011_user_stats'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'venues',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('address_line_1', sa.String(length=200), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('state', sa.String(length=100), nullable=False),
        sa.Column('postal_code', sa.String(length=20), nullable=False),
        sa.Column('country_code', sa.CHAR(length=2), nullable=False, server_default=sa.text("'US'")),
        sa.Column('neighborhood', sa.String(length=120)),
        sa.Column('latitude', sa.Numeric(precision=9, scale=6)),
        sa.Column('longitude', sa.Numeric(precision=9, scale=6)),
        sa.Column('external_place_id', sa.String(length=255)),
        sa.Column('venue_status', sa.String(length=30), nullable=False, server_default=sa.text("'pending_review'")),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('approved_by_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('approved_at', sa.DateTime(timezone=True)),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
        sa.CheckConstraint('char_length(country_code) = 2', name='ck_venues_country_code'),
        sa.CheckConstraint('(latitude IS NULL OR latitude BETWEEN -90 AND 90)', name='ck_venues_latitude'),
        sa.CheckConstraint('(longitude IS NULL OR longitude BETWEEN -180 AND 180)', name='ck_venues_longitude'),
        sa.CheckConstraint("venue_status IN ('pending_review', 'approved', 'rejected', 'inactive')", name='ck_venues_venue_status'),
        sa.ForeignKeyConstraint(['approved_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_venues_approved_by_user_id', 'venues', ['approved_by_user_id'], unique=False)
    op.create_index('ix_venues_city_state', 'venues', ['city', 'state'], unique=False)
    op.create_index('ix_venues_created_by_user_id', 'venues', ['created_by_user_id'], unique=False)
    op.create_index('ix_venues_external_place_id', 'venues', ['external_place_id'], unique=False)
    op.create_index('ix_venues_is_active', 'venues', ['is_active'], unique=False)
    op.create_index('ix_venues_venue_status', 'venues', ['venue_status'], unique=False)


def downgrade() -> None:
    op.drop_table('venues')
