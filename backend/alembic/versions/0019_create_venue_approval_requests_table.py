"""create venue_approval_requests table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0019_venue_approval_requests'
down_revision = '0018_sub_post_status_history'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'venue_approval_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('submitted_by_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('venue_id', postgresql.UUID(as_uuid=True)),
        sa.Column('requested_name', sa.String(length=150), nullable=False),
        sa.Column('requested_address_line_1', sa.String(length=200), nullable=False),
        sa.Column('requested_city', sa.String(length=100), nullable=False),
        sa.Column('requested_state', sa.String(length=100), nullable=False),
        sa.Column('requested_postal_code', sa.String(length=20), nullable=False),
        sa.Column('requested_country_code', sa.CHAR(length=2), nullable=False, server_default=sa.text("'US'")),
        sa.Column('request_status', sa.String(length=30), nullable=False, server_default=sa.text("'pending_review'")),
        sa.Column('reviewed_by_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('reviewed_at', sa.DateTime(timezone=True)),
        sa.Column('review_notes', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("(request_status <> 'approved' OR venue_id IS NOT NULL)", name='ck_venue_approval_requests_approved_requires_venue_id'),
        sa.CheckConstraint("request_status IN ('pending_review', 'approved', 'rejected', 'inactive')", name='ck_venue_approval_requests_request_status'),
        sa.CheckConstraint('char_length(requested_country_code) = 2', name='ck_venue_approval_requests_requested_country_code'),
        sa.CheckConstraint("request_status NOT IN ('approved', 'rejected', 'inactive') OR reviewed_at IS NOT NULL", name='ck_venue_approval_requests_reviewed_status_requires_reviewed_at'),
        sa.ForeignKeyConstraint(['reviewed_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['submitted_by_user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['venue_id'], ['venues.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_venue_approval_requests_created_at', 'venue_approval_requests', ['created_at'], unique=False)
    op.create_index('ix_venue_approval_requests_request_status', 'venue_approval_requests', ['request_status'], unique=False)
    op.create_index('ix_venue_approval_requests_request_status_created_at', 'venue_approval_requests', ['request_status', 'created_at'], unique=False)
    op.create_index('ix_venue_approval_requests_reviewed_by_user_id', 'venue_approval_requests', ['reviewed_by_user_id'], unique=False)
    op.create_index('ix_venue_approval_requests_submitted_by_user_id', 'venue_approval_requests', ['submitted_by_user_id'], unique=False)
    op.create_index('ix_venue_approval_requests_submitted_by_user_id_created_at', 'venue_approval_requests', ['submitted_by_user_id', 'created_at'], unique=False)
    op.create_index('ix_venue_approval_requests_venue_id', 'venue_approval_requests', ['venue_id'], unique=False)


def downgrade() -> None:
    op.drop_table('venue_approval_requests')
