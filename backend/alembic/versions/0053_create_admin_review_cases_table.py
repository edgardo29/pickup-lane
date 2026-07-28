"""create admin_review_cases table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0053_admin_review_cases'
down_revision = '0052_refund_events'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'admin_review_cases',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('case_type', sa.String(length=40), nullable=False),
        sa.Column('case_status', sa.String(length=30), nullable=False, server_default=sa.text("'open'")),
        sa.Column('case_category', sa.String(length=60), nullable=False),
        sa.Column('priority', sa.String(length=30), nullable=False, server_default=sa.text("'attention'")),
        sa.Column('title', sa.String(length=180), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('target_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('target_game_id', postgresql.UUID(as_uuid=True)),
        sa.Column('target_sub_post_id', postgresql.UUID(as_uuid=True)),
        sa.Column('target_sub_post_request_id', postgresql.UUID(as_uuid=True)),
        sa.Column('target_payment_id', postgresql.UUID(as_uuid=True)),
        sa.Column('target_financial_outcome_id', postgresql.UUID(as_uuid=True)),
        sa.Column('opened_by_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('closed_by_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('closure_outcome', sa.String(length=60)),
        sa.Column('closure_reason', sa.Text()),
        sa.Column('closed_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("case_category IN ('content_moderation', 'chat_moderation')", name='ck_admin_review_cases_case_category'),
        sa.CheckConstraint("case_status IN ('open', 'closed')", name='ck_admin_review_cases_case_status'),
        sa.CheckConstraint("case_type IN ('community_game', 'need_a_sub', 'money', 'user', 'system')", name='ck_admin_review_cases_case_type'),
        sa.CheckConstraint("closure_outcome IS NULL OR closure_outcome IN ('enforcement_applied', 'no_action_needed', 'invalid_signal')", name='ck_admin_review_cases_closure_outcome'),
        sa.CheckConstraint("(case_status = 'open' AND closed_by_user_id IS NULL AND closure_outcome IS NULL AND closure_reason IS NULL AND closed_at IS NULL) OR (case_status = 'closed' AND closure_outcome IS NOT NULL AND closure_reason IS NOT NULL AND closed_at IS NOT NULL)", name='ck_admin_review_cases_closure_state'),
        sa.CheckConstraint("priority IN ('attention', 'urgent', 'critical')", name='ck_admin_review_cases_priority'),
        sa.CheckConstraint("case_status = 'closed' OR target_user_id IS NOT NULL OR target_game_id IS NOT NULL OR target_sub_post_id IS NOT NULL OR target_sub_post_request_id IS NOT NULL OR target_payment_id IS NOT NULL OR target_financial_outcome_id IS NOT NULL", name='ck_admin_review_cases_target_required'),
        sa.ForeignKeyConstraint(['closed_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['opened_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_financial_outcome_id'], ['admin_financial_outcomes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_game_id'], ['games.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_payment_id'], ['payments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_sub_post_id'], ['sub_posts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_sub_post_request_id'], ['sub_post_requests.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_admin_review_cases_case_category', 'admin_review_cases', ['case_category'], unique=False)
    op.create_index('ix_admin_review_cases_case_status', 'admin_review_cases', ['case_status'], unique=False)
    op.create_index('ix_admin_review_cases_case_type', 'admin_review_cases', ['case_type'], unique=False)
    op.create_index('ix_admin_review_cases_closed_at', 'admin_review_cases', ['closed_at'], unique=False)
    op.create_index('ix_admin_review_cases_created_at', 'admin_review_cases', ['created_at'], unique=False)
    op.create_index('ix_admin_review_cases_priority', 'admin_review_cases', ['priority'], unique=False)
    op.create_index('ix_admin_review_cases_status_updated_id', 'admin_review_cases', ['case_status', 'updated_at', 'id'], unique=False)
    op.create_index('ix_admin_review_cases_target_financial_outcome_id', 'admin_review_cases', ['target_financial_outcome_id'], unique=False)
    op.create_index('ix_admin_review_cases_target_game_id', 'admin_review_cases', ['target_game_id'], unique=False)
    op.create_index('ix_admin_review_cases_target_payment_id', 'admin_review_cases', ['target_payment_id'], unique=False)
    op.create_index('ix_admin_review_cases_target_sub_post_id', 'admin_review_cases', ['target_sub_post_id'], unique=False)
    op.create_index('ix_admin_review_cases_target_sub_post_request_id', 'admin_review_cases', ['target_sub_post_request_id'], unique=False)
    op.create_index('ix_admin_review_cases_target_user_id', 'admin_review_cases', ['target_user_id'], unique=False)
    op.create_index('uq_admin_review_cases_open_community_game_content_moderation', 'admin_review_cases', ['target_game_id'], unique=True, postgresql_where=sa.text("target_game_id IS NOT NULL AND case_type = 'community_game' AND case_category = 'content_moderation' AND case_status = 'open'"))
    op.create_index('uq_admin_review_cases_open_need_sub_content_moderation', 'admin_review_cases', ['target_sub_post_id'], unique=True, postgresql_where=sa.text("target_sub_post_id IS NOT NULL AND case_type = 'need_a_sub' AND case_category = 'content_moderation' AND case_status = 'open'"))


def downgrade() -> None:
    op.drop_table('admin_review_cases')
