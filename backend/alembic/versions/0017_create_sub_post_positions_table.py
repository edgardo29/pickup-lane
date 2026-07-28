"""create sub_post_positions table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0017_sub_post_positions'
down_revision = '0016_sub_post_chats'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'sub_post_positions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('sub_post_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('position_label', sa.String(length=50), nullable=False),
        sa.Column('player_group', sa.String(length=30), nullable=False, server_default=sa.text("'open'")),
        sa.Column('spots_needed', sa.Integer(), nullable=False, server_default=sa.text('1')),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("player_group IN ('open', 'men', 'women')", name='ck_sub_post_positions_player_group'),
        sa.CheckConstraint("position_label IN ('field_player', 'goalkeeper')", name='ck_sub_post_positions_position_label'),
        sa.CheckConstraint('sort_order >= 0', name='ck_sub_post_positions_sort_order_non_negative'),
        sa.CheckConstraint('spots_needed > 0', name='ck_sub_post_positions_spots_needed_positive'),
        sa.ForeignKeyConstraint(['sub_post_id'], ['sub_posts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id', 'sub_post_id', name='uq_sub_post_positions_id_sub_post_id'),
        sa.UniqueConstraint('sub_post_id', 'position_label', 'player_group', name='uq_sub_post_positions_post_position_group')
    )
    op.create_index('ix_sub_post_positions_sub_post_id', 'sub_post_positions', ['sub_post_id'], unique=False)


def downgrade() -> None:
    op.drop_table('sub_post_positions')
