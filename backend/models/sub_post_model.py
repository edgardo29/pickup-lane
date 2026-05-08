import uuid
from datetime import datetime

from sqlalchemy import CHAR, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class SubPost(Base):
    __tablename__ = "sub_posts"
    __table_args__ = (
        CheckConstraint(
            "post_status IN ('draft', 'active', 'filled', 'expired', 'canceled', 'removed')",
            name="ck_sub_posts_post_status",
        ),
        CheckConstraint("sport_type IN ('soccer')", name="ck_sub_posts_sport_type"),
        CheckConstraint(
            (
                "skill_level IN ('any', 'beginner', 'recreational', "
                "'intermediate', 'advanced', 'competitive')"
            ),
            name="ck_sub_posts_skill_level",
        ),
        CheckConstraint(
            "game_player_group IN ('open', 'men', 'women', 'coed')",
            name="ck_sub_posts_game_player_group",
        ),
        CheckConstraint("subs_needed > 0", name="ck_sub_posts_subs_needed_positive"),
        CheckConstraint(
            "price_due_at_venue_cents >= 0",
            name="ck_sub_posts_price_due_non_negative",
        ),
        CheckConstraint("currency = 'USD'", name="ck_sub_posts_currency"),
        CheckConstraint("starts_at < ends_at", name="ck_sub_posts_starts_before_ends"),
        CheckConstraint(
            "expires_at <= starts_at",
            name="ck_sub_posts_expires_not_after_starts",
        ),
        CheckConstraint(
            "post_status != 'filled' OR filled_at IS NOT NULL",
            name="ck_sub_posts_filled_requires_filled_at",
        ),
        CheckConstraint(
            "post_status != 'canceled' OR canceled_at IS NOT NULL",
            name="ck_sub_posts_canceled_requires_canceled_at",
        ),
        CheckConstraint(
            "post_status != 'removed' OR removed_at IS NOT NULL",
            name="ck_sub_posts_removed_requires_removed_at",
        ),
        Index("ix_sub_posts_owner_user_id", "owner_user_id"),
        Index("ix_sub_posts_post_status", "post_status"),
        Index("ix_sub_posts_starts_at", "starts_at"),
        Index("ix_sub_posts_expires_at", "expires_at"),
        Index("ix_sub_posts_city_state_starts_at", "city", "state", "starts_at"),
        Index("ix_sub_posts_post_status_starts_at", "post_status", "starts_at"),
        Index(
            "ix_sub_posts_browse_active_filled_starts_at",
            "starts_at",
            postgresql_where=text("post_status IN ('active', 'filled')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    post_status: Mapped[str] = mapped_column(String(30), nullable=False)
    sport_type: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default=text("'soccer'")
    )
    format_label: Mapped[str] = mapped_column(String(20), nullable=False)
    skill_level: Mapped[str] = mapped_column(String(30), nullable=False)
    game_player_group: Mapped[str] = mapped_column(String(30), nullable=False)
    team_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    timezone: Mapped[str] = mapped_column(
        String(60), nullable=False, server_default=text("'America/Chicago'")
    )
    location_name: Mapped[str] = mapped_column(String(150), nullable=False)
    address_line_1: Mapped[str] = mapped_column(String(200), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    country_code: Mapped[str] = mapped_column(
        CHAR(2), nullable=False, server_default=text("'US'")
    )
    neighborhood: Mapped[str | None] = mapped_column(String(120), nullable=True)
    subs_needed: Mapped[int] = mapped_column(Integer, nullable=False)
    price_due_at_venue_cents: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    currency: Mapped[str] = mapped_column(
        CHAR(3), nullable=False, server_default=text("'USD'")
    )
    payment_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    filled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    removed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    remove_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
