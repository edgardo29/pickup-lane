"""create platform_notice_recipients table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0014_platform_notice_recipients'
down_revision = '0013_games'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'platform_notice_recipients',
        sa.Column('notice_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['notice_id'], ['platform_notices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('notice_id', 'user_id')
    )
    op.create_index('ix_platform_notice_recipients_user_notice', 'platform_notice_recipients', ['user_id', 'notice_id'], unique=False)


def downgrade() -> None:
    op.drop_table('platform_notice_recipients')
