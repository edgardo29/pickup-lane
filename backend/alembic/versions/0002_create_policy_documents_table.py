"""create policy_documents table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0002_policy_documents'
down_revision = '0001_pg_trgm'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'policy_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('policy_type', sa.String(length=50), nullable=False),
        sa.Column('version', sa.String(length=30), nullable=False),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('content_url', sa.Text()),
        sa.Column('content_text', sa.Text()),
        sa.Column('effective_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('retired_at', sa.DateTime(timezone=True)),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint('(content_url IS NOT NULL AND char_length(btrim(content_url)) > 0) OR (content_text IS NOT NULL AND char_length(btrim(content_text)) > 0)', name='ck_policy_documents_content_required'),
        sa.CheckConstraint("policy_type IN ('terms_of_service', 'privacy_policy', 'refund_policy', 'player_cancellation_policy', 'community_host_agreement', 'official_game_rules')", name='ck_policy_documents_policy_type'),
        sa.CheckConstraint('(retired_at IS NULL OR retired_at > effective_at)', name='ck_policy_documents_retired_after_effective'),
        sa.CheckConstraint('char_length(btrim(title)) > 0', name='ck_policy_documents_title_not_empty'),
        sa.CheckConstraint('char_length(btrim(version)) > 0', name='ck_policy_documents_version_not_empty'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('policy_type', 'version', name='uq_policy_documents_policy_type_version')
    )
    op.create_index('ix_policy_documents_effective_at', 'policy_documents', ['effective_at'], unique=False)
    op.create_index('ix_policy_documents_is_active', 'policy_documents', ['is_active'], unique=False)
    op.create_index('ix_policy_documents_policy_type', 'policy_documents', ['policy_type'], unique=False)


def downgrade() -> None:
    op.drop_table('policy_documents')
