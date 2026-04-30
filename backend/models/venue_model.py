import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CHAR,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


# This table stores venue records that can be reviewed, approved, and reused
# across the app without bundling in court details or extra venue metadata yet.
class Venue(Base):
    __tablename__ = "venues"
    __table_args__ = (
        # Keep status and coordinate values within the supported ranges so
        # invalid venue state cannot be stored accidentally.
        CheckConstraint(
            "venue_status IN ('pending_review', 'approved', 'rejected', 'inactive')",
            name="ck_venues_venue_status",
        ),
        CheckConstraint(
            "char_length(country_code) = 2",
            name="ck_venues_country_code",
        ),
        CheckConstraint(
            "(latitude IS NULL OR latitude BETWEEN -90 AND 90)",
            name="ck_venues_latitude",
        ),
        CheckConstraint(
            "(longitude IS NULL OR longitude BETWEEN -180 AND 180)",
            name="ck_venues_longitude",
        ),
        # These indexes support common venue browsing, review, and lookup paths.
        Index("ix_venues_city_state", "city", "state"),
        Index("ix_venues_venue_status", "venue_status"),
        Index("ix_venues_is_active", "is_active"),
        Index("ix_venues_external_place_id", "external_place_id"),
        Index("ix_venues_created_by_user_id", "created_by_user_id"),
        Index("ix_venues_approved_by_user_id", "approved_by_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    address_line_1: Mapped[str] = mapped_column(String(200), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    country_code: Mapped[str] = mapped_column(
        CHAR(2), nullable=False, server_default=text("'US'")
    )
    neighborhood: Mapped[str | None] = mapped_column(String(120), nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    external_place_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    venue_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'pending_review'")
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
