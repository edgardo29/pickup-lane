"""create booking_status_history table"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = '0030_booking_status_history'
down_revision = '0029_booking_policy_acceptances'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'booking_status_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('booking_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('old_booking_status', sa.String(length=30)),
        sa.Column('new_booking_status', sa.String(length=30), nullable=False),
        sa.Column('old_payment_status', sa.String(length=30)),
        sa.Column('new_payment_status', sa.String(length=30)),
        sa.Column('old_reservation_status', sa.String(length=30)),
        sa.Column('new_reservation_status', sa.String(length=30), nullable=False),
        sa.Column('changed_by_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('change_source', sa.String(length=30), nullable=False, server_default=sa.text("'system'")),
        sa.Column('change_reason', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("change_source IN ('user', 'host', 'admin', 'system', 'payment_webhook', 'scheduled_job')", name='ck_booking_status_history_change_source'),
        sa.CheckConstraint("new_booking_status IN ('pending_payment', 'confirmed', 'waitlisted', 'partially_cancelled', 'cancelled', 'expired', 'failed', 'capacity_conflict')", name='ck_booking_status_history_new_booking_status'),
        sa.CheckConstraint("(new_payment_status IS NULL OR new_payment_status IN ('not_required', 'unpaid', 'requires_action', 'processing', 'paid', 'failed', 'partially_refunded', 'refunded', 'credit_restored', 'disputed'))", name='ck_booking_status_history_new_payment_status'),
        sa.CheckConstraint("(old_booking_status IS NULL OR old_booking_status IN ('pending_payment', 'confirmed', 'waitlisted', 'partially_cancelled', 'cancelled', 'expired', 'failed', 'capacity_conflict'))", name='ck_booking_status_history_old_booking_status'),
        sa.CheckConstraint("(old_payment_status IS NULL OR old_payment_status IN ('not_required', 'unpaid', 'requires_action', 'processing', 'paid', 'failed', 'partially_refunded', 'refunded', 'credit_restored', 'disputed'))", name='ck_booking_status_history_old_payment_status'),
        sa.CheckConstraint("(old_reservation_status IS NULL OR old_reservation_status IN ('not_required', 'held', 'confirmed', 'released', 'capacity_conflict'))", name='ck_booking_status_history_old_reservation_status'),
        sa.CheckConstraint("new_reservation_status IN ('not_required', 'held', 'confirmed', 'released', 'capacity_conflict')", name='ck_booking_status_history_new_reservation_status'),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['changed_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_booking_status_history_booking_id', 'booking_status_history', ['booking_id'], unique=False)
    op.create_index('ix_booking_status_history_booking_id_created_at', 'booking_status_history', ['booking_id', 'created_at'], unique=False)
    op.create_index('ix_booking_status_history_change_source', 'booking_status_history', ['change_source'], unique=False)
    op.create_index('ix_booking_status_history_changed_by_user_id', 'booking_status_history', ['changed_by_user_id'], unique=False)
    op.create_index('ix_booking_status_history_created_at', 'booking_status_history', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('booking_status_history')
