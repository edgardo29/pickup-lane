"""create venue_images table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0020_venue_images'
down_revision = '0019_venue_approval_requests'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'venue_images',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('venue_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('uploaded_by_user_id', postgresql.UUID(as_uuid=True)),
        sa.Column('storage_provider', sa.String(length=30), nullable=False, server_default=sa.text("'r2'")),
        sa.Column('storage_object_key', sa.Text(), nullable=False),
        sa.Column('storage_bucket', sa.String(length=120), nullable=False),
        sa.Column('storage_account_id', sa.String(length=120), nullable=False),
        sa.Column('content_type', sa.String(length=120), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('etag', sa.String(length=255)),
        sa.Column('image_role', sa.String(length=30), nullable=False, server_default=sa.text("'gallery'")),
        sa.Column('image_status', sa.String(length=30), nullable=False, server_default=sa.text("'pending_upload'")),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('alt_text', sa.String(length=280)),
        sa.Column('caption', sa.String(length=280)),
        sa.Column('upload_requested_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('upload_completed_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
        sa.CheckConstraint('char_length(btrim(content_type)) > 0', name='ck_venue_images_content_type_not_empty'),
        sa.CheckConstraint("image_role IN ('card', 'gallery')", name='ck_venue_images_image_role'),
        sa.CheckConstraint("image_status IN ('pending_upload', 'active', 'hidden', 'removed')", name='ck_venue_images_image_status'),
        sa.CheckConstraint('size_bytes > 0', name='ck_venue_images_size_bytes_positive'),
        sa.CheckConstraint('sort_order >= 0', name='ck_venue_images_sort_order_non_negative'),
        sa.CheckConstraint('char_length(btrim(storage_account_id)) > 0', name='ck_venue_images_storage_account_id_not_empty'),
        sa.CheckConstraint('char_length(btrim(storage_bucket)) > 0', name='ck_venue_images_storage_bucket_not_empty'),
        sa.CheckConstraint('char_length(btrim(storage_object_key)) > 0', name='ck_venue_images_storage_object_key_not_empty'),
        sa.CheckConstraint('char_length(btrim(storage_provider)) > 0', name='ck_venue_images_storage_provider_not_empty'),
        sa.ForeignKeyConstraint(['uploaded_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['venue_id'], ['venues.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_venue_images_image_status', 'venue_images', ['image_status'], unique=False)
    op.create_index('ix_venue_images_sort_order', 'venue_images', ['sort_order'], unique=False)
    op.create_index('ix_venue_images_uploaded_by_user_id', 'venue_images', ['uploaded_by_user_id'], unique=False)
    op.create_index('ix_venue_images_venue_id', 'venue_images', ['venue_id'], unique=False)
    op.create_index('ix_venue_images_venue_id_image_status_sort_order', 'venue_images', ['venue_id', 'image_status', 'sort_order'], unique=False)
    op.create_index('uq_venue_images_one_active_primary_per_venue', 'venue_images', ['venue_id'], unique=True, postgresql_where=sa.text("is_primary = true AND image_status = 'active' AND deleted_at IS NULL"))
    op.create_index('uq_venue_images_storage_object_key', 'venue_images', ['storage_object_key'], unique=True)


def downgrade() -> None:
    op.drop_table('venue_images')
