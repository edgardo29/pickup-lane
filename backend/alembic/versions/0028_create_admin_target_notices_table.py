"""create admin_target_notices table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0028_admin_target_notices'
down_revision = '0027_sub_post_requests'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'admin_target_notices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('recipient_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('target_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('target_game_id', postgresql.UUID(as_uuid=True)),
        sa.Column('target_sub_post_id', postgresql.UUID(as_uuid=True)),
        sa.Column('target_sub_post_request_id', postgresql.UUID(as_uuid=True)),
        sa.Column('admin_action_id', postgresql.UUID(as_uuid=True)),
        sa.Column('notice_type', sa.String(length=60), nullable=False),
        sa.Column('notice_status', sa.String(length=20), nullable=False, server_default=sa.text("'active'")),
        sa.Column('title', sa.String(length=160), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('user_safe_reason', sa.Text()),
        sa.Column('notice_metadata', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('read_at', sa.DateTime(timezone=True)),
        sa.Column('dismissed_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("notice_status IN ('active', 'dismissed')", name='ck_admin_target_notices_notice_status'),
        sa.CheckConstraint("notice_type IN ('community_game_hidden', 'community_game_restored', 'community_game_joining_paused', 'community_game_joining_resumed', 'community_game_payment_info_hidden', 'community_game_payment_info_restored', 'community_game_cancelled', 'need_sub_post_hidden', 'need_sub_post_restored', 'need_sub_post_removed', 'publish_fee_refunded', 'publish_credit_added')", name='ck_admin_target_notices_notice_type'),
        sa.CheckConstraint('target_game_id IS NOT NULL OR target_sub_post_id IS NOT NULL OR target_sub_post_request_id IS NOT NULL OR target_user_id IS NOT NULL', name='ck_admin_target_notices_target_required'),
        sa.ForeignKeyConstraint(['admin_action_id'], ['admin_actions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['recipient_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_game_id'], ['games.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_sub_post_id'], ['sub_posts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_sub_post_request_id'], ['sub_post_requests.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_admin_target_notices_admin_action_id', 'admin_target_notices', ['admin_action_id'], unique=False)
    op.create_index('ix_admin_target_notices_created_at', 'admin_target_notices', ['created_at'], unique=False)
    op.create_index('ix_admin_target_notices_notice_type', 'admin_target_notices', ['notice_type'], unique=False)
    op.create_index('ix_admin_target_notices_recipient_user_id', 'admin_target_notices', ['recipient_user_id'], unique=False)
    op.create_index('ix_admin_target_notices_target_game_id', 'admin_target_notices', ['target_game_id'], unique=False)
    op.create_index('ix_admin_target_notices_target_sub_post_id', 'admin_target_notices', ['target_sub_post_id'], unique=False)
    op.create_index('ix_admin_target_notices_target_sub_post_request_id', 'admin_target_notices', ['target_sub_post_request_id'], unique=False)
    op.create_index('ix_admin_target_notices_target_user_id', 'admin_target_notices', ['target_user_id'], unique=False)


def downgrade() -> None:
    op.drop_table('admin_target_notices')
