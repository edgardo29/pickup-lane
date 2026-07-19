import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
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


# Chat messages store individual messages inside a game chat room, including
# player messages, system messages, pinned updates, visibility state, and review
# state.
class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        CheckConstraint(
            "message_type IN ('text', 'system', 'pinned_update')",
            name="ck_chat_messages_message_type",
        ),
        CheckConstraint(
            (
                "visibility_status IN ('visible', 'removed')"
            ),
            name="ck_chat_messages_visibility_status",
        ),
        CheckConstraint(
            "review_status IN ('clear', 'needs_review', 'reviewed')",
            name="ck_chat_messages_review_status",
        ),
        CheckConstraint(
            (
                "removed_source IS NULL "
                "OR removed_source IN ('admin', 'sender', 'system')"
            ),
            name="ck_chat_messages_removed_source",
        ),
        CheckConstraint(
            "char_length(btrim(message_body)) > 0",
            name="ck_chat_messages_message_body_not_empty",
        ),
        CheckConstraint(
            "char_length(message_body) <= 300",
            name="ck_chat_messages_message_body_max_length",
        ),
        CheckConstraint(
            "(is_pinned = false OR pinned_at IS NOT NULL)",
            name="ck_chat_messages_pinned_requires_pinned_at",
        ),
        CheckConstraint(
            "(is_pinned = false OR pinned_by_user_id IS NOT NULL)",
            name="ck_chat_messages_pinned_requires_pinned_by_user",
        ),
        CheckConstraint(
            (
                "(visibility_status <> 'removed' "
                "OR removed_at IS NOT NULL)"
            ),
            name="ck_chat_messages_removed_requires_removed_at",
        ),
        CheckConstraint(
            (
                "(visibility_status <> 'removed' "
                "OR removed_source IS NOT NULL)"
            ),
            name="ck_chat_messages_removed_requires_source",
        ),
        CheckConstraint(
            (
                "(review_status <> 'reviewed' "
                "OR reviewed_at IS NOT NULL)"
            ),
            name="ck_chat_messages_reviewed_requires_reviewed_at",
        ),
        CheckConstraint(
            (
                "(message_type NOT IN ('text', 'pinned_update') "
                "OR sender_user_id IS NOT NULL)"
            ),
            name="ck_chat_messages_user_messages_require_sender",
        ),
        Index("ix_chat_messages_chat_id", "chat_id"),
        Index("ix_chat_messages_sender_user_id", "sender_user_id"),
        Index("ix_chat_messages_pinned_by_user_id", "pinned_by_user_id"),
        Index("ix_chat_messages_removed_by_user_id", "removed_by_user_id"),
        Index("ix_chat_messages_reviewed_by_user_id", "reviewed_by_user_id"),
        Index("ix_chat_messages_restored_by_user_id", "restored_by_user_id"),
        Index("ix_chat_messages_visibility_status", "visibility_status"),
        Index("ix_chat_messages_review_status", "review_status"),
        Index("ix_chat_messages_chat_id_created_at", "chat_id", "created_at"),
        Index("ix_chat_messages_chat_id_review_status", "chat_id", "review_status"),
        Index(
            "ix_chat_messages_chat_id_visibility_status",
            "chat_id",
            "visibility_status",
        ),
        Index("ix_chat_messages_chat_id_is_pinned", "chat_id", "is_pinned"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)

    chat_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("game_chats.id", ondelete="RESTRICT"),
        nullable=False,
    )

    sender_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    message_type: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'text'")
    )

    message_body: Mapped[str] = mapped_column(Text, nullable=False)

    is_pinned: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )

    pinned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    pinned_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

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
