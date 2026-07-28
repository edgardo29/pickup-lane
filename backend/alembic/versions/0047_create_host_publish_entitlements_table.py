"""create host_publish_entitlements table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0047_host_publish_entitlements'
down_revision = '0046_game_credit_usage'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'host_publish_entitlements',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('host_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entitlement_type', sa.String(length=40), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('source', sa.String(length=40), nullable=False),
        sa.Column('source_admin_action_id', postgresql.UUID(as_uuid=True)),
        sa.Column('source_financial_outcome_id', postgresql.UUID(as_uuid=True)),
        sa.Column('reserved_by_attempt_id', postgresql.UUID(as_uuid=True)),
        sa.Column('used_by_game_id', postgresql.UUID(as_uuid=True)),
        sa.Column('used_by_host_publish_fee_id', postgresql.UUID(as_uuid=True)),
        sa.Column('used_at', sa.DateTime(timezone=True)),
        sa.Column('revoked_at', sa.DateTime(timezone=True)),
        sa.Column('revoked_by_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('revoke_reason', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("status <> 'reserved' OR (reserved_by_attempt_id IS NOT NULL AND used_at IS NULL)", name='ck_host_publish_entitlements_reserved_requirements'),
        sa.CheckConstraint("status <> 'revoked' OR (revoked_at IS NOT NULL AND NULLIF(BTRIM(revoke_reason), '') IS NOT NULL)", name='ck_host_publish_entitlements_revoked_requirements'),
        sa.CheckConstraint("source IN ('system', 'admin', 'financial_outcome')", name='ck_host_publish_entitlements_source'),
        sa.CheckConstraint("status IN ('available', 'reserved', 'used', 'revoked', 'expired')", name='ck_host_publish_entitlements_status'),
        sa.CheckConstraint("entitlement_type IN ('first_free', 'admin_grant', 'refund_replacement', 'courtesy')", name='ck_host_publish_entitlements_type'),
        sa.CheckConstraint("status <> 'used' OR (used_by_game_id IS NOT NULL AND used_by_host_publish_fee_id IS NOT NULL AND used_at IS NOT NULL)", name='ck_host_publish_entitlements_used_requirements'),
        sa.ForeignKeyConstraint(['host_user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['reserved_by_attempt_id'], ['community_publish_attempts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['revoked_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['source_admin_action_id'], ['admin_actions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['used_by_game_id'], ['games.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['used_by_host_publish_fee_id'], ['host_publish_fees.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_host_publish_entitlements_host_status', 'host_publish_entitlements', ['host_user_id', 'status'], unique=False)
    op.create_index('ix_host_publish_entitlements_host_user_id', 'host_publish_entitlements', ['host_user_id'], unique=False)
    op.create_index('ix_host_publish_entitlements_reserved_by_attempt_id', 'host_publish_entitlements', ['reserved_by_attempt_id'], unique=False)
    op.create_index('ix_host_publish_entitlements_status', 'host_publish_entitlements', ['status'], unique=False)
    op.create_index('ix_host_publish_entitlements_used_by_fee_id', 'host_publish_entitlements', ['used_by_host_publish_fee_id'], unique=False)
    op.create_index('ix_host_publish_entitlements_used_by_game_id', 'host_publish_entitlements', ['used_by_game_id'], unique=False)
    op.create_index('ux_host_publish_entitlements_one_first_free_per_host', 'host_publish_entitlements', ['host_user_id'], unique=True, postgresql_where=sa.text("entitlement_type = 'first_free'"))


def downgrade() -> None:
    op.drop_table('host_publish_entitlements')
