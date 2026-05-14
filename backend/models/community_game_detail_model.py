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


# Community game details store a per-game snapshot of host payment/rules
# details so old games do not change when a host edits their saved defaults.
class CommunityGameDetail(Base):
    __tablename__ = "community_game_details"
    __table_args__ = (
        CheckConstraint(
            "jsonb_typeof(payment_methods_snapshot) = 'array'",
            name="ck_community_game_details_payment_methods_array",
        ),
        CheckConstraint(
            (
                "payment_due_timing_snapshot IS NULL OR "
                "payment_due_timing_snapshot IN ("
                "'before_game', 'at_arrival', 'after_confirmation', 'custom'"
                ")"
            ),
            name="ck_community_game_details_payment_due_timing",
        ),
        UniqueConstraint("game_id", name="uq_community_game_details_game_id"),
        Index("ix_community_game_details_game_id", "game_id"),
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
    payment_due_timing_snapshot: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )
    price_note_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    refund_policy_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancellation_policy_snapshot: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    no_show_policy_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    arrival_expectations_snapshot: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    equipment_notes_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    behavior_rules_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    player_message_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
