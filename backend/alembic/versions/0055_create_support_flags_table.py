"""create support_flags table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0055_support_flags'
down_revision = '0054_money_issue_events'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'support_flags',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('flag_type', sa.String(length=80), nullable=False),
        sa.Column('flag_status', sa.String(length=30), nullable=False, server_default=sa.text("'open'")),
        sa.Column('severity', sa.String(length=30), nullable=False, server_default=sa.text("'attention'")),
        sa.Column('source', sa.String(length=40), nullable=False),
        sa.Column('title', sa.String(length=180), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('target_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('target_game_id', postgresql.UUID(as_uuid=True)),
        sa.Column('target_booking_id', postgresql.UUID(as_uuid=True)),
        sa.Column('target_payment_id', postgresql.UUID(as_uuid=True)),
        sa.Column('target_refund_id', postgresql.UUID(as_uuid=True)),
        sa.Column('target_game_credit_id', postgresql.UUID(as_uuid=True)),
        sa.Column('target_venue_id', postgresql.UUID(as_uuid=True)),
        sa.Column('target_venue_image_id', postgresql.UUID(as_uuid=True)),
        sa.Column('target_notification_id', postgresql.UUID(as_uuid=True)),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('idempotency_key', sa.String(length=160)),
        sa.Column('source_admin_action_id', postgresql.UUID(as_uuid=True)),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('resolved_by_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('resolution_outcome', sa.String(length=60)),
        sa.Column('resolution_reason', sa.Text()),
        sa.Column('resolution_admin_action_id', postgresql.UUID(as_uuid=True)),
        sa.Column('resolved_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("flag_status IN ('open', 'resolved')", name='ck_support_flags_flag_status'),
        sa.CheckConstraint("flag_type IN ('venue_image_upload_failed', 'venue_image_readiness_failed', 'account_delete_partial_failure', 'community_game_review_required')", name='ck_support_flags_flag_type'),
        sa.CheckConstraint("resolution_outcome IS NULL OR resolution_outcome IN ('handled_externally', 'retried_successfully', 'no_action_needed', 'duplicate', 'invalid_flag')", name='ck_support_flags_resolution_outcome'),
        sa.CheckConstraint("(flag_status = 'open' AND resolved_at IS NULL AND resolved_by_user_id IS NULL AND resolution_outcome IS NULL AND resolution_reason IS NULL) OR (flag_status = 'resolved' AND resolved_at IS NOT NULL AND resolved_by_user_id IS NOT NULL AND resolution_outcome IS NOT NULL AND resolution_reason IS NOT NULL)", name='ck_support_flags_resolution_state'),
        sa.CheckConstraint("severity IN ('attention', 'urgent', 'critical')", name='ck_support_flags_severity'),
        sa.CheckConstraint("source IN ('system', 'admin', 'stripe', 'venue_image', 'account', 'official_game')", name='ck_support_flags_source'),
        sa.CheckConstraint('target_user_id IS NOT NULL OR target_game_id IS NOT NULL OR target_booking_id IS NOT NULL OR target_payment_id IS NOT NULL OR target_refund_id IS NOT NULL OR target_game_credit_id IS NOT NULL OR target_venue_id IS NOT NULL OR target_venue_image_id IS NOT NULL OR target_notification_id IS NOT NULL', name='ck_support_flags_target_required'),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['resolution_admin_action_id'], ['admin_actions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['resolved_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['source_admin_action_id'], ['admin_actions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_booking_id'], ['bookings.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_game_credit_id'], ['game_credits.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_game_id'], ['games.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_notification_id'], ['notifications.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_payment_id'], ['payments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_refund_id'], ['refunds.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_venue_id'], ['venues.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_venue_image_id'], ['venue_images.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_support_flags_created_at', 'support_flags', ['created_at'], unique=False)
    op.create_index('ix_support_flags_flag_status', 'support_flags', ['flag_status'], unique=False)
    op.create_index('ix_support_flags_flag_type', 'support_flags', ['flag_type'], unique=False)
    op.create_index('ix_support_flags_resolution_admin_action_id', 'support_flags', ['resolution_admin_action_id'], unique=False)
    op.create_index('ix_support_flags_resolved_at', 'support_flags', ['resolved_at'], unique=False)
    op.create_index('ix_support_flags_source_admin_action_id', 'support_flags', ['source_admin_action_id'], unique=False)
    op.create_index('ix_support_flags_target_booking_id', 'support_flags', ['target_booking_id'], unique=False)
    op.create_index('ix_support_flags_target_game_credit_id', 'support_flags', ['target_game_credit_id'], unique=False)
    op.create_index('ix_support_flags_target_game_id', 'support_flags', ['target_game_id'], unique=False)
    op.create_index('ix_support_flags_target_notification_id', 'support_flags', ['target_notification_id'], unique=False)
    op.create_index('ix_support_flags_target_payment_id', 'support_flags', ['target_payment_id'], unique=False)
    op.create_index('ix_support_flags_target_refund_id', 'support_flags', ['target_refund_id'], unique=False)
    op.create_index('ix_support_flags_target_user_id', 'support_flags', ['target_user_id'], unique=False)
    op.create_index('ix_support_flags_target_venue_id', 'support_flags', ['target_venue_id'], unique=False)
    op.create_index('ix_support_flags_target_venue_image_id', 'support_flags', ['target_venue_image_id'], unique=False)
    op.create_index('uq_support_flags_flag_type_idempotency_key', 'support_flags', ['flag_type', 'idempotency_key'], unique=True, postgresql_where=sa.text('idempotency_key IS NOT NULL'))


def downgrade() -> None:
    op.drop_table('support_flags')
