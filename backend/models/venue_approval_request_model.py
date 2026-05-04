import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import CHAR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


# Venue approval requests store user-submitted venue locations that need admin
# review before being connected to an approved venue record.
class VenueApprovalRequest(Base):
    __tablename__ = "venue_approval_requests"
    __table_args__ = (
        CheckConstraint(
            "request_status IN ('pending_review', 'approved', 'rejected', 'inactive')",
            name="ck_venue_approval_requests_request_status",
        ),
        CheckConstraint(
            "char_length(requested_country_code) = 2",
            name="ck_venue_approval_requests_requested_country_code",
        ),
        CheckConstraint(
            (
                "request_status NOT IN ('approved', 'rejected', 'inactive') "
                "OR reviewed_at IS NOT NULL"
            ),
            name="ck_venue_approval_requests_reviewed_status_requires_reviewed_at",
        ),
        CheckConstraint(
            "(request_status <> 'approved' OR venue_id IS NOT NULL)",
            name="ck_venue_approval_requests_approved_requires_venue_id",
        ),
        Index(
            "ix_venue_approval_requests_submitted_by_user_id",
            "submitted_by_user_id",
        ),
        Index("ix_venue_approval_requests_venue_id", "venue_id"),
        Index(
            "ix_venue_approval_requests_reviewed_by_user_id",
            "reviewed_by_user_id",
        ),
        Index("ix_venue_approval_requests_request_status", "request_status"),
        Index("ix_venue_approval_requests_created_at", "created_at"),
        Index(
            "ix_venue_approval_requests_request_status_created_at",
            "request_status",
            "created_at",
        ),
        Index(
            "ix_venue_approval_requests_submitted_by_user_id_created_at",
            "submitted_by_user_id",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)

    submitted_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    venue_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("venues.id", ondelete="SET NULL"),
        nullable=True,
    )

    requested_name: Mapped[str] = mapped_column(String(150), nullable=False)

    requested_address_line_1: Mapped[str] = mapped_column(String(200), nullable=False)

    requested_city: Mapped[str] = mapped_column(String(100), nullable=False)

    requested_state: Mapped[str] = mapped_column(String(100), nullable=False)

    requested_postal_code: Mapped[str] = mapped_column(String(20), nullable=False)

    requested_country_code: Mapped[str] = mapped_column(
        CHAR(2), nullable=False, server_default=text("'US'")
    )

    request_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'pending_review'")
    )

    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )