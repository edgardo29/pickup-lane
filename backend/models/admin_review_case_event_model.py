import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class AdminReviewCaseEvent(Base):
    __tablename__ = "admin_review_case_events"
    __table_args__ = (
        CheckConstraint(
            (
                "event_type IN ("
                "'case_created', 'signal_attached', "
                "'finding_attached', 'finding_cleared', "
                "'note_added', 'enforcement_action_linked', "
                "'closed')"
            ),
            name="ck_admin_review_case_events_event_type",
        ),
        CheckConstraint(
            "signal_id IS NULL OR content_moderation_finding_id IS NULL",
            name="ck_admin_review_case_events_one_child_ref",
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
        ForeignKey("admin_review_cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    admin_action_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_actions.id", ondelete="SET NULL"),
        nullable=True,
    )
    signal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_review_signals.id", ondelete="SET NULL"),
        nullable=True,
    )
    content_moderation_finding_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_content_moderation_findings.id", ondelete="SET NULL"),
        nullable=True,
    )
    note_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_review_case_notes.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
