"""create sub_post_chat_message_detections table"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0034_sub_chat_msg_detections"
down_revision = "0033_payments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sub_post_chat_message_detections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("rule_key", sa.String(length=80), nullable=False),
        sa.Column("matched_preview", sa.String(length=240)),
        sa.Column("scanner_id", sa.String(length=80), nullable=False),
        sa.Column("scanner_version", sa.String(length=80), nullable=False),
        sa.Column("taxonomy_version", sa.String(length=40), nullable=False),
        sa.Column("configuration_hash", sa.String(length=64), nullable=False),
        sa.Column("canonicalization_version", sa.String(length=80), nullable=False),
        sa.Column("evidence_format_version", sa.String(length=40), nullable=False),
        sa.Column("target_context", sa.String(length=60), nullable=False),
        sa.Column("field_purpose", sa.String(length=40), nullable=False),
        sa.Column("source_field", sa.String(length=80), nullable=False),
        sa.Column("source_content_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "matched_rule_versions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "declared_limits", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("evidence_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("scanned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("execution_duration_us", sa.BigInteger(), nullable=False),
        sa.Column("detection_identity_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "category IN ('phone_number', 'email', 'link', 'off_platform_contact', 'payment_discussion', 'harassment_or_abuse', 'threat_or_safety', 'slur_or_hate', 'spam_or_repeated_message')",
            name="ck_sub_post_chat_message_detections_category",
        ),
        sa.CheckConstraint(
            "severity IN ('low', 'medium', 'high')",
            name="ck_sub_post_chat_message_detections_severity",
        ),
        sa.CheckConstraint(
            "configuration_hash ~ '^[0-9a-f]{64}$'",
            name="ck_sub_post_chat_message_detections_configuration_hash",
        ),
        sa.CheckConstraint(
            "source_content_hash ~ '^[0-9a-f]{64}$'",
            name="ck_sub_post_chat_message_detections_source_hash",
        ),
        sa.CheckConstraint(
            "evidence_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_sub_post_chat_message_detections_evidence_fingerprint",
        ),
        sa.CheckConstraint(
            "detection_identity_hash ~ '^[0-9a-f]{64}$'",
            name="ck_sub_post_chat_message_detections_identity_hash",
        ),
        sa.CheckConstraint(
            "execution_duration_us >= 0",
            name="ck_sub_post_chat_message_detections_duration_nonnegative",
        ),
        sa.CheckConstraint(
            "length(trim(scanner_id)) > 0 AND length(trim(scanner_version)) > 0 AND length(trim(taxonomy_version)) > 0 AND length(trim(canonicalization_version)) > 0 AND length(trim(evidence_format_version)) > 0 AND length(trim(target_context)) > 0 AND length(trim(field_purpose)) > 0 AND length(trim(source_field)) > 0",
            name="ck_sub_post_chat_message_detections_provenance_present",
        ),
        sa.CheckConstraint(
            "length(trim(rule_key)) > 0",
            name="ck_sub_post_chat_message_detections_rule_key_present",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(matched_rule_versions) = 'array' AND jsonb_array_length(matched_rule_versions) BETWEEN 1 AND 32",
            name="ck_sub_post_chat_message_detections_rule_versions_nonempty",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(declared_limits) = 'array' AND jsonb_array_length(declared_limits) BETWEEN 1 AND 16",
            name="ck_sub_post_chat_message_detections_declared_limits_nonempty",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(evidence) = 'object' "
            "AND jsonb_typeof(evidence->'evidence_kind') = 'string' "
            "AND COALESCE(evidence->>'evidence_kind', '') "
            "IN ('span', 'context_predicate')",
            name="ck_sub_post_chat_message_detections_evidence_shape",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"], ["sub_post_chat_messages.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "message_id",
            "detection_identity_hash",
            name="uq_sub_post_chat_message_detections_message_identity",
        ),
    )
    op.create_index(
        "ix_sub_post_chat_message_detections_category",
        "sub_post_chat_message_detections",
        ["category"],
        unique=False,
    )
    op.create_index(
        "ix_sub_post_chat_message_detections_created_at",
        "sub_post_chat_message_detections",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_sub_post_chat_message_detections_message_id",
        "sub_post_chat_message_detections",
        ["message_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("sub_post_chat_message_detections")
