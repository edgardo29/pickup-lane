"""create admin_review_case_events table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0059_admin_review_case_events'
down_revision = '0058_admin_review_signals'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'admin_review_case_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('review_case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(length=60), nullable=False),
        sa.Column('actor_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('admin_action_id', postgresql.UUID(as_uuid=True)),
        sa.Column('signal_id', postgresql.UUID(as_uuid=True)),
        sa.Column('content_moderation_finding_id', postgresql.UUID(as_uuid=True)),
        sa.Column('note_id', postgresql.UUID(as_uuid=True)),
        sa.Column('event_metadata', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("event_type IN ('case_created', 'signal_attached', 'finding_attached', 'finding_cleared', 'note_added', 'enforcement_action_linked', 'closed')", name='ck_admin_review_case_events_event_type'),
        sa.CheckConstraint('signal_id IS NULL OR content_moderation_finding_id IS NULL', name='ck_admin_review_case_events_one_child_ref'),
        sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['admin_action_id'], ['admin_actions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['content_moderation_finding_id'], ['admin_content_moderation_findings.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['note_id'], ['admin_review_case_notes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['review_case_id'], ['admin_review_cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['signal_id'], ['admin_review_signals.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_admin_review_case_events_actor_user_id', 'admin_review_case_events', ['actor_user_id'], unique=False)
    op.create_index('ix_admin_review_case_events_admin_action_id', 'admin_review_case_events', ['admin_action_id'], unique=False)
    op.create_index('ix_admin_review_case_events_content_moderation_finding_id', 'admin_review_case_events', ['content_moderation_finding_id'], unique=False)
    op.create_index('ix_admin_review_case_events_created_at', 'admin_review_case_events', ['created_at'], unique=False)
    op.create_index('ix_admin_review_case_events_event_type', 'admin_review_case_events', ['event_type'], unique=False)
    op.create_index('ix_admin_review_case_events_note_id', 'admin_review_case_events', ['note_id'], unique=False)
    op.create_index('ix_admin_review_case_events_review_case_id', 'admin_review_case_events', ['review_case_id'], unique=False)
    op.create_index('ix_admin_review_case_events_signal_id', 'admin_review_case_events', ['signal_id'], unique=False)


def downgrade() -> None:
    op.drop_table('admin_review_case_events')
