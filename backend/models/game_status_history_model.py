import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


# Game status history stores append-only lifecycle audit rows for publish and
# gameplay status changes on a game.
class GameStatusHistory(Base):
    __tablename__ = "game_status_history"
    __table_args__ = (
        CheckConstraint(
            (
                "(old_publish_status IS NULL OR old_publish_status IN "
                "('draft', 'published', 'archived'))"
            ),
            name="ck_game_status_history_old_publish_status",
        ),
        CheckConstraint(
            "new_publish_status IN ('draft', 'published', 'archived')",
            name="ck_game_status_history_new_publish_status",
        ),
        CheckConstraint(
            (
                "(old_game_status IS NULL OR old_game_status IN "
                "('scheduled', 'full', 'cancelled', 'completed', 'abandoned'))"
            ),
            name="ck_game_status_history_old_game_status",
        ),
        CheckConstraint(
            (
                "new_game_status IN "
                "('scheduled', 'full', 'cancelled', 'completed', 'abandoned')"
            ),
            name="ck_game_status_history_new_game_status",
        ),
        CheckConstraint(
            (
                "change_source IN ("
                "'user', 'host', 'admin', 'system', 'payment_webhook', "
                "'scheduled_job'"
                ")"
            ),
            name="ck_game_status_history_change_source",
        ),
        Index("ix_game_status_history_game_id", "game_id"),
        Index("ix_game_status_history_changed_by_user_id", "changed_by_user_id"),
        Index("ix_game_status_history_change_source", "change_source"),
        Index("ix_game_status_history_created_at", "created_at"),
        Index("ix_game_status_history_game_id_created_at", "game_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)

    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
    )

    old_publish_status: Mapped[str | None] = mapped_column(String(30), nullable=True)

    new_publish_status: Mapped[str] = mapped_column(String(30), nullable=False)

    old_game_status: Mapped[str | None] = mapped_column(String(30), nullable=True)

    new_game_status: Mapped[str] = mapped_column(String(30), nullable=False)

    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    change_source: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'user'")
    )

    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
