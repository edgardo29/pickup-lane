"""create platform_notices table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0006_platform_notices'
down_revision = '0005_platform_seen_states'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE platform_notice_global_sequence_seq")
    op.create_table(
        'platform_notices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('audience_type', sa.String(length=30), nullable=False),
        sa.Column('global_sequence', sa.BigInteger()),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by_admin_id', postgresql.UUID(as_uuid=True)),
        sa.Column('idempotency_key_hash', sa.String(length=64), nullable=False),
        sa.Column('request_fingerprint', sa.String(length=64), nullable=False),
        sa.Column('cancelled_at', sa.DateTime(timezone=True)),
        sa.Column('cancelled_by_admin_id', postgresql.UUID(as_uuid=True)),
        sa.Column('cancellation_reason', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("audience_type IN ('all_eligible_users', 'selected_users')", name='ck_platform_notices_audience_type'),
        sa.CheckConstraint('(cancelled_at IS NULL AND cancelled_by_admin_id IS NULL AND cancellation_reason IS NULL) OR (cancelled_at IS NOT NULL AND cancelled_by_admin_id IS NOT NULL AND cancellation_reason IS NOT NULL)', name='ck_platform_notices_cancellation_integrity'),
        sa.CheckConstraint("(audience_type = 'all_eligible_users' AND global_sequence IS NOT NULL) OR (audience_type = 'selected_users' AND global_sequence IS NULL)", name='ck_platform_notices_global_sequence_scope'),
        sa.CheckConstraint('char_length(btrim(message)) > 0', name='ck_platform_notices_message_not_empty'),
        sa.CheckConstraint('char_length(btrim(title)) > 0', name='ck_platform_notices_title_not_empty'),
        sa.ForeignKeyConstraint(['cancelled_by_admin_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by_admin_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_platform_notices_audience_cancelled_published_id', 'platform_notices', ['audience_type', 'cancelled_at', 'published_at', 'id'], unique=False)
    op.create_index('ix_platform_notices_cancelled_at', 'platform_notices', ['cancelled_at'], unique=False)
    op.create_index('ix_platform_notices_created_by_admin_id', 'platform_notices', ['created_by_admin_id'], unique=False)
    op.create_index('ix_platform_notices_history_order', 'platform_notices', [sa.text('published_at DESC'), sa.text('id DESC')], unique=False)
    op.create_index('ix_platform_notices_history_search_trgm', 'platform_notices', [sa.text("(coalesce(title, '') || ' ' || coalesce(message, '')) gin_trgm_ops")], unique=False, postgresql_using='gin')
    op.create_index('uq_platform_notices_admin_idempotency_key', 'platform_notices', ['created_by_admin_id', 'idempotency_key_hash'], unique=True)
    op.create_index('uq_platform_notices_global_sequence', 'platform_notices', ['global_sequence'], unique=True, postgresql_where=sa.text('global_sequence IS NOT NULL'))


def downgrade() -> None:
    op.drop_table('platform_notices')
    op.execute("DROP SEQUENCE platform_notice_global_sequence_seq")
