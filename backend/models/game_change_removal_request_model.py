import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database_metadata import Base


class GameChangeRemovalRequest(Base):
    """A player's request to leave an official game whose details changed.

    Submitting a request changes no booking, roster, refund, or credit. Staff
    processing completes the removal and the chosen refund or game credit.
    """

    __tablename__ = "game_change_removal_requests"
    __table_args__ = (
        CheckConstraint(
            "relief_choice IN ('original_payment_method', 'game_credit')",
            name="ck_game_change_removal_requests_relief_choice",
        ),
        CheckConstraint(
            "request_status IN ('pending', 'processing', 'completed', 'rejected', 'failed')",
            name="ck_game_change_removal_requests_status",
        ),
        Index(
            "ix_game_change_removal_requests_booking_submitted",
            "booking_id",
            "submitted_at",
        ),
        Index(
            "uq_game_change_removal_requests_active_booking",
            "booking_id",
            unique=True,
            postgresql_where=text(
                "request_status IN ('pending', 'processing', 'failed')"
            ),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=False
    )
    requester_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    processed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    relief_choice: Mapped[str] = mapped_column(String(30), nullable=False)
    request_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'pending'")
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
