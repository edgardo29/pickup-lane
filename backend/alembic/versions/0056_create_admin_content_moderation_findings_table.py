"""create admin_content_moderation_findings table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0056_admin_content_findings'
down_revision = '0055_support_flags'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'admin_content_moderation_findings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('review_case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('risk_area', sa.String(length=60), nullable=False),
        sa.Column('finding_type', sa.String(length=60), nullable=False),
        sa.Column('priority', sa.String(length=30), nullable=False, server_default=sa.text("'attention'")),
        sa.Column('source_field', sa.String(length=80), nullable=False),
        sa.Column('source_content_hash', sa.String(length=64), nullable=False),
        sa.Column('evidence_fingerprint', sa.String(length=64), nullable=False),
        sa.Column('evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('current_match', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('first_detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('cleared_at', sa.DateTime(timezone=True)),
        sa.Column('scanner_version', sa.String(length=80), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint('(current_match = true AND cleared_at IS NULL) OR (current_match = false AND cleared_at IS NOT NULL)', name='ck_admin_content_moderation_findings_current_clear_state'),
        sa.CheckConstraint('first_detected_at <= last_detected_at', name='ck_admin_content_moderation_findings_detected_order'),
        sa.CheckConstraint("jsonb_typeof(evidence) = 'array' AND jsonb_array_length(evidence) > 0", name='ck_admin_content_moderation_findings_evidence_nonempty'),
        sa.CheckConstraint("finding_type IN ('off_app_contact', 'payment_pressure', 'spam_or_scam', 'threat_or_violence', 'harassment_or_abuse', 'slur_or_hate', 'sexual_or_explicit')", name='ck_admin_content_moderation_findings_finding_type'),
        sa.CheckConstraint('length(trim(evidence_fingerprint)) > 0', name='ck_admin_content_moderation_findings_fingerprint_present'),
        sa.CheckConstraint("priority IN ('attention', 'urgent', 'critical')", name='ck_admin_content_moderation_findings_priority'),
        sa.CheckConstraint("risk_area IN ('unsafe_post_text', 'unsafe_payment_text')", name='ck_admin_content_moderation_findings_risk_area'),
        sa.CheckConstraint('length(trim(source_field)) > 0', name='ck_admin_content_moderation_findings_source_field_present'),
        sa.CheckConstraint('length(trim(source_content_hash)) > 0', name='ck_admin_content_moderation_findings_source_hash_present'),
        sa.ForeignKeyConstraint(['review_case_id'], ['admin_review_cases.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_admin_content_moderation_findings_case_current_type', 'admin_content_moderation_findings', ['review_case_id', 'current_match', 'finding_type'], unique=False)
    op.create_index('ix_admin_content_moderation_findings_current_match', 'admin_content_moderation_findings', ['current_match'], unique=False)
    op.create_index('ix_admin_content_moderation_findings_finding_type', 'admin_content_moderation_findings', ['finding_type'], unique=False)
    op.create_index('ix_admin_content_moderation_findings_review_case_id', 'admin_content_moderation_findings', ['review_case_id'], unique=False)
    op.create_index('uq_admin_content_moderation_findings_current_identity', 'admin_content_moderation_findings', ['review_case_id', 'source_field', 'finding_type', 'evidence_fingerprint'], unique=True, postgresql_where=sa.text('current_match = true'))


def downgrade() -> None:
    op.drop_table('admin_content_moderation_findings')
