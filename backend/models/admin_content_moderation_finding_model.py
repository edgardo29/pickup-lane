import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database_metadata import Base


class AdminContentModerationFinding(Base):
    __tablename__ = "admin_content_moderation_findings"
    __table_args__ = (
        CheckConstraint(
            "risk_area IN ('unsafe_post_text', 'unsafe_payment_text')",
            name="ck_admin_content_moderation_findings_risk_area",
        ),
        CheckConstraint(
            (
                "finding_type IN ("
                "'off_app_contact', 'payment_pressure', 'spam_or_scam', "
                "'threat_or_violence', 'harassment_or_abuse', "
                "'slur_or_hate', 'sexual_or_explicit')"
            ),
            name="ck_admin_content_moderation_findings_finding_type",
        ),
        CheckConstraint(
            "priority IN ('attention', 'urgent', 'critical')",
            name="ck_admin_content_moderation_findings_priority",
        ),
        CheckConstraint(
            "length(trim(source_field)) > 0",
            name="ck_admin_content_moderation_findings_source_field_present",
        ),
        CheckConstraint(
            "source_content_hash ~ '^[0-9a-f]{64}$'",
            name="ck_admin_content_moderation_findings_source_hash_present",
        ),
        CheckConstraint(
            "evidence_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_admin_content_moderation_findings_fingerprint_present",
        ),
        CheckConstraint(
            "configuration_hash ~ '^[0-9a-f]{64}$'",
            name="ck_admin_content_moderation_findings_configuration_hash",
        ),
        CheckConstraint(
            "finding_identity_hash ~ '^[0-9a-f]{64}$'",
            name="ck_admin_content_moderation_findings_identity_hash",
        ),
        CheckConstraint(
            "jsonb_typeof(evidence) = 'array' "
            "AND jsonb_array_length(evidence) BETWEEN 1 AND 8",
            name="ck_admin_content_moderation_findings_evidence_nonempty",
        ),
        CheckConstraint(
            "length(trim(scanner_id)) > 0 "
            "AND length(trim(scanner_version)) > 0 "
            "AND length(trim(taxonomy_version)) > 0 "
            "AND length(trim(canonicalization_version)) > 0 "
            "AND length(trim(evidence_format_version)) > 0 "
            "AND length(trim(target_context)) > 0 "
            "AND length(trim(field_purpose)) > 0",
            name="ck_admin_content_moderation_findings_provenance_present",
        ),
        CheckConstraint(
            (
                "(current_match = true AND cleared_at IS NULL) "
                "OR (current_match = false AND cleared_at IS NOT NULL)"
            ),
            name="ck_admin_content_moderation_findings_current_clear_state",
        ),
        CheckConstraint(
            "first_detected_at <= last_detected_at",
            name="ck_admin_content_moderation_findings_detected_order",
        ),
        CheckConstraint(
            "execution_duration_us >= 0",
            name="ck_admin_content_moderation_findings_duration_nonnegative",
        ),
        CheckConstraint(
            "jsonb_typeof(matched_rule_versions) = 'array' "
            "AND jsonb_array_length(matched_rule_versions) BETWEEN 1 AND 32",
            name="ck_admin_content_moderation_findings_rule_versions_nonempty",
        ),
        CheckConstraint(
            "jsonb_typeof(declared_limits) = 'array' "
            "AND jsonb_array_length(declared_limits) BETWEEN 1 AND 16",
            name="ck_admin_content_moderation_findings_declared_limits_nonempty",
        ),
        Index(
            "ix_admin_content_moderation_findings_review_case_id",
            "review_case_id",
        ),
        Index(
            "ix_admin_content_moderation_findings_current_match",
            "current_match",
        ),
        Index(
            "ix_admin_content_moderation_findings_finding_type",
            "finding_type",
        ),
        Index(
            "ix_admin_content_moderation_findings_case_current_type",
            "review_case_id",
            "current_match",
            "finding_type",
        ),
        Index(
            "uq_admin_content_moderation_findings_current_identity",
            "review_case_id",
            "finding_identity_hash",
            unique=True,
            postgresql_where=text("current_match = true"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    review_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_review_cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    risk_area: Mapped[str] = mapped_column(String(60), nullable=False)
    finding_type: Mapped[str] = mapped_column(String(60), nullable=False)
    priority: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default=text("'attention'"),
    )
    source_field: Mapped[str] = mapped_column(String(80), nullable=False)
    source_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    scanner_id: Mapped[str] = mapped_column(String(80), nullable=False)
    taxonomy_version: Mapped[str] = mapped_column(String(40), nullable=False)
    configuration_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    canonicalization_version: Mapped[str] = mapped_column(String(80), nullable=False)
    evidence_format_version: Mapped[str] = mapped_column(String(40), nullable=False)
    target_context: Mapped[str] = mapped_column(String(60), nullable=False)
    field_purpose: Mapped[str] = mapped_column(String(40), nullable=False)
    matched_rule_versions: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    declared_limits: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    scanned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    execution_duration_us: Mapped[int] = mapped_column(BigInteger, nullable=False)
    finding_identity_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    current_match: Mapped[bool] = mapped_column(
        nullable=False,
        server_default=text("true"),
    )
    first_detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    last_detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    cleared_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    scanner_version: Mapped[str] = mapped_column(String(80), nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
