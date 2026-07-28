"""create users table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0003_users'
down_revision = '0002_policy_documents'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('auth_user_id', sa.String(length=128)),
        sa.Column('role', sa.String(length=20), nullable=False, server_default=sa.text("'player'")),
        sa.Column('email', sa.String(length=255)),
        sa.Column('email_verified_at', sa.DateTime(timezone=True)),
        sa.Column('phone', sa.String(length=30)),
        sa.Column('first_name', sa.String(length=100)),
        sa.Column('last_name', sa.String(length=100)),
        sa.Column('date_of_birth', sa.Date()),
        sa.Column('profile_photo_url', sa.Text()),
        sa.Column('home_city', sa.String(length=120)),
        sa.Column('home_state', sa.String(length=120)),
        sa.Column('account_status', sa.String(length=30), nullable=False, server_default=sa.text("'active'")),
        sa.Column('hosting_status', sa.String(length=30), nullable=False, server_default=sa.text("'not_eligible'")),
        sa.Column('stripe_customer_id', sa.String(length=255)),
        sa.Column('member_since', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
        sa.CheckConstraint("account_status IN ('active', 'suspended', 'pending_deletion', 'deleted')", name='ck_users_account_status'),
        sa.CheckConstraint("hosting_status IN ('not_eligible', 'eligible', 'restricted')", name='ck_users_hosting_status'),
        sa.CheckConstraint("role IN ('player', 'admin')", name='ck_users_role'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('auth_user_id', name='uq_users_auth_user_id'),
        sa.UniqueConstraint('email', name='uq_users_email'),
        sa.UniqueConstraint('phone', name='uq_users_phone'),
        sa.UniqueConstraint('stripe_customer_id', name='uq_users_stripe_customer_id')
    )
    op.create_index('ix_users_admin_account_status_created_id', 'users', ['account_status', sa.text('created_at DESC'), sa.text('id DESC')], unique=False, postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('ix_users_admin_email_lower', 'users', [sa.text('lower(email)')], unique=False, postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('ix_users_admin_hosting_status_created_id', 'users', ['hosting_status', sa.text('created_at DESC'), sa.text('id DESC')], unique=False, postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('ix_users_admin_list_created_id', 'users', [sa.text('created_at DESC'), sa.text('id DESC')], unique=False)
    op.create_index('ix_users_admin_role_created_id', 'users', ['role', sa.text('created_at DESC'), sa.text('id DESC')], unique=False, postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('ix_users_email_trgm', 'users', ['email'], unique=False, postgresql_using='gin', postgresql_where=sa.text('deleted_at IS NULL'), postgresql_ops={'email': 'gin_trgm_ops'})
    op.create_index('ix_users_first_name_trgm', 'users', ['first_name'], unique=False, postgresql_using='gin', postgresql_where=sa.text('deleted_at IS NULL'), postgresql_ops={'first_name': 'gin_trgm_ops'})
    op.create_index('ix_users_last_name_trgm', 'users', ['last_name'], unique=False, postgresql_using='gin', postgresql_where=sa.text('deleted_at IS NULL'), postgresql_ops={'last_name': 'gin_trgm_ops'})
    op.create_index('ix_users_platform_notice_active_id', 'users', ['id'], unique=False, postgresql_where=sa.text("account_status = 'active' AND deleted_at IS NULL"))


def downgrade() -> None:
    op.drop_table('users')
