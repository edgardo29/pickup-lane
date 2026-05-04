import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


# Policy documents store versioned legal/policy documents such as terms,
# privacy policy, refund rules, host agreements, and official game rules.
class PolicyDocument(Base):
    __tablename__ = "policy_documents"
    __table_args__ = (
        CheckConstraint(
            (
                "policy_type IN ("
                "'terms_of_service', 'privacy_policy', 'refund_policy', "
                "'player_cancellation_policy', 'host_deposit_policy', "
                "'community_host_agreement', 'official_game_rules'"
                ")"
            ),
            name="ck_policy_documents_policy_type",
        ),
        CheckConstraint(
            "char_length(btrim(version)) > 0",
            name="ck_policy_documents_version_not_empty",
        ),
        CheckConstraint(
            "char_length(btrim(title)) > 0",
            name="ck_policy_documents_title_not_empty",
        ),
        CheckConstraint(
            (
                "(content_url IS NOT NULL AND char_length(btrim(content_url)) > 0) "
                "OR (content_text IS NOT NULL AND char_length(btrim(content_text)) > 0)"
            ),
            name="ck_policy_documents_content_required",
        ),
        CheckConstraint(
            "(retired_at IS NULL OR retired_at > effective_at)",
            name="ck_policy_documents_retired_after_effective",
        ),
        UniqueConstraint(
            "policy_type",
            "version",
            name="uq_policy_documents_policy_type_version",
        ),
        Index("ix_policy_documents_policy_type", "policy_type"),
        Index("ix_policy_documents_is_active", "is_active"),
        Index("ix_policy_documents_effective_at", "effective_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)

    policy_type: Mapped[str] = mapped_column(String(50), nullable=False)

    version: Mapped[str] = mapped_column(String(30), nullable=False)

    title: Mapped[str] = mapped_column(String(150), nullable=False)

    content_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    content_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    effective_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    retired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
