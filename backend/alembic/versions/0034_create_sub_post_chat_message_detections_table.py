"""create sub_post_chat_message_detections table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0034_sub_chat_msg_detections'
down_revision = '0033_payments'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'sub_post_chat_message_detections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('message_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('rule_key', sa.String(length=80), nullable=False),
        sa.Column('matched_preview', sa.String(length=240)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("category IN ('phone_number', 'email', 'link', 'off_platform_contact', 'payment_discussion', 'harassment_or_abuse', 'threat_or_safety', 'slur_or_hate', 'spam_or_repeated_message')", name='ck_sub_post_chat_message_detections_category'),
        sa.CheckConstraint("severity IN ('low', 'medium', 'high')", name='ck_sub_post_chat_message_detections_severity'),
        sa.ForeignKeyConstraint(['message_id'], ['sub_post_chat_messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sub_post_chat_message_detections_category', 'sub_post_chat_message_detections', ['category'], unique=False)
    op.create_index('ix_sub_post_chat_message_detections_created_at', 'sub_post_chat_message_detections', ['created_at'], unique=False)
    op.create_index('ix_sub_post_chat_message_detections_message_id', 'sub_post_chat_message_detections', ['message_id'], unique=False)


def downgrade() -> None:
    op.drop_table('sub_post_chat_message_detections')
