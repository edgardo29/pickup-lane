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
# player messages, system messages, pinned updates, and moderation state.
class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        CheckConstraint(
            "message_type IN ('text', 'system', 'pinned_update')",
            name="ck_chat_messages_message_type",
        ),
        CheckConstraint(
            (
                "moderation_status IN ("
                "'visible', 'hidden_by_admin', 'deleted_by_sender', 'flagged'"
                ")"
            ),
            name="ck_chat_messages_moderation_status",
        ),
        CheckConstraint(
            "char_length(btrim(message_body)) > 0",
            name="ck_chat_messages_message_body_not_empty",
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
                "(moderation_status <> 'deleted_by_sender' "
                "OR deleted_at IS NOT NULL)"
            ),
            name="ck_chat_messages_deleted_by_sender_requires_deleted_at",
        ),
        CheckConstraint(
            (
                "(moderation_status <> 'hidden_by_admin' "
                "OR deleted_at IS NOT NULL)"
            ),
            name="ck_chat_messages_hidden_by_admin_requires_deleted_at",
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
        Index("ix_chat_messages_deleted_by_user_id", "deleted_by_user_id"),
        Index("ix_chat_messages_moderation_status", "moderation_status"),
        Index("ix_chat_messages_chat_id_created_at", "chat_id", "created_at"),
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

    moderation_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'visible'")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    edited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    deleted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )