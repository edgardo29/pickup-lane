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
                "moderation_status IN ("
                "'visible', 'hidden_by_admin', 'removed_by_admin', "
                "'deleted_by_sender', 'flagged'"
                ")"
            ),
            name="ck_sub_post_chat_messages_moderation_status",
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
                "(moderation_status <> 'deleted_by_sender' "
                "OR deleted_at IS NOT NULL)"
            ),
            name="ck_sub_post_chat_messages_deleted_requires_deleted_at",
        ),
        CheckConstraint(
            (
                "(moderation_status <> 'hidden_by_admin' "
                "OR deleted_at IS NOT NULL)"
            ),
            name="ck_sub_post_chat_messages_hidden_requires_deleted_at",
        ),
        CheckConstraint(
            (
                "(moderation_status <> 'removed_by_admin' "
                "OR deleted_at IS NOT NULL)"
            ),
            name="ck_sub_post_chat_messages_removed_requires_deleted_at",
        ),
        Index("ix_sub_post_chat_messages_chat_id", "chat_id"),
        Index("ix_sub_post_chat_messages_sender_user_id", "sender_user_id"),
        Index("ix_sub_post_chat_messages_deleted_by_user_id", "deleted_by_user_id"),
        Index("ix_sub_post_chat_messages_moderation_status", "moderation_status"),
        Index(
            "ix_sub_post_chat_messages_chat_id_created_at",
            "chat_id",
            "created_at",
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
