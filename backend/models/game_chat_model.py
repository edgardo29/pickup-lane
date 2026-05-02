import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
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
            "chat_status IN ('active', 'locked', 'archived')",
            name="ck_game_chats_chat_status",
        ),
        CheckConstraint(
            "(chat_status <> 'locked' OR locked_at IS NOT NULL)",
            name="ck_game_chats_locked_requires_locked_at",
        ),
        UniqueConstraint("game_id", name="uq_game_chats_game_id"),
        Index("ix_game_chats_chat_status", "chat_status"),
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
    locked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
