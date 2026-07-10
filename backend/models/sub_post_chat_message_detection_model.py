import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


# Need a Sub chat message detections store immutable moderation signals found
# during message creation. The message row owns current visibility/review state.
class SubPostChatMessageDetection(Base):
    __tablename__ = "sub_post_chat_message_detections"
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
            name="ck_sub_post_chat_message_detections_category",
        ),
        CheckConstraint(
            "severity IN ('low', 'medium', 'high')",
            name="ck_sub_post_chat_message_detections_severity",
        ),
        Index(
            "ix_sub_post_chat_message_detections_message_id",
            "message_id",
        ),
        Index(
            "ix_sub_post_chat_message_detections_category",
            "category",
        ),
        Index(
            "ix_sub_post_chat_message_detections_created_at",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sub_post_chat_messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    rule_key: Mapped[str] = mapped_column(String(80), nullable=False)
    matched_preview: Mapped[str | None] = mapped_column(String(240), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
