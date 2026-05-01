import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


# This table tracks users waiting for game spots and the short promotion window
# when a spot opens before the waitlist entry reaches a final lifecycle state.
class WaitlistEntry(Base):
    __tablename__ = "waitlist_entries"
    __table_args__ = (
        CheckConstraint(
            (
                "waitlist_status IN ("
                "'active', 'promoted', 'accepted', 'declined', 'expired', "
                "'cancelled', 'removed'"
                ")"
            ),
            name="ck_waitlist_entries_waitlist_status",
        ),
        CheckConstraint(
            "party_size > 0",
            name="ck_waitlist_entries_party_size",
        ),
        CheckConstraint(
            "position > 0",
            name="ck_waitlist_entries_position",
        ),
        CheckConstraint(
            "(waitlist_status <> 'promoted' OR promoted_at IS NOT NULL)",
            name="ck_waitlist_entries_promoted_requires_promoted_at",
        ),
        CheckConstraint(
            "(waitlist_status <> 'promoted' OR promotion_expires_at IS NOT NULL)",
            name="ck_waitlist_entries_promoted_requires_promotion_expires_at",
        ),
        CheckConstraint(
            "(waitlist_status <> 'cancelled' OR cancelled_at IS NOT NULL)",
            name="ck_waitlist_entries_cancelled_requires_cancelled_at",
        ),
        CheckConstraint(
            "(waitlist_status <> 'expired' OR expired_at IS NOT NULL)",
            name="ck_waitlist_entries_expired_requires_expired_at",
        ),
        Index("ix_waitlist_entries_game_id", "game_id"),
        Index("ix_waitlist_entries_user_id", "user_id"),
        Index("ix_waitlist_entries_waitlist_status", "waitlist_status"),
        Index(
            "ix_waitlist_entries_game_id_waitlist_status_position",
            "game_id",
            "waitlist_status",
            "position",
        ),
        Index(
            "ix_waitlist_entries_user_id_waitlist_status",
            "user_id",
            "waitlist_status",
        ),
        Index(
            "ux_waitlist_entries_active_user_per_game",
            "game_id",
            "user_id",
            unique=True,
            postgresql_where=text("waitlist_status = 'active'"),
        ),
        Index(
            "ux_waitlist_entries_active_position_per_game",
            "game_id",
            "position",
            unique=True,
            postgresql_where=text("waitlist_status = 'active'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="RESTRICT"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    party_size: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1")
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    waitlist_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'active'")
    )
    promoted_booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="SET NULL"),
        nullable=True,
    )
    promotion_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    promoted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
