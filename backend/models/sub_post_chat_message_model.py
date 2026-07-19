import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


# Sub post chat messages are intentionally narrower than game chat messages:
# v1 is text-only logistics chat with sender snapshots for durable history.
class SubPostChatMessage(Base):
    __tablename__ = "sub_post_chat_messages"
    __table_args__ = (
        CheckConstraint(
            "message_type IN ('text')",
            name="ck_sub_post_chat_messages_message_type",
        ),
        CheckConstraint(
            (
                "visibility_status IN ('visible', 'removed')"
            ),
            name="ck_sub_post_chat_messages_visibility_status",
        ),
        CheckConstraint(
            "review_status IN ('clear', 'needs_review', 'reviewed')",
            name="ck_sub_post_chat_messages_review_status",
        ),
        CheckConstraint(
            (
                "removed_source IS NULL "
                "OR removed_source IN ('admin', 'sender', 'system')"
            ),
            name="ck_sub_post_chat_messages_removed_source",
        ),
        CheckConstraint(
            "char_length(btrim(message_body)) > 0",
            name="ck_sub_post_chat_messages_body_not_empty",
        ),
        CheckConstraint(
            "char_length(message_body) <= 300",
            name="ck_sub_post_chat_messages_body_max_length",
        ),
        CheckConstraint(
            "char_length(btrim(sender_display_name_snapshot)) > 0",
            name="ck_sub_post_chat_messages_sender_name_not_empty",
        ),
        CheckConstraint(
            "char_length(btrim(sender_initials_snapshot)) > 0",
            name="ck_sub_post_chat_messages_sender_initials_not_empty",
        ),
        CheckConstraint(
            (
                "(visibility_status <> 'removed' "
                "OR removed_at IS NOT NULL)"
            ),
            name="ck_sub_post_chat_messages_removed_requires_removed_at",
        ),
        CheckConstraint(
            (
                "(visibility_status <> 'removed' "
                "OR removed_source IS NOT NULL)"
            ),
            name="ck_sub_post_chat_messages_removed_requires_source",
        ),
        CheckConstraint(
            (
                "(review_status <> 'reviewed' "
                "OR reviewed_at IS NOT NULL)"
            ),
            name="ck_sub_post_chat_messages_reviewed_requires_reviewed_at",
        ),
        Index("ix_sub_post_chat_messages_chat_id", "chat_id"),
        Index("ix_sub_post_chat_messages_sender_user_id", "sender_user_id"),
        Index("ix_sub_post_chat_messages_removed_by_user_id", "removed_by_user_id"),
        Index("ix_sub_post_chat_messages_reviewed_by_user_id", "reviewed_by_user_id"),
        Index("ix_sub_post_chat_messages_restored_by_user_id", "restored_by_user_id"),
        Index("ix_sub_post_chat_messages_visibility_status", "visibility_status"),
        Index("ix_sub_post_chat_messages_review_status", "review_status"),
        Index(
            "ix_sub_post_chat_messages_chat_id_created_at",
            "chat_id",
            "created_at",
        ),
        Index(
            "ix_sub_post_chat_messages_chat_id_review_status",
            "chat_id",
            "review_status",
        ),
        Index(
            "ix_sub_post_chat_messages_chat_id_visibility_status",
            "chat_id",
            "visibility_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)

    chat_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sub_post_chats.id", ondelete="RESTRICT"),
        nullable=False,
    )

    sender_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    sender_display_name_snapshot: Mapped[str] = mapped_column(
        String(120), nullable=False
    )

    sender_initials_snapshot: Mapped[str] = mapped_column(String(8), nullable=False)

    message_type: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'text'")
    )

    message_body: Mapped[str] = mapped_column(Text, nullable=False)

    visibility_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'visible'")
    )

    review_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'clear'")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    removed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    removed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    removed_source: Mapped[str | None] = mapped_column(String(30), nullable=True)

    removed_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    restored_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    restored_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    restored_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
