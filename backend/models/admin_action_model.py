import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


# Admin actions store audit rows for important admin/support actions across
# users, games, payments, venues, chat messages, and host deposits.
class AdminAction(Base):
    __tablename__ = "admin_actions"
    __table_args__ = (
        CheckConstraint(
            (
                "action_type IN ("
                "'cancel_game', 'refund_booking', 'mark_no_show', "
                "'reverse_no_show', 'suspend_user', 'unsuspend_user', "
                "'restrict_hosting', 'restore_hosting', 'approve_venue', "
                "'reject_venue', 'remove_chat_message', 'hide_chat_message', "
                "'forfeit_host_deposit', 'release_host_deposit', "
                "'waive_host_deposit', 'update_game', 'update_booking', "
                "'update_participant'"
                ")"
            ),
            name="ck_admin_actions_action_type",
        ),
        CheckConstraint(
            (
                "target_user_id IS NOT NULL "
                "OR target_game_id IS NOT NULL "
                "OR target_booking_id IS NOT NULL "
                "OR target_participant_id IS NOT NULL "
                "OR target_payment_id IS NOT NULL "
                "OR target_venue_id IS NOT NULL "
                "OR target_message_id IS NOT NULL "
                "OR target_host_deposit_id IS NOT NULL"
            ),
            name="ck_admin_actions_target_required",
        ),
        Index("ix_admin_actions_admin_user_id", "admin_user_id"),
        Index("ix_admin_actions_action_type", "action_type"),
        Index("ix_admin_actions_created_at", "created_at"),
        Index("ix_admin_actions_target_user_id", "target_user_id"),
        Index("ix_admin_actions_target_game_id", "target_game_id"),
        Index("ix_admin_actions_target_booking_id", "target_booking_id"),
        Index("ix_admin_actions_target_participant_id", "target_participant_id"),
        Index("ix_admin_actions_target_payment_id", "target_payment_id"),
        Index("ix_admin_actions_target_venue_id", "target_venue_id"),
        Index("ix_admin_actions_target_message_id", "target_message_id"),
        Index("ix_admin_actions_target_host_deposit_id", "target_host_deposit_id"),
        Index(
            "ix_admin_actions_admin_user_id_created_at",
            "admin_user_id",
            "created_at",
        ),
        Index(
            "ix_admin_actions_action_type_created_at",
            "action_type",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)

    admin_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    action_type: Mapped[str] = mapped_column(String(60), nullable=False)

    target_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    target_game_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="SET NULL"),
        nullable=True,
    )

    target_booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="SET NULL"),
        nullable=True,
    )

    target_participant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("game_participants.id", ondelete="SET NULL"),
        nullable=True,
    )

    target_payment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
    )

    target_venue_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("venues.id", ondelete="SET NULL"),
        nullable=True,
    )

    target_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_messages.id", ondelete="SET NULL"),
        nullable=True,
    )

    target_host_deposit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("host_deposits.id", ondelete="SET NULL"),
        nullable=True,
    )

    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    metadata_: Mapped[dict | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )