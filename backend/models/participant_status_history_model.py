import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


# Participant status history stores append-only audit rows for participant
# lifecycle and attendance status changes.
class ParticipantStatusHistory(Base):
    __tablename__ = "participant_status_history"
    __table_args__ = (
        CheckConstraint(
            (
                "(old_participant_status IS NULL OR old_participant_status IN ("
                "'pending_payment', 'confirmed', 'waitlisted', 'cancelled', "
                "'late_cancelled', 'removed', 'refunded'))"
            ),
            name="ck_participant_status_history_old_participant_status",
        ),
        CheckConstraint(
            (
                "new_participant_status IN ("
                "'pending_payment', 'confirmed', 'waitlisted', 'cancelled', "
                "'late_cancelled', 'removed', 'refunded'"
                ")"
            ),
            name="ck_participant_status_history_new_participant_status",
        ),
        CheckConstraint(
            (
                "(old_attendance_status IS NULL OR old_attendance_status IN ("
                "'unknown', 'attended', 'no_show', 'excused_absence', "
                "'not_applicable'))"
            ),
            name="ck_participant_status_history_old_attendance_status",
        ),
        CheckConstraint(
            (
                "(new_attendance_status IS NULL OR new_attendance_status IN ("
                "'unknown', 'attended', 'no_show', 'excused_absence', "
                "'not_applicable'))"
            ),
            name="ck_participant_status_history_new_attendance_status",
        ),
        CheckConstraint(
            (
                "change_source IN ("
                "'user', 'host', 'admin', 'system', 'payment_webhook', "
                "'scheduled_job'"
                ")"
            ),
            name="ck_participant_status_history_change_source",
        ),
        Index("ix_participant_status_history_participant_id", "participant_id"),
        Index(
            "ix_participant_status_history_changed_by_user_id",
            "changed_by_user_id",
        ),
        Index("ix_participant_status_history_change_source", "change_source"),
        Index("ix_participant_status_history_created_at", "created_at"),
        Index(
            "ix_participant_status_history_participant_id_created_at",
            "participant_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)

    participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("game_participants.id", ondelete="CASCADE"),
        nullable=False,
    )

    old_participant_status: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )

    new_participant_status: Mapped[str] = mapped_column(String(30), nullable=False)

    old_attendance_status: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )

    new_attendance_status: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )

    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    change_source: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'system'")
    )

    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )