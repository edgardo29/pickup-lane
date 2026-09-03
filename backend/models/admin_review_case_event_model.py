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
                "'finding_attached', 'finding_cleared', "
                "'signal_superseded', 'signal_reactivated', "
                "'note_added', 'assignment_changed', "
                "'enforcement_action_linked', 'closed', 'reopened', "
                "'merged_into', 'merged_from')"
            ),
            name="ck_admin_review_case_events_event_type",
        ),
        CheckConstraint(
            "event_sequence > 0 AND case_version > 0 AND event_sequence = case_version",
            name="ck_admin_review_case_events_sequence_version",
        ),
        CheckConstraint(
            "actor_kind IN ('admin', 'automation')",
            name="ck_admin_review_case_events_actor_kind",
        ),
        CheckConstraint(
            (
                "(actor_kind = 'admin' AND actor_user_id IS NOT NULL "
                "AND automation_rule_id IS NULL AND automation_rule_version IS NULL) "
                "OR (actor_kind = 'automation' AND actor_user_id IS NULL "
                "AND automation_rule_id IS NOT NULL "
                "AND btrim(automation_rule_id) <> '' "
                "AND automation_rule_version IS NOT NULL "
                "AND btrim(automation_rule_version) <> '')"
            ),
            name="ck_admin_review_case_events_actor_shape",
        ),
        CheckConstraint(
            "signal_id IS NULL OR content_moderation_finding_id IS NULL",
            name="ck_admin_review_case_events_one_child_ref",
        ),
        CheckConstraint(
            (
                "(event_type = 'case_created' AND note_id IS NULL "
                "AND related_case_id IS NULL AND related_event_id IS NULL) OR "
                "(event_type IN ('finding_attached', 'finding_cleared') "
                "AND content_moderation_finding_id IS NOT NULL "
                "AND signal_id IS NULL AND note_id IS NULL "
                "AND related_case_id IS NULL AND related_event_id IS NULL) OR "
                "(event_type IN ('signal_attached', 'signal_superseded', "
                "'signal_reactivated') AND signal_id IS NOT NULL "
                "AND content_moderation_finding_id IS NULL AND note_id IS NULL "
                "AND related_case_id IS NULL AND related_event_id IS NULL) OR "
                "(event_type = 'note_added' AND note_id IS NOT NULL "
                "AND signal_id IS NULL "
                "AND content_moderation_finding_id IS NULL "
                "AND related_case_id IS NULL AND related_event_id IS NULL) OR "
                "(event_type IN ('assignment_changed', "
                "'enforcement_action_linked', 'closed') "
                "AND signal_id IS NULL "
                "AND content_moderation_finding_id IS NULL AND note_id IS NULL "
                "AND related_case_id IS NULL AND related_event_id IS NULL) OR "
                "(event_type = 'reopened' AND related_event_id IS NOT NULL "
                "AND signal_id IS NULL "
                "AND content_moderation_finding_id IS NULL AND note_id IS NULL "
                "AND related_case_id IS NULL) OR "
                "(event_type IN ('merged_into', 'merged_from') "
                "AND related_case_id IS NOT NULL AND related_event_id IS NOT NULL "
                "AND signal_id IS NULL "
                "AND content_moderation_finding_id IS NULL AND note_id IS NULL)"
            ),
            name="ck_admin_review_case_events_reference_shape",
        ),
        CheckConstraint(
            (
                "(event_type IN ('case_created', 'finding_attached', "
                "'finding_cleared', 'signal_attached', 'signal_superseded', "
                "'signal_reactivated') AND actor_kind = 'automation') OR "
                "(event_type IN ('note_added', 'assignment_changed', "
                "'enforcement_action_linked', 'reopened', 'merged_into', "
                "'merged_from') AND actor_kind = 'admin' "
                "AND admin_action_id IS NOT NULL) OR "
                "(event_type = 'closed' AND (actor_kind = 'automation' "
                "OR admin_action_id IS NOT NULL))"
            ),
            name="ck_admin_review_case_events_transition_actor",
        ),
        UniqueConstraint(
            "review_case_id",
            "event_sequence",
            name="uq_admin_review_case_events_case_sequence",
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
        Index("ix_admin_review_case_events_related_case_id", "related_case_id"),
        Index("ix_admin_review_case_events_related_event_id", "related_event_id"),
        Index("ix_admin_review_case_events_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    review_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_review_cases.id", ondelete="RESTRICT"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    event_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    case_version: Mapped[int] = mapped_column(Integer, nullable=False)
    actor_kind: Mapped[str] = mapped_column(String(20), nullable=False)
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
    related_case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_review_cases.id", ondelete="RESTRICT"),
        nullable=True,
    )
    related_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_review_case_events.id", ondelete="RESTRICT"),
        nullable=True,
    )
    automation_rule_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    automation_rule_version: Mapped[str | None] = mapped_column(
        String(40), nullable=True
    )
    trigger_actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    event_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
