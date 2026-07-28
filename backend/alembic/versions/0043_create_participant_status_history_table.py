"""create participant_status_history table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0043_participant_status_history'
down_revision = '0042_host_publish_fees'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'participant_status_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('participant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('old_participant_status', sa.String(length=30)),
        sa.Column('new_participant_status', sa.String(length=30), nullable=False),
        sa.Column('old_attendance_status', sa.String(length=30)),
        sa.Column('new_attendance_status', sa.String(length=30)),
        sa.Column('changed_by_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('change_source', sa.String(length=30), nullable=False, server_default=sa.text("'system'")),
        sa.Column('change_reason', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("change_source IN ('user', 'host', 'admin', 'system', 'payment_webhook', 'scheduled_job')", name='ck_participant_status_history_change_source'),
        sa.CheckConstraint("(new_attendance_status IS NULL OR new_attendance_status IN ('unknown', 'attended', 'no_show', 'excused_absence', 'not_applicable'))", name='ck_participant_status_history_new_attendance_status'),
        sa.CheckConstraint("new_participant_status IN ('pending_payment', 'confirmed', 'waitlisted', 'cancelled', 'late_cancelled', 'removed', 'refunded')", name='ck_participant_status_history_new_participant_status'),
        sa.CheckConstraint("(old_attendance_status IS NULL OR old_attendance_status IN ('unknown', 'attended', 'no_show', 'excused_absence', 'not_applicable'))", name='ck_participant_status_history_old_attendance_status'),
        sa.CheckConstraint("(old_participant_status IS NULL OR old_participant_status IN ('pending_payment', 'confirmed', 'waitlisted', 'cancelled', 'late_cancelled', 'removed', 'refunded'))", name='ck_participant_status_history_old_participant_status'),
        sa.ForeignKeyConstraint(['changed_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['participant_id'], ['game_participants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_participant_status_history_change_source', 'participant_status_history', ['change_source'], unique=False)
    op.create_index('ix_participant_status_history_changed_by_user_id', 'participant_status_history', ['changed_by_user_id'], unique=False)
    op.create_index('ix_participant_status_history_created_at', 'participant_status_history', ['created_at'], unique=False)
    op.create_index('ix_participant_status_history_participant_id', 'participant_status_history', ['participant_id'], unique=False)
    op.create_index('ix_participant_status_history_participant_id_created_at', 'participant_status_history', ['participant_id', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('participant_status_history')
