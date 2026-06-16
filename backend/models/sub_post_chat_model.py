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


# Sub post chats are one scoped logistics chat room attached to one Need a Sub
# post. They are separate from game_chats so the game chat implementation stays
# isolated.
class SubPostChat(Base):
    __tablename__ = "sub_post_chats"
    __table_args__ = (
        CheckConstraint(
            "chat_status IN ('active', 'closed', 'archived')",
            name="ck_sub_post_chats_chat_status",
        ),
        CheckConstraint(
            "(chat_status = 'active' OR closed_at IS NOT NULL)",
            name="ck_sub_post_chats_closed_requires_closed_at",
        ),
        UniqueConstraint("sub_post_id", name="uq_sub_post_chats_sub_post_id"),
        Index("ix_sub_post_chats_sub_post_id", "sub_post_id"),
        Index("ix_sub_post_chats_chat_status", "chat_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    sub_post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sub_posts.id", ondelete="RESTRICT"),
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
