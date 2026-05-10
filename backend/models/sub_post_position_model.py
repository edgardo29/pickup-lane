import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class SubPostPosition(Base):
    __tablename__ = "sub_post_positions"
    __table_args__ = (
        CheckConstraint(
            "position_label IN ('field_player', 'goalkeeper')",
            name="ck_sub_post_positions_position_label",
        ),
        CheckConstraint(
            "player_group IN ('open', 'men', 'women')",
            name="ck_sub_post_positions_player_group",
        ),
        CheckConstraint(
            "spots_needed > 0",
            name="ck_sub_post_positions_spots_needed_positive",
        ),
        CheckConstraint(
            "sort_order >= 0",
            name="ck_sub_post_positions_sort_order_non_negative",
        ),
        UniqueConstraint(
            "sub_post_id",
            "position_label",
            "player_group",
            name="uq_sub_post_positions_post_position_group",
        ),
        UniqueConstraint(
            "id",
            "sub_post_id",
            name="uq_sub_post_positions_id_sub_post_id",
        ),
        Index("ix_sub_post_positions_sub_post_id", "sub_post_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    sub_post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sub_posts.id", ondelete="CASCADE"),
        nullable=False,
    )
    position_label: Mapped[str] = mapped_column(String(50), nullable=False)
    player_group: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'open'")
    )
    spots_needed: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1")
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
