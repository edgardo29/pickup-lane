"""create admin_review_signals table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0058_admin_review_signals'
down_revision = '0057_admin_review_case_notes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'admin_review_signals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('review_case_id', postgresql.UUID(as_uuid=True)),
        sa.Column('signal_category', sa.String(length=60), nullable=False),
        sa.Column('source', sa.String(length=60), nullable=False),
        sa.Column('signal_status', sa.String(length=30), nullable=False, server_default=sa.text("'open'")),
        sa.Column('priority', sa.String(length=30), nullable=False, server_default=sa.text("'attention'")),
        sa.Column('title', sa.String(length=180), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('target_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('target_game_id', postgresql.UUID(as_uuid=True)),
        sa.Column('target_sub_post_id', postgresql.UUID(as_uuid=True)),
        sa.Column('target_sub_post_request_id', postgresql.UUID(as_uuid=True)),
        sa.Column('target_payment_id', postgresql.UUID(as_uuid=True)),
        sa.Column('target_financial_outcome_id', postgresql.UUID(as_uuid=True)),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('idempotency_key', sa.String(length=160)),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("priority IN ('attention', 'urgent', 'critical')", name='ck_admin_review_signals_priority'),
        sa.CheckConstraint("signal_category IN ('chat_moderation')", name='ck_admin_review_signals_signal_category'),
        sa.CheckConstraint("signal_status IN ('open', 'attached', 'dismissed')", name='ck_admin_review_signals_signal_status'),
        sa.CheckConstraint("source IN ('chat_moderation')", name='ck_admin_review_signals_source'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['review_case_id'], ['admin_review_cases.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_financial_outcome_id'], ['admin_financial_outcomes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_game_id'], ['games.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_payment_id'], ['payments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_sub_post_id'], ['sub_posts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_sub_post_request_id'], ['sub_post_requests.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_admin_review_signals_created_at', 'admin_review_signals', ['created_at'], unique=False)
    op.create_index('ix_admin_review_signals_priority', 'admin_review_signals', ['priority'], unique=False)
    op.create_index('ix_admin_review_signals_review_case_id', 'admin_review_signals', ['review_case_id'], unique=False)
    op.create_index('ix_admin_review_signals_signal_category', 'admin_review_signals', ['signal_category'], unique=False)
    op.create_index('ix_admin_review_signals_signal_status', 'admin_review_signals', ['signal_status'], unique=False)
    op.create_index('ix_admin_review_signals_target_financial_outcome_id', 'admin_review_signals', ['target_financial_outcome_id'], unique=False)
    op.create_index('ix_admin_review_signals_target_game_id', 'admin_review_signals', ['target_game_id'], unique=False)
    op.create_index('ix_admin_review_signals_target_payment_id', 'admin_review_signals', ['target_payment_id'], unique=False)
    op.create_index('ix_admin_review_signals_target_sub_post_id', 'admin_review_signals', ['target_sub_post_id'], unique=False)
    op.create_index('ix_admin_review_signals_target_sub_post_request_id', 'admin_review_signals', ['target_sub_post_request_id'], unique=False)
    op.create_index('ix_admin_review_signals_target_user_id', 'admin_review_signals', ['target_user_id'], unique=False)
    op.create_index('uq_admin_review_signals_source_idempotency_key', 'admin_review_signals', ['source', 'idempotency_key'], unique=True, postgresql_where=sa.text('idempotency_key IS NOT NULL'))


def downgrade() -> None:
    op.drop_table('admin_review_signals')
