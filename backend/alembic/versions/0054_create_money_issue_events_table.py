"""create money_issue_events table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0054_money_issue_events'
down_revision = '0053_admin_review_cases'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'money_issue_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('money_issue_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(length=60), nullable=False),
        sa.Column('event_source', sa.String(length=20), nullable=False),
        sa.Column('actor_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('admin_action_id', postgresql.UUID(as_uuid=True)),
        sa.Column('refund_event_id', postgresql.UUID(as_uuid=True)),
        sa.Column('result_credit_usage_id', postgresql.UUID(as_uuid=True)),
        sa.Column('previous_status', sa.String(length=20)),
        sa.Column('new_status', sa.String(length=20)),
        sa.Column('previous_issue_type', sa.String(length=80)),
        sa.Column('new_issue_type', sa.String(length=80)),
        sa.Column('previous_recommended_action_code', sa.String(length=80)),
        sa.Column('new_recommended_action_code', sa.String(length=80)),
        sa.Column('reason_code', sa.String(length=80)),
        sa.Column('summary', sa.Text()),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("event_source IN ('system', 'admin')", name='ck_money_issue_events_event_source'),
        sa.CheckConstraint("event_type IN ('issue_opened', 'issue_reopened', 'classification_changed', 'recommended_action_changed', 'admin_retry_initiated', 'refund_outcome_linked', 'credit_restore_failed', 'credit_restore_succeeded', 'credit_release_failed', 'credit_release_succeeded', 'issue_resolved')", name='ck_money_issue_events_event_type'),
        sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['admin_action_id'], ['admin_actions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['money_issue_id'], ['money_issues.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['refund_event_id'], ['refund_events.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['result_credit_usage_id'], ['game_credit_usage.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_money_issue_events_issue_occurred_id', 'money_issue_events', ['money_issue_id', 'occurred_at', 'id'], unique=False)
    op.create_index('ix_money_issue_events_money_issue_id', 'money_issue_events', ['money_issue_id'], unique=False)
    op.create_index('ix_money_issue_events_refund_event_id', 'money_issue_events', ['refund_event_id'], unique=False)
    op.create_index('ix_money_issue_events_result_credit_usage_id', 'money_issue_events', ['result_credit_usage_id'], unique=False)


def downgrade() -> None:
    op.drop_table('money_issue_events')
