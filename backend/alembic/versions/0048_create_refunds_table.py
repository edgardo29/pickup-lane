"""create refunds table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0048_refunds'
down_revision = '0047_host_publish_entitlements'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'refunds',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('booking_id', postgresql.UUID(as_uuid=True)),
        sa.Column('participant_id', postgresql.UUID(as_uuid=True)),
        sa.Column('host_publish_fee_id', postgresql.UUID(as_uuid=True)),
        sa.Column('provider_refund_id', sa.String(length=255)),
        sa.Column('origin_workflow', sa.String(length=80), nullable=False, server_default=sa.text("'direct_admin_refund'")),
        sa.Column('provider', sa.String(length=20), nullable=False, server_default=sa.text("'stripe'")),
        sa.Column('provider_status', sa.String(length=30)),
        sa.Column('provider_status_observed_at', sa.DateTime(timezone=True)),
        sa.Column('provider_charge_id', sa.String(length=255)),
        sa.Column('last_refund_event_at', sa.DateTime(timezone=True)),
        sa.Column('amount_cents', sa.Integer(), nullable=False),
        sa.Column('currency', sa.CHAR(length=3), nullable=False, server_default=sa.text("'USD'")),
        sa.Column('refund_reason', sa.String(length=40), nullable=False),
        sa.Column('refund_status', sa.String(length=30), nullable=False, server_default=sa.text("'pending'")),
        sa.Column('requested_by_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('approved_by_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('requested_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('approved_at', sa.DateTime(timezone=True)),
        sa.Column('refunded_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint('amount_cents > 0', name='ck_refunds_amount_cents'),
        sa.CheckConstraint("(refund_status <> 'approved' OR approved_at IS NOT NULL)", name='ck_refunds_approved_requires_approved_at'),
        sa.CheckConstraint("currency = 'USD'", name='ck_refunds_currency'),
        sa.CheckConstraint("origin_workflow IN ('player_removal', 'official_game_cancellation', 'community_publish_fee_refund', 'direct_admin_refund', 'official_game_checkout', 'pending_checkout_expiration', 'pending_checkout_cancellation', 'admin_game_update')", name='ck_refunds_origin_workflow'),
        sa.CheckConstraint("provider IN ('stripe')", name='ck_refunds_provider'),
        sa.CheckConstraint("provider_status IS NULL OR provider_status IN ('processing', 'succeeded', 'failed', 'cancelled', 'unknown')", name='ck_refunds_provider_status'),
        sa.CheckConstraint("refund_reason IN ('player_cancelled', 'late_cancel', 'host_cancelled', 'game_cancelled', 'weather', 'admin_refund', 'duplicate_payment', 'dispute_resolution', 'publish_fee_refund')", name='ck_refunds_refund_reason'),
        sa.CheckConstraint("refund_status IN ('pending', 'approved', 'processing', 'succeeded', 'failed', 'cancelled')", name='ck_refunds_refund_status'),
        sa.CheckConstraint("(refund_status <> 'succeeded' OR refunded_at IS NOT NULL)", name='ck_refunds_succeeded_requires_refunded_at'),
        sa.CheckConstraint('booking_id IS NOT NULL OR participant_id IS NOT NULL OR host_publish_fee_id IS NOT NULL', name='ck_refunds_target_required'),
        sa.ForeignKeyConstraint(['approved_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['host_publish_fee_id'], ['host_publish_fees.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['participant_id'], ['game_participants.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['requested_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_refunds_amount_cents_id', 'refunds', ['amount_cents', 'id'], unique=False)
    op.create_index('ix_refunds_approved_by_user_id', 'refunds', ['approved_by_user_id'], unique=False)
    op.create_index('ix_refunds_booking_id', 'refunds', ['booking_id'], unique=False)
    op.create_index('ix_refunds_host_publish_fee_id', 'refunds', ['host_publish_fee_id'], unique=False)
    op.create_index('ix_refunds_last_refund_event_at', 'refunds', ['last_refund_event_at', 'id'], unique=False)
    op.create_index('ix_refunds_origin_workflow_created', 'refunds', ['origin_workflow', 'created_at', 'id'], unique=False)
    op.create_index('ix_refunds_participant_id', 'refunds', ['participant_id'], unique=False)
    op.create_index('ix_refunds_payment_id', 'refunds', ['payment_id'], unique=False)
    op.create_index('ix_refunds_provider_charge_id', 'refunds', ['provider_charge_id'], unique=False)
    op.create_index('ix_refunds_provider_refund_id', 'refunds', ['provider_refund_id'], unique=False)
    op.create_index('ix_refunds_provider_status_created', 'refunds', ['provider_status', 'created_at', 'id'], unique=False)
    op.create_index('ix_refunds_refund_reason', 'refunds', ['refund_reason'], unique=False)
    op.create_index('ix_refunds_refund_status_created', 'refunds', ['refund_status', 'created_at', 'id'], unique=False)
    op.create_index('ix_refunds_requested_by_user_id', 'refunds', ['requested_by_user_id'], unique=False)
    op.create_index('uq_refunds_provider_refund_id', 'refunds', ['provider', 'provider_refund_id'], unique=True, postgresql_where=sa.text('provider_refund_id IS NOT NULL'))


def downgrade() -> None:
    op.drop_table('refunds')
