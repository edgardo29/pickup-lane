"""create user_stats table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0011_user_stats'
down_revision = '0010_user_settings'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'user_stats',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('games_played_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('games_hosted_completed_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('no_show_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('late_cancel_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('host_cancel_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('last_calculated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint('games_hosted_completed_count >= 0', name='ck_user_stats_games_hosted_completed_count'),
        sa.CheckConstraint('games_played_count >= 0', name='ck_user_stats_games_played_count'),
        sa.CheckConstraint('host_cancel_count >= 0', name='ck_user_stats_host_cancel_count'),
        sa.CheckConstraint('late_cancel_count >= 0', name='ck_user_stats_late_cancel_count'),
        sa.CheckConstraint('no_show_count >= 0', name='ck_user_stats_no_show_count'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id')
    )


def downgrade() -> None:
    op.drop_table('user_stats')
