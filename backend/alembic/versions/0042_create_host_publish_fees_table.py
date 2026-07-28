"""create host_publish_fees table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0042_host_publish_fees'
down_revision = '0041_game_credits'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'host_publish_fees',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('game_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('host_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True)),
        sa.Column('amount_cents', sa.Integer(), nullable=False),
        sa.Column('currency', sa.CHAR(length=3), nullable=False, server_default=sa.text("'USD'")),
        sa.Column('fee_status', sa.String(length=30), nullable=False),
        sa.Column('waiver_reason', sa.String(length=30), nullable=False, server_default=sa.text("'none'")),
        sa.Column('paid_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint('amount_cents >= 0', name='ck_host_publish_fees_amount_cents'),
        sa.CheckConstraint("currency = 'USD'", name='ck_host_publish_fees_currency'),
        sa.CheckConstraint("fee_status IN ('pending', 'paid', 'waived', 'failed', 'refunded')", name='ck_host_publish_fees_fee_status'),
        sa.CheckConstraint("fee_status <> 'paid' OR (payment_id IS NOT NULL AND paid_at IS NOT NULL AND amount_cents > 0)", name='ck_host_publish_fees_paid_requires_payment'),
        sa.CheckConstraint("fee_status <> 'waived' OR (amount_cents = 0 AND waiver_reason <> 'none' AND payment_id IS NULL)", name='ck_host_publish_fees_waived_requirements'),
        sa.CheckConstraint("waiver_reason IN ('none', 'first_game_free', 'admin_comp')", name='ck_host_publish_fees_waiver_reason'),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['host_user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('game_id', name='uq_host_publish_fees_game_id'),
        sa.UniqueConstraint('payment_id', name='uq_host_publish_fees_payment_id')
    )
    op.create_index('ix_host_publish_fees_fee_status', 'host_publish_fees', ['fee_status'], unique=False)
    op.create_index('ix_host_publish_fees_game_id', 'host_publish_fees', ['game_id'], unique=False)
    op.create_index('ix_host_publish_fees_host_user_id', 'host_publish_fees', ['host_user_id'], unique=False)
    op.create_index('ix_host_publish_fees_payment_id', 'host_publish_fees', ['payment_id'], unique=False)


def downgrade() -> None:
    op.drop_table('host_publish_fees')
