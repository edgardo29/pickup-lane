import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database_metadata import Base


# Game chat message detections store immutable moderation signals found during
# message creation. The message row owns current visibility/review state.
class GameChatMessageDetection(Base):
    __tablename__ = "game_chat_message_detections"
    __table_args__ = (
        CheckConstraint(
            (
                "category IN ("
                "'phone_number', 'email', 'link', 'off_platform_contact', "
                "'payment_discussion', 'harassment_or_abuse', "
                "'threat_or_safety', 'slur_or_hate', "
                "'spam_or_repeated_message'"
                ")"
            ),
            name="ck_game_chat_message_detections_category",
        ),
        CheckConstraint(
            "severity IN ('low', 'medium', 'high')",
            name="ck_game_chat_message_detections_severity",
        ),
        CheckConstraint(
            "configuration_hash ~ '^[0-9a-f]{64}$'",
            name="ck_game_chat_message_detections_configuration_hash",
        ),
        CheckConstraint(
            "source_content_hash ~ '^[0-9a-f]{64}$'",
            name="ck_game_chat_message_detections_source_hash",
        ),
        CheckConstraint(
            "evidence_fingerprint ~ '^[0-9a-f]{64}$'",
            name="ck_game_chat_message_detections_evidence_fingerprint",
        ),
        CheckConstraint(
            "detection_identity_hash ~ '^[0-9a-f]{64}$'",
            name="ck_game_chat_message_detections_identity_hash",
        ),
        CheckConstraint(
            "execution_duration_us >= 0",
            name="ck_game_chat_message_detections_duration_nonnegative",
        ),
        CheckConstraint(
            "length(trim(scanner_id)) > 0 "
            "AND length(trim(scanner_version)) > 0 "
            "AND length(trim(taxonomy_version)) > 0 "
            "AND length(trim(canonicalization_version)) > 0 "
            "AND length(trim(evidence_format_version)) > 0 "
            "AND length(trim(target_context)) > 0 "
            "AND length(trim(field_purpose)) > 0 "
            "AND length(trim(source_field)) > 0",
            name="ck_game_chat_message_detections_provenance_present",
        ),
        CheckConstraint(
            "length(trim(rule_key)) > 0",
            name="ck_game_chat_message_detections_rule_key_present",
        ),
        CheckConstraint(
            "jsonb_typeof(matched_rule_versions) = 'array' "
            "AND jsonb_array_length(matched_rule_versions) BETWEEN 1 AND 32",
            name="ck_game_chat_message_detections_rule_versions_nonempty",
        ),
        CheckConstraint(
            "jsonb_typeof(declared_limits) = 'array' "
            "AND jsonb_array_length(declared_limits) BETWEEN 1 AND 16",
            name="ck_game_chat_message_detections_declared_limits_nonempty",
        ),
        CheckConstraint(
            "jsonb_typeof(evidence) = 'object' "
            "AND jsonb_typeof(evidence->'evidence_kind') = 'string' "
            "AND COALESCE(evidence->>'evidence_kind', '') "
            "IN ('span', 'context_predicate')",
            name="ck_game_chat_message_detections_evidence_shape",
        ),
        UniqueConstraint(
            "message_id",
            "detection_identity_hash",
            name="uq_game_chat_message_detections_message_identity",
        ),
        Index(
            "ix_game_chat_message_detections_message_id",
            "message_id",
        ),
        Index(
            "ix_game_chat_message_detections_category",
            "category",
        ),
        Index(
            "ix_game_chat_message_detections_created_at",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    rule_key: Mapped[str] = mapped_column(String(80), nullable=False)
    matched_preview: Mapped[str | None] = mapped_column(String(240), nullable=True)
    scanner_id: Mapped[str] = mapped_column(String(80), nullable=False)
    scanner_version: Mapped[str] = mapped_column(String(80), nullable=False)
    taxonomy_version: Mapped[str] = mapped_column(String(40), nullable=False)
    configuration_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    canonicalization_version: Mapped[str] = mapped_column(String(80), nullable=False)
    evidence_format_version: Mapped[str] = mapped_column(String(40), nullable=False)
    target_context: Mapped[str] = mapped_column(String(60), nullable=False)
    field_purpose: Mapped[str] = mapped_column(String(40), nullable=False)
    source_field: Mapped[str] = mapped_column(String(80), nullable=False)
    source_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    matched_rule_versions: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    declared_limits: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    evidence_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=False)
    scanned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    execution_duration_us: Mapped[int] = mapped_column(BigInteger, nullable=False)
    detection_identity_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
