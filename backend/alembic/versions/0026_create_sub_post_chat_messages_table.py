"""create sub_post_chat_messages table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0026_sub_post_chat_messages'
down_revision = '0025_game_status_history'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'sub_post_chat_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('chat_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sender_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('sender_display_name_snapshot', sa.String(length=120), nullable=False),
        sa.Column('sender_initials_snapshot', sa.String(length=8), nullable=False),
        sa.Column('message_type', sa.String(length=30), nullable=False, server_default=sa.text("'text'")),
        sa.Column('message_body', sa.Text(), nullable=False),
        sa.Column('visibility_status', sa.String(length=30), nullable=False, server_default=sa.text("'visible'")),
        sa.Column('review_status', sa.String(length=30), nullable=False, server_default=sa.text("'clear'")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('reviewed_at', sa.DateTime(timezone=True)),
        sa.Column('reviewed_by_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('removed_at', sa.DateTime(timezone=True)),
        sa.Column('removed_by_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('removed_source', sa.String(length=30)),
        sa.Column('removed_reason', sa.Text()),
        sa.Column('restored_at', sa.DateTime(timezone=True)),
        sa.Column('restored_by_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('restored_reason', sa.Text()),
        sa.CheckConstraint('char_length(message_body) <= 300', name='ck_sub_post_chat_messages_body_max_length'),
        sa.CheckConstraint('char_length(btrim(message_body)) > 0', name='ck_sub_post_chat_messages_body_not_empty'),
        sa.CheckConstraint("message_type IN ('text')", name='ck_sub_post_chat_messages_message_type'),
        sa.CheckConstraint("(visibility_status <> 'removed' OR removed_at IS NOT NULL)", name='ck_sub_post_chat_messages_removed_requires_removed_at'),
        sa.CheckConstraint("(visibility_status <> 'removed' OR removed_source IS NOT NULL)", name='ck_sub_post_chat_messages_removed_requires_source'),
        sa.CheckConstraint("removed_source IS NULL OR removed_source IN ('admin', 'sender', 'system')", name='ck_sub_post_chat_messages_removed_source'),
        sa.CheckConstraint("review_status IN ('clear', 'needs_review', 'reviewed')", name='ck_sub_post_chat_messages_review_status'),
        sa.CheckConstraint("(review_status <> 'reviewed' OR reviewed_at IS NOT NULL)", name='ck_sub_post_chat_messages_reviewed_requires_reviewed_at'),
        sa.CheckConstraint('char_length(btrim(sender_initials_snapshot)) > 0', name='ck_sub_post_chat_messages_sender_initials_not_empty'),
        sa.CheckConstraint('char_length(btrim(sender_display_name_snapshot)) > 0', name='ck_sub_post_chat_messages_sender_name_not_empty'),
        sa.CheckConstraint("visibility_status IN ('visible', 'removed')", name='ck_sub_post_chat_messages_visibility_status'),
        sa.ForeignKeyConstraint(['chat_id'], ['sub_post_chats.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['removed_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['restored_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reviewed_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['sender_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sub_post_chat_messages_chat_id', 'sub_post_chat_messages', ['chat_id'], unique=False)
    op.create_index('ix_sub_post_chat_messages_chat_id_created_at', 'sub_post_chat_messages', ['chat_id', 'created_at'], unique=False)
    op.create_index('ix_sub_post_chat_messages_chat_id_review_status', 'sub_post_chat_messages', ['chat_id', 'review_status'], unique=False)
    op.create_index('ix_sub_post_chat_messages_chat_id_visibility_status', 'sub_post_chat_messages', ['chat_id', 'visibility_status'], unique=False)
    op.create_index('ix_sub_post_chat_messages_removed_by_user_id', 'sub_post_chat_messages', ['removed_by_user_id'], unique=False)
    op.create_index('ix_sub_post_chat_messages_restored_by_user_id', 'sub_post_chat_messages', ['restored_by_user_id'], unique=False)
    op.create_index('ix_sub_post_chat_messages_review_status', 'sub_post_chat_messages', ['review_status'], unique=False)
    op.create_index('ix_sub_post_chat_messages_reviewed_by_user_id', 'sub_post_chat_messages', ['reviewed_by_user_id'], unique=False)
    op.create_index('ix_sub_post_chat_messages_sender_user_id', 'sub_post_chat_messages', ['sender_user_id'], unique=False)
    op.create_index('ix_sub_post_chat_messages_visibility_status', 'sub_post_chat_messages', ['visibility_status'], unique=False)


def downgrade() -> None:
    op.drop_table('sub_post_chat_messages')
