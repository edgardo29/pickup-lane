import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
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


# Game images store Browse card images and Game Details gallery images.
class GameImage(Base):
    __tablename__ = "game_images"
    __table_args__ = (
        CheckConstraint(
            "image_role IN ('card', 'gallery')",
            name="ck_game_images_image_role",
        ),
        CheckConstraint(
            "image_status IN ('active', 'hidden', 'removed')",
            name="ck_game_images_image_status",
        ),
        CheckConstraint(
            "char_length(btrim(image_url)) > 0",
            name="ck_game_images_image_url_not_empty",
        ),
        CheckConstraint(
            "sort_order >= 0",
            name="ck_game_images_sort_order_non_negative",
        ),
        Index("ix_game_images_game_id", "game_id"),
        Index("ix_game_images_uploaded_by_user_id", "uploaded_by_user_id"),
        Index("ix_game_images_image_status", "image_status"),
        Index("ix_game_images_sort_order", "sort_order"),
        Index(
            "ix_game_images_game_id_image_status_sort_order",
            "game_id",
            "image_status",
            "sort_order",
        ),
        Index(
            "uq_game_images_one_active_primary_per_game",
            "game_id",
            unique=True,
            postgresql_where=text(
                "is_primary = true AND image_status = 'active' AND deleted_at IS NULL"
            ),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)

    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=False,
    )

    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    image_url: Mapped[str] = mapped_column(Text, nullable=False)

    image_role: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'gallery'")
    )

    image_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'active'")
    )

    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
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

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )