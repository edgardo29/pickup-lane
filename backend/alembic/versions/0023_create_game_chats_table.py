"""create game_chats table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0023_game_chats'
down_revision = '0022_community_game_details'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'game_chats',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('game_id', postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.CheckConstraint("chat_status IN ('active', 'closed')", name='ck_game_chats_chat_status'),
        sa.CheckConstraint("(chat_status = 'active' AND closed_at IS NULL) OR (chat_status = 'closed' AND closed_at IS NOT NULL)", name='ck_game_chats_closed_requires_closed_at'),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('game_id', name='uq_game_chats_game_id')
    )
    op.create_index('ix_game_chats_chat_status', 'game_chats', ['chat_status'], unique=False)
    op.create_index('ix_game_chats_latest_message_at', 'game_chats', ['latest_message_at'], unique=False)
    op.create_index('ix_game_chats_needs_review_count', 'game_chats', ['needs_review_count'], unique=False)


def downgrade() -> None:
    op.drop_table('game_chats')
