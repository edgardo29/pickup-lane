"""create community_publish_attempts table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0038_community_publish_attempts'
down_revision = '0037_waitlist_entries'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'community_publish_attempts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('host_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('payment_id', postgresql.UUID(as_uuid=True)),
        sa.Column('created_game_id', postgresql.UUID(as_uuid=True)),
        sa.Column('attempt_status', sa.String(length=30), nullable=False),
        sa.Column('publish_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('payment_method_id', postgresql.UUID(as_uuid=True)),
        sa.Column('starts_on_local', sa.Date(), nullable=False),
        sa.Column('amount_cents', sa.Integer(), nullable=False),
        sa.Column('currency', sa.CHAR(length=3), nullable=False, server_default=sa.text("'USD'")),
        sa.Column('failure_code', sa.String(length=100)),
        sa.Column('failure_message', sa.Text()),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint('amount_cents >= 0', name='ck_community_publish_attempts_amount_cents'),
        sa.CheckConstraint("currency = 'USD'", name='ck_community_publish_attempts_currency'),
        sa.CheckConstraint("jsonb_typeof(publish_payload) = 'object'", name='ck_community_publish_attempts_payload_object'),
        sa.CheckConstraint("attempt_status IN ('requires_payment_method', 'requires_action', 'processing', 'succeeded', 'failed', 'cancelled', 'expired')", name='ck_community_publish_attempts_status'),
        sa.CheckConstraint("(attempt_status <> 'succeeded' OR created_game_id IS NOT NULL)", name='ck_community_publish_attempts_succeeded_requires_game'),
        sa.ForeignKeyConstraint(['created_game_id'], ['games.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['host_user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['payment_method_id'], ['user_payment_methods.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('created_game_id', name='uq_community_publish_attempts_created_game_id'),
        sa.UniqueConstraint('payment_id', name='uq_community_publish_attempts_payment_id')
    )
    op.create_index('ix_community_publish_attempts_attempt_status', 'community_publish_attempts', ['attempt_status'], unique=False)
    op.create_index('ix_community_publish_attempts_created_game_id', 'community_publish_attempts', ['created_game_id'], unique=False)
    op.create_index('ix_community_publish_attempts_host_date', 'community_publish_attempts', ['host_user_id', 'starts_on_local'], unique=False)
    op.create_index('ix_community_publish_attempts_host_user_id', 'community_publish_attempts', ['host_user_id'], unique=False)
    op.create_index('ix_community_publish_attempts_payment_id', 'community_publish_attempts', ['payment_id'], unique=False)
    op.create_index('ux_community_publish_attempts_one_active_paid_per_host_date', 'community_publish_attempts', ['host_user_id', 'starts_on_local'], unique=True, postgresql_where=sa.text("attempt_status IN ('requires_payment_method', 'requires_action', 'processing')"))


def downgrade() -> None:
    op.drop_table('community_publish_attempts')
