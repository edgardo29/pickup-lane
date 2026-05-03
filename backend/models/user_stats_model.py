import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


# User stats stores cached profile/accountability counts for fast profile display.
# Source-of-truth data remains in participant, history, and game tables.
class UserStats(Base):
    __tablename__ = "user_stats"
    __table_args__ = (
        CheckConstraint(
            "games_played_count >= 0",
            name="ck_user_stats_games_played_count",
        ),
        CheckConstraint(
            "games_hosted_completed_count >= 0",
            name="ck_user_stats_games_hosted_completed_count",
        ),
        CheckConstraint(
            "no_show_count >= 0",
            name="ck_user_stats_no_show_count",
        ),
        CheckConstraint(
            "late_cancel_count >= 0",
            name="ck_user_stats_late_cancel_count",
        ),
        CheckConstraint(
            "host_cancel_count >= 0",
            name="ck_user_stats_host_cancel_count",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    games_played_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )

    games_hosted_completed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )

    no_show_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )

    late_cancel_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )

    host_cancel_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )

    last_calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )