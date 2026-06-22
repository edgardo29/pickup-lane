import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


# Community game details store the per-game host payment snapshot that players
# see after joining a community game.
class CommunityGameDetail(Base):
    __tablename__ = "community_game_details"
    __table_args__ = (
        CheckConstraint(
            "jsonb_typeof(payment_methods_snapshot) = 'array'",
            name="ck_community_game_details_payment_methods_array",
        ),
        CheckConstraint(
            "payment_text_moderation_status IN ('visible', 'hidden')",
            name="ck_community_game_details_payment_text_moderation_status",
        ),
        CheckConstraint(
            (
                "payment_text_moderation_status != 'hidden' "
                "OR (payment_text_hidden_at IS NOT NULL "
                "AND NULLIF(BTRIM(payment_text_hidden_reason), '') IS NOT NULL)"
            ),
            name="ck_community_game_details_hidden_requires_metadata",
        ),
        UniqueConstraint("game_id", name="uq_community_game_details_game_id"),
        Index("ix_community_game_details_game_id", "game_id"),
        Index(
            "ix_community_game_details_payment_text_moderation_status",
            "payment_text_moderation_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="RESTRICT"),
        nullable=False,
    )
    payment_methods_snapshot: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    payment_instructions_snapshot: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    payment_text_moderation_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default=text("'visible'"),
    )
    payment_text_hidden_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    payment_text_hidden_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    payment_text_hidden_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
