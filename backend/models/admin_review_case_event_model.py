import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database_metadata import Base


class AdminReviewCaseEvent(Base):
    __tablename__ = "admin_review_case_events"
    __table_args__ = (
        CheckConstraint(
            (
                "event_type IN ("
                "'case_created', 'signal_attached', "
                "'signal_superseded', 'signal_reactivated', "
                "'finding_attached', 'finding_cleared', "
                "'note_added', 'enforcement_action_linked', "
                "'closed')"
            ),
            name="ck_admin_review_case_events_event_type",
        ),
        CheckConstraint(
            (
                "(event_type = 'case_created' "
                "AND signal_id IS NULL "
                "AND content_moderation_finding_id IS NULL "
                "AND note_id IS NULL "
                "AND admin_action_id IS NULL) "
                "OR (event_type IN ('signal_attached', 'signal_superseded', "
                "'signal_reactivated') "
                "AND signal_id IS NOT NULL "
                "AND content_moderation_finding_id IS NULL "
                "AND note_id IS NULL "
                "AND admin_action_id IS NULL) "
                "OR (event_type IN ('finding_attached', 'finding_cleared') "
                "AND signal_id IS NULL "
                "AND content_moderation_finding_id IS NOT NULL "
                "AND note_id IS NULL "
                "AND admin_action_id IS NULL) "
                "OR (event_type = 'note_added' "
                "AND signal_id IS NULL "
                "AND content_moderation_finding_id IS NULL "
                "AND note_id IS NOT NULL "
                "AND admin_action_id IS NOT NULL) "
                "OR (event_type = 'enforcement_action_linked' "
                "AND signal_id IS NULL "
                "AND content_moderation_finding_id IS NULL "
                "AND note_id IS NULL "
                "AND admin_action_id IS NOT NULL) "
                "OR (event_type = 'closed' "
                "AND signal_id IS NULL "
                "AND content_moderation_finding_id IS NULL "
                "AND note_id IS NULL)"
            ),
            name="ck_admin_review_case_events_reference_shape",
        ),
        CheckConstraint(
            "case_version > 0",
            name="ck_admin_review_case_events_case_version_positive",
        ),
        CheckConstraint(
            "event_type = 'closed' OR event_metadata IS NULL",
            name="ck_admin_review_case_events_metadata_scope",
        ),
        UniqueConstraint(
            "review_case_id",
            "case_version",
            name="uq_admin_review_case_events_case_version",
        ),
        Index("ix_admin_review_case_events_review_case_id", "review_case_id"),
        Index("ix_admin_review_case_events_event_type", "event_type"),
        Index("ix_admin_review_case_events_actor_user_id", "actor_user_id"),
        Index("ix_admin_review_case_events_admin_action_id", "admin_action_id"),
        Index("ix_admin_review_case_events_signal_id", "signal_id"),
        Index(
            "ix_admin_review_case_events_content_moderation_finding_id",
            "content_moderation_finding_id",
        ),
        Index("ix_admin_review_case_events_note_id", "note_id"),
        Index("ix_admin_review_case_events_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    review_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_review_cases.id", ondelete="RESTRICT"),
        nullable=False,
    )
    case_version: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    admin_action_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_actions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    signal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_review_signals.id", ondelete="RESTRICT"),
        nullable=True,
    )
    content_moderation_finding_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_content_moderation_findings.id", ondelete="RESTRICT"),
        nullable=True,
    )
    note_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_review_case_notes.id", ondelete="RESTRICT"),
        nullable=True,
    )
    event_metadata: Mapped[dict | None] = mapped_column(
        JSONB(none_as_null=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
