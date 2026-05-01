import uuid
from datetime import datetime

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


# This table stores the actual roster slots for a game, including registered
# players, guests, hosts, and admin-added participants as the source of truth
# for participation and attendance outcomes.
class GameParticipant(Base):
    __tablename__ = "game_participants"
    __table_args__ = (
        # Keep participant identity, lifecycle, attendance, and money fields
        # within the supported values and required combinations.
        CheckConstraint(
            "participant_type IN ('registered_user', 'guest', 'host', 'admin_added')",
            name="ck_game_participants_participant_type",
        ),
        CheckConstraint(
            (
                "participant_status IN ("
                "'pending_payment', 'confirmed', 'waitlisted', 'cancelled', "
                "'late_cancelled', 'removed', 'refunded'"
                ")"
            ),
            name="ck_game_participants_participant_status",
        ),
        CheckConstraint(
            (
                "attendance_status IN ("
                "'unknown', 'attended', 'no_show', 'excused_absence', "
                "'not_applicable'"
                ")"
            ),
            name="ck_game_participants_attendance_status",
        ),
        CheckConstraint(
            (
                "cancellation_type IN ("
                "'none', 'on_time', 'late', 'host_cancelled', "
                "'admin_cancelled', 'payment_failed'"
                ")"
            ),
            name="ck_game_participants_cancellation_type",
        ),
        CheckConstraint(
            "currency = 'USD'",
            name="ck_game_participants_currency",
        ),
        CheckConstraint(
            "price_cents >= 0",
            name="ck_game_participants_price_cents",
        ),
        CheckConstraint(
            "(roster_order IS NULL OR roster_order > 0)",
            name="ck_game_participants_roster_order",
        ),
        CheckConstraint(
            "(participant_type <> 'guest' OR guest_name IS NOT NULL)",
            name="ck_game_participants_guest_requires_guest_name",
        ),
        CheckConstraint(
            (
                "(participant_type NOT IN ('registered_user', 'host', 'admin_added') "
                "OR user_id IS NOT NULL)"
            ),
            name="ck_game_participants_non_guest_requires_user",
        ),
        CheckConstraint(
            "(participant_status <> 'confirmed' OR confirmed_at IS NOT NULL)",
            name="ck_game_participants_confirmed_requires_confirmed_at",
        ),
        CheckConstraint(
            (
                "(participant_status NOT IN ('cancelled', 'late_cancelled', "
                "'removed', 'refunded') OR cancelled_at IS NOT NULL)"
            ),
            name="ck_game_participants_cancelled_requires_cancelled_at",
        ),
        CheckConstraint(
            (
                "(attendance_status NOT IN ('attended', 'no_show', "
                "'excused_absence') OR attendance_decided_at IS NOT NULL)"
            ),
            name="ck_game_participants_attendance_requires_decided_at",
        ),
        # These indexes support roster lookups, booking joins, and operational
        # views without trying to encode capacity rules at the database level.
        Index("ix_game_participants_game_id", "game_id"),
        Index("ix_game_participants_booking_id", "booking_id"),
        Index("ix_game_participants_user_id", "user_id"),
        Index("ix_game_participants_participant_status", "participant_status"),
        Index("ix_game_participants_attendance_status", "attendance_status"),
        Index(
            "ix_game_participants_game_id_participant_status",
            "game_id",
            "participant_status",
        ),
        Index(
            "ix_game_participants_booking_id_participant_status",
            "booking_id",
            "participant_status",
        ),
        Index(
            "ix_game_participants_user_id_participant_status",
            "user_id",
            "participant_status",
        ),
        Index(
            "ux_game_participants_active_registered_user_per_game",
            "game_id",
            "user_id",
            unique=True,
            postgresql_where=text(
                "user_id IS NOT NULL AND participant_status IN "
                "('pending_payment', 'confirmed', 'waitlisted')"
            ),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="RESTRICT"),
        nullable=False,
    )
    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="RESTRICT"),
        nullable=True,
    )
    participant_type: Mapped[str] = mapped_column(String(20), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    guest_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    guest_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    guest_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    display_name_snapshot: Mapped[str] = mapped_column(String(150), nullable=False)
    participant_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'pending_payment'")
    )
    attendance_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'unknown'")
    )
    cancellation_type: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'none'")
    )
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(
        CHAR(3), nullable=False, server_default=text("'USD'")
    )
    roster_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    checked_in_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    marked_attendance_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    attendance_decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    attendance_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
