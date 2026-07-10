import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


# Game chats represent the single chat room attached to a game. Message and
# moderation details live outside this room-level table.
class GameChat(Base):
    __tablename__ = "game_chats"
    __table_args__ = (
        CheckConstraint(
            "chat_status IN ('active', 'closed')",
            name="ck_game_chats_chat_status",
        ),
        CheckConstraint(
            (
                "(chat_status = 'active' AND closed_at IS NULL) "
                "OR (chat_status = 'closed' AND closed_at IS NOT NULL)"
            ),
            name="ck_game_chats_closed_requires_closed_at",
        ),
        UniqueConstraint("game_id", name="uq_game_chats_game_id"),
        Index("ix_game_chats_chat_status", "chat_status"),
        Index("ix_game_chats_latest_message_at", "latest_message_at"),
        Index("ix_game_chats_needs_review_count", "needs_review_count"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="RESTRICT"),
        nullable=False,
    )
    chat_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'active'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    message_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    needs_review_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    removed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    latest_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    latest_message_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    latest_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
