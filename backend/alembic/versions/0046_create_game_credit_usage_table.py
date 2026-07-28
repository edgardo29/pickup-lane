"""create game_credit_usage table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0046_game_credit_usage'
down_revision = '0045_admin_rejected_attempts'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'game_credit_usage',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('game_credit_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('booking_id', postgresql.UUID(as_uuid=True)),
        sa.Column('game_id', postgresql.UUID(as_uuid=True)),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True)),
        sa.Column('original_usage_id', postgresql.UUID(as_uuid=True)),
        sa.Column('amount_cents', sa.Integer(), nullable=False),
        sa.Column('currency', sa.CHAR(length=3), nullable=False, server_default=sa.text("'USD'")),
        sa.Column('usage_type', sa.String(length=30), nullable=False),
        sa.Column('usage_status', sa.String(length=30), nullable=False),
        sa.Column('idempotency_key', sa.String(length=255), nullable=False),
        sa.Column('reason_code', sa.String(length=80)),
        sa.Column('reserved_at', sa.DateTime(timezone=True)),
        sa.Column('redeemed_at', sa.DateTime(timezone=True)),
        sa.Column('released_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint('amount_cents > 0', name='ck_game_credit_usage_amount_cents'),
        sa.CheckConstraint("currency = 'USD'", name='ck_game_credit_usage_currency'),
        sa.CheckConstraint("(usage_type <> 'redeem' OR booking_id IS NOT NULL)", name='ck_game_credit_usage_redeem_requires_booking'),
        sa.CheckConstraint("(usage_status <> 'redeemed' OR redeemed_at IS NOT NULL)", name='ck_game_credit_usage_redeemed_requires_redeemed_at'),
        sa.CheckConstraint("(usage_status <> 'released' OR released_at IS NOT NULL)", name='ck_game_credit_usage_released_requires_released_at'),
        sa.CheckConstraint("(usage_status <> 'reserved' OR reserved_at IS NOT NULL)", name='ck_game_credit_usage_reserved_requires_reserved_at'),
        sa.CheckConstraint("(usage_type <> 'restore' OR original_usage_id IS NOT NULL)", name='ck_game_credit_usage_restore_requires_original_usage'),
        sa.CheckConstraint("((usage_type = 'redeem' AND usage_status IN ('reserved', 'redeemed', 'released')) OR (usage_type = 'reverse' AND usage_status = 'reversed') OR (usage_type = 'restore' AND usage_status = 'restored'))", name='ck_game_credit_usage_type_status_match'),
        sa.CheckConstraint("usage_status IN ('reserved', 'redeemed', 'released', 'reversed', 'restored')", name='ck_game_credit_usage_usage_status'),
        sa.CheckConstraint("usage_type IN ('redeem', 'reverse', 'restore')", name='ck_game_credit_usage_usage_type'),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['game_credit_id'], ['game_credits.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['original_usage_id'], ['game_credit_usage.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('idempotency_key', name='uq_game_credit_usage_idempotency_key')
    )
    op.create_index('ix_game_credit_usage_booking_id', 'game_credit_usage', ['booking_id'], unique=False)
    op.create_index('ix_game_credit_usage_created_at', 'game_credit_usage', ['created_at'], unique=False)
    op.create_index('ix_game_credit_usage_credit_created', 'game_credit_usage', ['game_credit_id', 'created_at', 'id'], unique=False)
    op.create_index('ix_game_credit_usage_credit_status', 'game_credit_usage', ['game_credit_id', 'usage_status'], unique=False)
    op.create_index('ix_game_credit_usage_game_credit_id', 'game_credit_usage', ['game_credit_id'], unique=False)
    op.create_index('ix_game_credit_usage_game_id', 'game_credit_usage', ['game_id'], unique=False)
    op.create_index('ix_game_credit_usage_original_usage_id', 'game_credit_usage', ['original_usage_id'], unique=False)
    op.create_index('ix_game_credit_usage_payment_id', 'game_credit_usage', ['payment_id'], unique=False)
    op.create_index('ix_game_credit_usage_usage_status', 'game_credit_usage', ['usage_status'], unique=False)
    op.create_index('ix_game_credit_usage_usage_type', 'game_credit_usage', ['usage_type'], unique=False)
    op.create_index('uq_game_credit_usage_one_restore_per_original', 'game_credit_usage', ['original_usage_id'], unique=True, postgresql_where=sa.text("usage_type = 'restore' AND usage_status = 'restored' AND original_usage_id IS NOT NULL"))


def downgrade() -> None:
    op.drop_table('game_credit_usage')
