import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


# Booking policy acceptances track which policy document versions applied to a
# specific booking at the time the user confirmed and paid.
class BookingPolicyAcceptance(Base):
    __tablename__ = "booking_policy_acceptances"
    __table_args__ = (
        UniqueConstraint(
            "booking_id",
            "policy_document_id",
            name="uq_booking_policy_acceptances_booking_id_policy_document_id",
        ),
        Index("ix_booking_policy_acceptances_booking_id", "booking_id"),
        Index("ix_booking_policy_acceptances_policy_document_id", "policy_document_id"),
        Index("ix_booking_policy_acceptances_accepted_at", "accepted_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)

    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
    )

    policy_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("policy_documents.id", ondelete="RESTRICT"),
        nullable=False,
    )

    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )