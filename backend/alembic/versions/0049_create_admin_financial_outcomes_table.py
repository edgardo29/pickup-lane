"""create admin_financial_outcomes table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0049_admin_financial_outcomes'
down_revision = '0048_refunds'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'admin_financial_outcomes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('target_game_id', postgresql.UUID(as_uuid=True)),
        sa.Column('target_sub_post_id', postgresql.UUID(as_uuid=True)),
        sa.Column('host_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('host_publish_fee_id', postgresql.UUID(as_uuid=True)),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True)),
        sa.Column('refund_id', postgresql.UUID(as_uuid=True)),
        sa.Column('host_publish_entitlement_id', postgresql.UUID(as_uuid=True)),
        sa.Column('admin_action_id', postgresql.UUID(as_uuid=True)),
        sa.Column('review_case_id', postgresql.UUID(as_uuid=True)),
        sa.Column('outcome', sa.String(length=40), nullable=False),
        sa.Column('applied_status', sa.String(length=30), nullable=False),
        sa.Column('amount_cents', sa.Integer(), nullable=False),
        sa.Column('currency', sa.CHAR(length=3), nullable=False, server_default=sa.text("'USD'")),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('internal_note', sa.Text()),
        sa.Column('failure_reason', sa.Text()),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('applied_by_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('applied_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint('amount_cents >= 0', name='ck_admin_financial_outcomes_amount_cents'),
        sa.CheckConstraint("applied_status IN ('pending', 'applied', 'failed', 'not_applicable')", name='ck_admin_financial_outcomes_applied_status'),
        sa.CheckConstraint("currency = 'USD'", name='ck_admin_financial_outcomes_currency'),
        sa.CheckConstraint("outcome IN ('no_fee_charged', 'refund', 'credit', 'forfeit', 'manual_review')", name='ck_admin_financial_outcomes_outcome'),
        sa.CheckConstraint('host_user_id IS NOT NULL AND (target_game_id IS NOT NULL OR target_sub_post_id IS NOT NULL OR host_publish_fee_id IS NOT NULL OR payment_id IS NOT NULL)', name='ck_admin_financial_outcomes_target_required'),
        sa.CheckConstraint("applied_status NOT IN ('applied', 'failed') OR applied_at IS NOT NULL", name='ck_admin_financial_outcomes_terminal_requires_applied_at'),
        sa.ForeignKeyConstraint(['admin_action_id'], ['admin_actions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['applied_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['host_publish_entitlement_id'], ['host_publish_entitlements.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['host_publish_fee_id'], ['host_publish_fees.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['host_user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['refund_id'], ['refunds.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_game_id'], ['games.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_sub_post_id'], ['sub_posts.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_admin_financial_outcomes_admin_action_id', 'admin_financial_outcomes', ['admin_action_id'], unique=False)
    op.create_index('ix_admin_financial_outcomes_applied_status', 'admin_financial_outcomes', ['applied_status'], unique=False)
    op.create_index('ix_admin_financial_outcomes_created_by_user_id', 'admin_financial_outcomes', ['created_by_user_id'], unique=False)
    op.create_index('ix_admin_financial_outcomes_entitlement_id', 'admin_financial_outcomes', ['host_publish_entitlement_id'], unique=False)
    op.create_index('ix_admin_financial_outcomes_host_publish_fee_id', 'admin_financial_outcomes', ['host_publish_fee_id'], unique=False)
    op.create_index('ix_admin_financial_outcomes_host_user_id', 'admin_financial_outcomes', ['host_user_id'], unique=False)
    op.create_index('ix_admin_financial_outcomes_outcome', 'admin_financial_outcomes', ['outcome'], unique=False)
    op.create_index('ix_admin_financial_outcomes_payment_id', 'admin_financial_outcomes', ['payment_id'], unique=False)
    op.create_index('ix_admin_financial_outcomes_refund_id', 'admin_financial_outcomes', ['refund_id'], unique=False)
    op.create_index('ix_admin_financial_outcomes_review_case_id', 'admin_financial_outcomes', ['review_case_id'], unique=False)
    op.create_index('ix_admin_financial_outcomes_target_game_id', 'admin_financial_outcomes', ['target_game_id'], unique=False)
    op.create_index('ix_admin_financial_outcomes_target_sub_post_id', 'admin_financial_outcomes', ['target_sub_post_id'], unique=False)
    op.create_index('uq_admin_financial_outcomes_active_fee_decision', 'admin_financial_outcomes', ['host_publish_fee_id'], unique=True, postgresql_where=sa.text("host_publish_fee_id IS NOT NULL AND applied_status IN ('pending', 'applied', 'not_applicable')"))
    op.create_index('uq_admin_financial_outcomes_active_game_no_fee_decision', 'admin_financial_outcomes', ['host_user_id', 'target_game_id'], unique=True, postgresql_where=sa.text("target_game_id IS NOT NULL AND host_publish_fee_id IS NULL AND applied_status IN ('pending', 'applied', 'not_applicable')"))


def downgrade() -> None:
    op.drop_table('admin_financial_outcomes')
