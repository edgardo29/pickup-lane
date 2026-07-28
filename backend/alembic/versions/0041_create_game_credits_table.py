"""create game_credits table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0041_game_credits'
down_revision = '0040_game_chat_reads'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'game_credits',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('amount_cents', sa.Integer(), nullable=False),
        sa.Column('available_cents', sa.Integer(), nullable=False),
        sa.Column('currency', sa.CHAR(length=3), nullable=False, server_default=sa.text("'USD'")),
        sa.Column('credit_status', sa.String(length=30), nullable=False, server_default=sa.text("'active'")),
        sa.Column('credit_reason', sa.String(length=40), nullable=False),
        sa.Column('source_game_id', postgresql.UUID(as_uuid=True)),
        sa.Column('source_booking_id', postgresql.UUID(as_uuid=True)),
        sa.Column('source_payment_id', postgresql.UUID(as_uuid=True)),
        sa.Column('issued_by_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('reversed_by_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('idempotency_key', sa.String(length=255), nullable=False),
        sa.Column('note', sa.Text()),
        sa.Column('reversed_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint('amount_cents > 0', name='ck_game_credits_amount_cents'),
        sa.CheckConstraint('available_cents >= 0', name='ck_game_credits_available_cents_non_negative'),
        sa.CheckConstraint('available_cents <= amount_cents', name='ck_game_credits_available_not_above_amount'),
        sa.CheckConstraint("credit_reason IN ('official_game_cancelled', 'weather_cancelled', 'player_cancelled_on_time', 'admin_credit', 'support_adjustment')", name='ck_game_credits_credit_reason'),
        sa.CheckConstraint("credit_status IN ('active', 'used', 'reversed')", name='ck_game_credits_credit_status'),
        sa.CheckConstraint("currency = 'USD'", name='ck_game_credits_currency'),
        sa.CheckConstraint("((credit_status = 'reversed') AND reversed_by_user_id IS NOT NULL AND reversed_at IS NOT NULL) OR ((credit_status <> 'reversed') AND reversed_by_user_id IS NULL AND reversed_at IS NULL)", name='ck_game_credits_reversal_fields_match_status'),
        sa.CheckConstraint("(credit_status <> 'reversed' OR available_cents = 0)", name='ck_game_credits_reversed_has_no_available'),
        sa.ForeignKeyConstraint(['issued_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reversed_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['source_booking_id'], ['bookings.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['source_game_id'], ['games.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['source_payment_id'], ['payments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('idempotency_key', name='uq_game_credits_idempotency_key')
    )
    op.create_index('ix_game_credits_created_at', 'game_credits', ['created_at'], unique=False)
    op.create_index('ix_game_credits_credit_reason_created', 'game_credits', ['credit_reason', 'created_at', 'id'], unique=False)
    op.create_index('ix_game_credits_credit_status_created', 'game_credits', ['credit_status', 'created_at', 'id'], unique=False)
    op.create_index('ix_game_credits_source_booking_id', 'game_credits', ['source_booking_id'], unique=False)
    op.create_index('ix_game_credits_source_game_id', 'game_credits', ['source_game_id'], unique=False)
    op.create_index('ix_game_credits_source_payment_id', 'game_credits', ['source_payment_id'], unique=False)
    op.create_index('ix_game_credits_user_created', 'game_credits', ['user_id', 'created_at', 'id'], unique=False)
    op.create_index('ix_game_credits_user_id_credit_status', 'game_credits', ['user_id', 'credit_status'], unique=False)


def downgrade() -> None:
    op.drop_table('game_credits')
