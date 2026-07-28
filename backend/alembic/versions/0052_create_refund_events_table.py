"""create refund_events table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0052_refund_events'
down_revision = '0051_notifications'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'refund_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('refund_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(length=40), nullable=False),
        sa.Column('event_source', sa.String(length=30), nullable=False),
        sa.Column('actor_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('admin_action_id', postgresql.UUID(as_uuid=True)),
        sa.Column('idempotency_key', sa.String(length=255)),
        sa.Column('provider', sa.String(length=20)),
        sa.Column('provider_event_id', sa.String(length=255)),
        sa.Column('provider_refund_id', sa.String(length=255)),
        sa.Column('provider_charge_id', sa.String(length=255)),
        sa.Column('provider_status', sa.String(length=30)),
        sa.Column('previous_refund_status', sa.String(length=30)),
        sa.Column('new_refund_status', sa.String(length=30)),
        sa.Column('reason_code', sa.String(length=80)),
        sa.Column('summary', sa.Text()),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("event_source IN ('system', 'webhook', 'reconciliation', 'admin')", name='ck_refund_events_event_source'),
        sa.CheckConstraint("event_type IN ('provider_result_recorded', 'reconciliation_checked', 'local_status_changed', 'provider_outcome_unknown')", name='ck_refund_events_event_type'),
        sa.CheckConstraint("(provider IS NULL OR provider IN ('stripe'))", name='ck_refund_events_provider'),
        sa.CheckConstraint("provider_status IS NULL OR provider_status IN ('processing', 'succeeded', 'failed', 'cancelled', 'unknown')", name='ck_refund_events_provider_status'),
        sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['admin_action_id'], ['admin_actions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['refund_id'], ['refunds.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_refund_events_provider_charge_id', 'refund_events', ['provider_charge_id'], unique=False)
    op.create_index('ix_refund_events_provider_refund_id', 'refund_events', ['provider_refund_id'], unique=False)
    op.create_index('ix_refund_events_refund_id', 'refund_events', ['refund_id'], unique=False)
    op.create_index('ix_refund_events_refund_id_occurred_id', 'refund_events', ['refund_id', 'occurred_at', 'id'], unique=False)
    op.create_index('uq_refund_events_idempotency_key', 'refund_events', ['idempotency_key'], unique=True, postgresql_where=sa.text('idempotency_key IS NOT NULL'))
    op.create_index('uq_refund_events_provider_event_id', 'refund_events', ['provider', 'provider_event_id'], unique=True, postgresql_where=sa.text('provider_event_id IS NOT NULL'))


def downgrade() -> None:
    op.drop_table('refund_events')
