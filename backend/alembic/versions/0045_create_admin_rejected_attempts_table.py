"""create admin_rejected_attempts table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0045_admin_rejected_attempts'
down_revision = '0044_payment_events'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'admin_rejected_attempts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('admin_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('attempt_type', sa.String(length=80), nullable=False),
        sa.Column('rejection_mode', sa.String(length=40), nullable=False),
        sa.Column('response_status_code', sa.Integer(), nullable=False),
        sa.Column('route_method', sa.String(length=10), nullable=False),
        sa.Column('route_path', sa.String(length=240), nullable=False),
        sa.Column('target_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('target_game_credit_id', postgresql.UUID(as_uuid=True)),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("attempt_type IN ('issue_credit_rejected', 'reverse_credit_rejected', 'suspend_user_rejected', 'delete_user_rejected')", name='ck_admin_rejected_attempts_attempt_type'),
        sa.CheckConstraint("rejection_mode IN ('domain_rejected_postload')", name='ck_admin_rejected_attempts_rejection_mode'),
        sa.CheckConstraint('response_status_code BETWEEN 400 AND 599', name='ck_admin_rejected_attempts_response_status_code'),
        sa.ForeignKeyConstraint(['admin_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_game_credit_id'], ['game_credits.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_admin_rejected_attempts_admin_user_id', 'admin_rejected_attempts', ['admin_user_id'], unique=False)
    op.create_index('ix_admin_rejected_attempts_attempt_type', 'admin_rejected_attempts', ['attempt_type'], unique=False)
    op.create_index('ix_admin_rejected_attempts_created_at', 'admin_rejected_attempts', ['created_at'], unique=False)
    op.create_index('ix_admin_rejected_attempts_rejection_mode', 'admin_rejected_attempts', ['rejection_mode'], unique=False)
    op.create_index('ix_admin_rejected_attempts_target_game_credit_id', 'admin_rejected_attempts', ['target_game_credit_id'], unique=False)
    op.create_index('ix_admin_rejected_attempts_target_user_id', 'admin_rejected_attempts', ['target_user_id'], unique=False)


def downgrade() -> None:
    op.drop_table('admin_rejected_attempts')
