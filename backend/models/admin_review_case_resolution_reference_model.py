import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database_metadata import Base


class AdminReviewCaseResolutionReference(Base):
    __tablename__ = "admin_review_case_resolution_references"
    __table_args__ = (
        CheckConstraint(
            (
                "reference_type IN ("
                "'finding', 'signal', 'enforcement_action', 'source_case')"
            ),
            name="ck_admin_review_case_resolution_refs_type",
        ),
        CheckConstraint(
            (
                "(reference_type = 'finding' "
                "AND content_moderation_finding_id IS NOT NULL "
                "AND signal_id IS NULL AND admin_action_id IS NULL "
                "AND source_case_id IS NULL AND was_current IS NOT NULL) OR "
                "(reference_type = 'signal' AND signal_id IS NOT NULL "
                "AND content_moderation_finding_id IS NULL "
                "AND admin_action_id IS NULL AND source_case_id IS NULL "
                "AND was_current IS NOT NULL) OR "
                "(reference_type = 'enforcement_action' "
                "AND admin_action_id IS NOT NULL "
                "AND content_moderation_finding_id IS NULL AND signal_id IS NULL "
                "AND source_case_id IS NULL AND was_current IS NULL) OR "
                "(reference_type = 'source_case' AND source_case_id IS NOT NULL "
                "AND content_moderation_finding_id IS NULL AND signal_id IS NULL "
                "AND admin_action_id IS NULL AND was_current IS NULL)"
            ),
            name="ck_admin_review_case_resolution_refs_shape",
        ),
        UniqueConstraint(
            "closure_event_id",
            "content_moderation_finding_id",
            name="uq_admin_review_case_resolution_refs_finding",
        ),
        UniqueConstraint(
            "closure_event_id",
            "signal_id",
            name="uq_admin_review_case_resolution_refs_signal",
        ),
        UniqueConstraint(
            "closure_event_id",
            "admin_action_id",
            name="uq_admin_review_case_resolution_refs_action",
        ),
        UniqueConstraint(
            "closure_event_id",
            "source_case_id",
            name="uq_admin_review_case_resolution_refs_source_case",
        ),
        Index(
            "ix_admin_review_case_resolution_refs_closure_event_id",
            "closure_event_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    closure_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_review_case_events.id", ondelete="RESTRICT"),
        nullable=False,
    )
    reference_type: Mapped[str] = mapped_column(String(30), nullable=False)
    content_moderation_finding_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_content_moderation_findings.id", ondelete="RESTRICT"),
        nullable=True,
    )
    signal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_review_signals.id", ondelete="RESTRICT"),
        nullable=True,
    )
    admin_action_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_actions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    source_case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_review_cases.id", ondelete="RESTRICT"),
        nullable=True,
    )
    was_current: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
