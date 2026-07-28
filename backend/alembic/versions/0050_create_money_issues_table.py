"""create money_issues table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0050_money_issues'
down_revision = '0049_admin_financial_outcomes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'money_issues',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('operation_key', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('issue_type', sa.String(length=80), nullable=False),
        sa.Column('origin_workflow', sa.String(length=80), nullable=False),
        sa.Column('value_kind', sa.String(length=40), nullable=False),
        sa.Column('amount_cents', sa.Integer(), nullable=False),
        sa.Column('currency', sa.CHAR(length=3), nullable=False, server_default=sa.text("'USD'")),
        sa.Column('target_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('target_game_id', postgresql.UUID(as_uuid=True)),
        sa.Column('target_booking_id', postgresql.UUID(as_uuid=True)),
        sa.Column('target_payment_id', postgresql.UUID(as_uuid=True)),
        sa.Column('target_refund_id', postgresql.UUID(as_uuid=True)),
        sa.Column('target_game_credit_id', postgresql.UUID(as_uuid=True)),
        sa.Column('target_credit_usage_id', postgresql.UUID(as_uuid=True)),
        sa.Column('latest_reason_code', sa.String(length=80)),
        sa.Column('latest_summary', sa.Text()),
        sa.Column('recommended_action_code', sa.String(length=80), nullable=False),
        sa.Column('occurrence_count', sa.Integer(), nullable=False),
        sa.Column('reopen_count', sa.Integer(), nullable=False),
        sa.Column('first_detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True)),
        sa.Column('resolved_by_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('resolution_reason_code', sa.String(length=80)),
        sa.Column('resolution_note', sa.Text()),
        sa.Column('resolution_external_reference', sa.String(length=255)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint('amount_cents >= 0', name='ck_money_issues_amount_cents'),
        sa.CheckConstraint("(issue_type NOT LIKE 'credit_%' OR target_credit_usage_id IS NOT NULL)", name='ck_money_issues_credit_requires_usage'),
        sa.CheckConstraint("currency = 'USD'", name='ck_money_issues_currency'),
        sa.CheckConstraint("issue_type IN ('refund_missing_provider_reference', 'refund_processing_overdue', 'refund_failed', 'refund_cancelled', 'refund_outcome_unknown', 'credit_restore_failed', 'credit_release_failed')", name='ck_money_issues_issue_type'),
        sa.CheckConstraint('occurrence_count >= 1', name='ck_money_issues_occurrence_count'),
        sa.CheckConstraint("origin_workflow IN ('player_removal', 'official_game_cancellation', 'community_publish_fee_refund', 'direct_admin_refund', 'official_game_checkout', 'pending_checkout_expiration', 'pending_checkout_cancellation', 'admin_game_update')", name='ck_money_issues_origin_workflow'),
        sa.CheckConstraint("recommended_action_code IN ('recover_provider_reference', 'retry_refund', 'verify_provider_refund', 'retry_credit_restore', 'retry_credit_release', 'review_unknown_outcome', 'review_and_resolve_no_action', 'document_external_completion')", name='ck_money_issues_recommended_action_code'),
        sa.CheckConstraint("(issue_type NOT LIKE 'refund_%' OR target_refund_id IS NOT NULL)", name='ck_money_issues_refund_requires_refund'),
        sa.CheckConstraint('reopen_count >= 0', name='ck_money_issues_reopen_count'),
        sa.CheckConstraint("((status = 'open') AND resolved_at IS NULL AND resolved_by_user_id IS NULL AND resolution_reason_code IS NULL AND resolution_note IS NULL AND resolution_external_reference IS NULL) OR ((status = 'resolved') AND resolved_at IS NOT NULL AND resolved_by_user_id IS NOT NULL AND resolution_reason_code IS NOT NULL)", name='ck_money_issues_resolution_fields_match_status'),
        sa.CheckConstraint("resolution_reason_code IS NULL OR resolution_reason_code IN ('retried_successfully', 'provider_completed_no_action_required', 'handled_externally', 'invalid_issue', 'unable_to_complete_documented')", name='ck_money_issues_resolution_reason_code'),
        sa.CheckConstraint("status IN ('open', 'resolved')", name='ck_money_issues_status'),
        sa.CheckConstraint("value_kind IN ('cash_refund', 'game_credit_restore', 'game_credit_release')", name='ck_money_issues_value_kind'),
        sa.ForeignKeyConstraint(['resolved_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_booking_id'], ['bookings.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_credit_usage_id'], ['game_credit_usage.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['target_game_credit_id'], ['game_credits.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_game_id'], ['games.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_payment_id'], ['payments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_refund_id'], ['refunds.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['target_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('operation_key', name='uq_money_issues_operation_key')
    )
    op.create_index('ix_money_issues_activity', 'money_issues', ['last_activity_at', 'id'], unique=False)
    op.create_index('ix_money_issues_issue_type_status', 'money_issues', ['issue_type', 'status'], unique=False)
    op.create_index('ix_money_issues_open_queue', 'money_issues', ['status', 'first_detected_at', 'id'], unique=False)
    op.create_index('ix_money_issues_origin_workflow_status', 'money_issues', ['origin_workflow', 'status'], unique=False)
    op.create_index('ix_money_issues_resolved', 'money_issues', ['resolved_at', 'id'], unique=False)
    op.create_index('ix_money_issues_target_booking_id', 'money_issues', ['target_booking_id'], unique=False)
    op.create_index('ix_money_issues_target_credit_usage_id', 'money_issues', ['target_credit_usage_id'], unique=False)
    op.create_index('ix_money_issues_target_game_credit_id', 'money_issues', ['target_game_credit_id'], unique=False)
    op.create_index('ix_money_issues_target_game_id', 'money_issues', ['target_game_id'], unique=False)
    op.create_index('ix_money_issues_target_payment_id', 'money_issues', ['target_payment_id'], unique=False)
    op.create_index('ix_money_issues_target_refund_id', 'money_issues', ['target_refund_id'], unique=False)
    op.create_index('ix_money_issues_target_user_id', 'money_issues', ['target_user_id'], unique=False)


def downgrade() -> None:
    op.drop_table('money_issues')
