"""create game_chat_message_detections table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0039_game_chat_msg_detections'
down_revision = '0038_community_publish_attempts'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'game_chat_message_detections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('rule_key', sa.String(length=80), nullable=False),
        sa.Column('matched_preview', sa.String(length=240)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("category IN ('phone_number', 'email', 'link', 'off_platform_contact', 'payment_discussion', 'harassment_or_abuse', 'threat_or_safety', 'slur_or_hate', 'spam_or_repeated_message')", name='ck_game_chat_message_detections_category'),
        sa.CheckConstraint("severity IN ('low', 'medium', 'high')", name='ck_game_chat_message_detections_severity'),
        sa.ForeignKeyConstraint(['message_id'], ['chat_messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_game_chat_message_detections_category', 'game_chat_message_detections', ['category'], unique=False)
    op.create_index('ix_game_chat_message_detections_created_at', 'game_chat_message_detections', ['created_at'], unique=False)
    op.create_index('ix_game_chat_message_detections_message_id', 'game_chat_message_detections', ['message_id'], unique=False)


def downgrade() -> None:
    op.drop_table('game_chat_message_detections')
