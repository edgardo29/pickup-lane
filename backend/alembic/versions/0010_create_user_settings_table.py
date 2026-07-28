"""create user_settings table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0010_user_settings'
down_revision = '0009_user_payment_methods'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'user_settings',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('push_notifications_enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('email_notifications_enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('sms_notifications_enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('marketing_opt_in', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('location_permission_status', sa.String(length=20), nullable=False, server_default=sa.text("'unknown'")),
        sa.Column('selected_city', sa.String(length=120)),
        sa.Column('selected_state', sa.String(length=120)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("location_permission_status IN ('unknown', 'allowed', 'denied', 'skipped')", name='ck_user_settings_location_permission_status'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id')
    )


def downgrade() -> None:
    op.drop_table('user_settings')
