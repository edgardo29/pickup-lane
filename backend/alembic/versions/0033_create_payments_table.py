"""create payments table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0033_payments'
down_revision = '0032_game_participants'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('payer_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('booking_id', postgresql.UUID(as_uuid=True)),
        sa.Column('game_id', postgresql.UUID(as_uuid=True)),
        sa.Column('payment_type', sa.String(length=30), nullable=False),
        sa.Column('provider', sa.String(length=20), nullable=False, server_default=sa.text("'stripe'")),
        sa.Column('provider_payment_intent_id', sa.String(length=255)),
        sa.Column('provider_charge_id', sa.String(length=255)),
        sa.Column('idempotency_key', sa.String(length=255), nullable=False),
        sa.Column('amount_cents', sa.Integer(), nullable=False),
        sa.Column('currency', sa.CHAR(length=3), nullable=False, server_default=sa.text("'USD'")),
        sa.Column('payment_status', sa.String(length=30), nullable=False),
        sa.Column('paid_at', sa.DateTime(timezone=True)),
        sa.Column('failure_code', sa.String(length=100)),
        sa.Column('failure_message', sa.Text()),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint('amount_cents > 0', name='ck_payments_amount_cents'),
        sa.CheckConstraint("(payment_type <> 'booking' OR booking_id IS NOT NULL)", name='ck_payments_booking_requires_booking_id'),
        sa.CheckConstraint("(payment_type <> 'community_publish_fee' OR booking_id IS NULL)", name='ck_payments_community_publish_fee_no_booking'),
        sa.CheckConstraint("currency = 'USD'", name='ck_payments_currency'),
        sa.CheckConstraint("payment_status IN ('requires_payment_method', 'processing', 'requires_action', 'succeeded', 'failed', 'canceled')", name='ck_payments_payment_status'),
        sa.CheckConstraint("payment_type IN ('booking', 'community_publish_fee', 'admin_charge')", name='ck_payments_payment_type'),
        sa.CheckConstraint("provider IN ('stripe')", name='ck_payments_provider'),
        sa.CheckConstraint("(payment_status <> 'succeeded' OR paid_at IS NOT NULL)", name='ck_payments_succeeded_requires_paid_at'),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['payer_user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('idempotency_key', name='uq_payments_idempotency_key')
    )
    op.create_index('ix_payments_booking_id', 'payments', ['booking_id'], unique=False)
    op.create_index('ix_payments_game_id', 'payments', ['game_id'], unique=False)
    op.create_index('ix_payments_payer_created', 'payments', ['payer_user_id', 'created_at', 'id'], unique=False)
    op.create_index('ix_payments_payment_status_created', 'payments', ['payment_status', 'created_at', 'id'], unique=False)
    op.create_index('ix_payments_payment_type_created', 'payments', ['payment_type', 'created_at', 'id'], unique=False)
    op.create_index('ix_payments_provider_charge_id', 'payments', ['provider_charge_id'], unique=False)
    op.create_index('ix_payments_provider_payment_intent_id', 'payments', ['provider_payment_intent_id'], unique=False)
    op.create_index('uq_payments_provider_charge_id', 'payments', ['provider', 'provider_charge_id'], unique=True, postgresql_where=sa.text('provider_charge_id IS NOT NULL'))
    op.create_index('uq_payments_provider_payment_intent_id', 'payments', ['provider', 'provider_payment_intent_id'], unique=True, postgresql_where=sa.text('provider_payment_intent_id IS NOT NULL'))


def downgrade() -> None:
    op.drop_table('payments')
