import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class SubPostRequestStatusHistory(Base):
    __tablename__ = "sub_post_request_status_history"
    __table_args__ = (
        CheckConstraint(
            (
                "new_status IN ('pending', 'confirmed', 'declined', "
                "'sub_waitlist', 'canceled_by_player', 'canceled_by_owner', "
                "'no_show_reported', 'expired')"
            ),
            name="ck_sub_post_request_status_history_new_status",
        ),
        CheckConstraint(
            (
                "old_status IS NULL OR old_status IN ('pending', 'confirmed', "
                "'declined', 'sub_waitlist', 'canceled_by_player', "
                "'canceled_by_owner', 'no_show_reported', 'expired')"
            ),
            name="ck_sub_post_request_status_history_old_status",
        ),
        CheckConstraint(
            (
                "change_source IN ('requester', 'owner', 'admin', 'system', "
                "'scheduled_job')"
            ),
            name="ck_sub_post_request_status_history_change_source",
        ),
        Index(
            "ix_sub_post_request_status_history_request_created",
            "sub_post_request_id",
            "created_at",
        ),
        Index(
            "ix_sub_post_request_status_history_changed_by_user_id",
            "changed_by_user_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    sub_post_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sub_post_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    old_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    new_status: Mapped[str] = mapped_column(String(30), nullable=False)
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    change_source: Mapped[str] = mapped_column(String(30), nullable=False)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
