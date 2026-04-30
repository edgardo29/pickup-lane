import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
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


# This table stores the core published game record, including venue snapshot
# data and lifecycle state, without pulling in bookings or participant details.
class Game(Base):
    __tablename__ = "games"
    __table_args__ = (
        # Keep game state, policy, and scheduling fields within the supported
        # values and ranges so invalid game state cannot be stored accidentally.
        CheckConstraint(
            "game_type IN ('official', 'community')",
            name="ck_games_game_type",
        ),
        CheckConstraint(
            "publish_status IN ('draft', 'published', 'archived')",
            name="ck_games_publish_status",
        ),
        CheckConstraint(
            "game_status IN ('scheduled', 'full', 'cancelled', 'completed', 'abandoned')",
            name="ck_games_game_status",
        ),
        CheckConstraint(
            "environment_type IN ('indoor', 'outdoor')",
            name="ck_games_environment_type",
        ),
        CheckConstraint(
            "policy_mode IN ('official_standard', 'custom_hosted')",
            name="ck_games_policy_mode",
        ),
        CheckConstraint(
            "currency = 'USD'",
            name="ck_games_currency",
        ),
        CheckConstraint(
            "ends_at > starts_at",
            name="ck_games_ends_after_starts",
        ),
        CheckConstraint(
            "total_spots > 0",
            name="ck_games_total_spots",
        ),
        CheckConstraint(
            "price_per_player_cents >= 0",
            name="ck_games_price_per_player_cents",
        ),
        CheckConstraint(
            "max_guests_per_booking >= 0",
            name="ck_games_max_guests_per_booking",
        ),
        CheckConstraint(
            "(minimum_age IS NULL OR minimum_age >= 13)",
            name="ck_games_minimum_age",
        ),
        CheckConstraint(
            "(game_type <> 'community' OR host_user_id IS NOT NULL)",
            name="ck_games_community_requires_host_user",
        ),
        CheckConstraint(
            "(game_type <> 'official' OR policy_mode = 'official_standard')",
            name="ck_games_official_policy_mode",
        ),
        CheckConstraint(
            "(game_type <> 'community' OR policy_mode = 'custom_hosted')",
            name="ck_games_community_policy_mode",
        ),
        CheckConstraint(
            "(publish_status <> 'published' OR published_at IS NOT NULL)",
            name="ck_games_published_requires_published_at",
        ),
        CheckConstraint(
            "(game_status <> 'cancelled' OR cancelled_at IS NOT NULL)",
            name="ck_games_cancelled_requires_cancelled_at",
        ),
        CheckConstraint(
            "(game_status <> 'completed' OR completed_at IS NOT NULL)",
            name="ck_games_completed_requires_completed_at",
        ),
        # These indexes support common browse, scheduling, and owner lookup
        # paths without modeling bookings or participation yet.
        Index("ix_games_venue_id", "venue_id"),
        Index("ix_games_host_user_id", "host_user_id"),
        Index("ix_games_created_by_user_id", "created_by_user_id"),
        Index("ix_games_starts_at", "starts_at"),
        Index(
            "ix_games_browse_city_publish_status_game_status_starts_at",
            "city_snapshot",
            "publish_status",
            "game_status",
            "starts_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    game_type: Mapped[str] = mapped_column(String(20), nullable=False)
    publish_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'draft'")
    )
    game_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'scheduled'")
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    venue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("venues.id", ondelete="RESTRICT"),
        nullable=False,
    )
    venue_name_snapshot: Mapped[str] = mapped_column(String(150), nullable=False)
    address_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    city_snapshot: Mapped[str] = mapped_column(String(100), nullable=False)
    state_snapshot: Mapped[str] = mapped_column(String(100), nullable=False)
    neighborhood_snapshot: Mapped[str | None] = mapped_column(
        String(120), nullable=True
    )
    host_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    timezone: Mapped[str] = mapped_column(
        String(60), nullable=False, server_default=text("'America/Chicago'")
    )
    sport_type: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default=text("'soccer'")
    )
    format_label: Mapped[str] = mapped_column(String(20), nullable=False)
    environment_type: Mapped[str] = mapped_column(String(20), nullable=False)
    total_spots: Mapped[int] = mapped_column(Integer, nullable=False)
    price_per_player_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(
        CHAR(3), nullable=False, server_default=text("'USD'")
    )
    minimum_age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    allow_guests: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    max_guests_per_booking: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("2")
    )
    waitlist_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    is_chat_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    policy_mode: Mapped[str] = mapped_column(String(30), nullable=False)
    custom_rules_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    custom_cancellation_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    game_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    arrival_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    parking_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
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
