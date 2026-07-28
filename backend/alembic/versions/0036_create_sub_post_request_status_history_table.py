"""create sub_post_request_status_history table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0036_sub_post_req_status_hist'
down_revision = '0035_sub_post_chat_reads'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'sub_post_request_status_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('sub_post_request_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('old_status', sa.String(length=30)),
        sa.Column('new_status', sa.String(length=30), nullable=False),
        sa.Column('changed_by_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('change_source', sa.String(length=30), nullable=False),
        sa.Column('change_reason', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("change_source IN ('requester', 'owner', 'admin', 'system', 'scheduled_job')", name='ck_sub_post_request_status_history_change_source'),
        sa.CheckConstraint("new_status IN ('pending', 'confirmed', 'declined', 'sub_waitlist', 'canceled_by_player', 'canceled_by_owner', 'no_show_reported', 'expired', 'closed_by_admin')", name='ck_sub_post_request_status_history_new_status'),
        sa.CheckConstraint("old_status IS NULL OR old_status IN ('pending', 'confirmed', 'declined', 'sub_waitlist', 'canceled_by_player', 'canceled_by_owner', 'no_show_reported', 'expired', 'closed_by_admin')", name='ck_sub_post_request_status_history_old_status'),
        sa.ForeignKeyConstraint(['changed_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['sub_post_request_id'], ['sub_post_requests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sub_post_request_status_history_changed_by_user_id', 'sub_post_request_status_history', ['changed_by_user_id'], unique=False)
    op.create_index('ix_sub_post_request_status_history_request_created', 'sub_post_request_status_history', ['sub_post_request_id', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('sub_post_request_status_history')
