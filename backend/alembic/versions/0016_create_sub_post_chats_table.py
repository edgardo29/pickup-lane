"""create sub_post_chats table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0016_sub_post_chats'
down_revision = '0015_platform_selected_reads'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'sub_post_chats',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('sub_post_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chat_status', sa.String(length=30), nullable=False, server_default=sa.text("'active'")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('closed_at', sa.DateTime(timezone=True)),
        sa.Column('message_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('needs_review_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('removed_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('latest_message_id', postgresql.UUID(as_uuid=True)),
        sa.Column('latest_message_preview', sa.Text()),
        sa.Column('latest_message_at', sa.DateTime(timezone=True)),
        sa.CheckConstraint("chat_status IN ('active', 'closed')", name='ck_sub_post_chats_chat_status'),
        sa.CheckConstraint("(chat_status = 'active' AND closed_at IS NULL) OR (chat_status = 'closed' AND closed_at IS NOT NULL)", name='ck_sub_post_chats_closed_requires_closed_at'),
        sa.ForeignKeyConstraint(['sub_post_id'], ['sub_posts.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sub_post_id', name='uq_sub_post_chats_sub_post_id')
    )
    op.create_index('ix_sub_post_chats_chat_status', 'sub_post_chats', ['chat_status'], unique=False)
    op.create_index('ix_sub_post_chats_latest_message_at', 'sub_post_chats', ['latest_message_at'], unique=False)
    op.create_index('ix_sub_post_chats_needs_review_count', 'sub_post_chats', ['needs_review_count'], unique=False)
    op.create_index('ix_sub_post_chats_sub_post_id', 'sub_post_chats', ['sub_post_id'], unique=False)


def downgrade() -> None:
    op.drop_table('sub_post_chats')
