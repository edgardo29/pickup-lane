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


# Notifications store inbox/activity feed records for one user and may point
# back to the game, booking, participant, or chat message that caused them.
class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(
            (
                "notification_type IN ("
                "'booking_confirmed', 'booking_cancelled', 'booking_refunded', "
                "'payment_failed', 'game_cancelled', 'game_updated', "
                "'game_reminder', 'waitlist_joined', 'waitlist_promoted', "
                "'waitlist_expired', 'host_update', 'chat_message', "
                "'deposit_paid', 'deposit_released', 'deposit_forfeited', "
                "'admin_notice'"
                ")"
            ),
            name="ck_notifications_notification_type",
        ),
        CheckConstraint(
            "char_length(btrim(title)) > 0",
            name="ck_notifications_title_not_empty",
        ),
        CheckConstraint(
            "char_length(btrim(body)) > 0",
            name="ck_notifications_body_not_empty",
        ),
        CheckConstraint(
            "((is_read = true AND read_at IS NOT NULL) "
            "OR (is_read = false AND read_at IS NULL))",
            name="ck_notifications_read_state_matches_read_at",
        ),
        Index("ix_notifications_user_id", "user_id"),
        Index("ix_notifications_notification_type", "notification_type"),
        Index("ix_notifications_is_read", "is_read"),
        Index("ix_notifications_created_at", "created_at"),
        Index(
            "ix_notifications_user_id_is_read_created_at",
            "user_id",
            "is_read",
            "created_at",
        ),
        Index("ix_notifications_related_game_id", "related_game_id"),
        Index("ix_notifications_related_booking_id", "related_booking_id"),
        Index("ix_notifications_related_participant_id", "related_participant_id"),
        Index("ix_notifications_related_message_id", "related_message_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)

    title: Mapped[str] = mapped_column(String(150), nullable=False)

    body: Mapped[str] = mapped_column(Text, nullable=False)

    related_game_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="SET NULL"),
        nullable=True,
    )

    related_booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="SET NULL"),
        nullable=True,
    )

    related_participant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("game_participants.id", ondelete="SET NULL"),
        nullable=True,
    )

    related_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_messages.id", ondelete="SET NULL"),
        nullable=True,
    )

    is_read: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )

    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
