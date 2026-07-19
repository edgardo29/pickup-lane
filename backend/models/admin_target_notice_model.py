import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class AdminTargetNotice(Base):
    __tablename__ = "admin_target_notices"
    __table_args__ = (
        CheckConstraint(
            (
                "notice_type IN ("
                "'community_game_hidden', 'community_game_restored', "
                "'community_game_joining_paused', "
                "'community_game_joining_resumed', "
                "'community_game_payment_info_hidden', "
                "'community_game_payment_info_restored', "
                "'community_game_cancelled', 'need_sub_post_hidden', "
                "'need_sub_post_restored', 'need_sub_post_removed', "
                "'publish_fee_refunded', 'publish_credit_added'"
                ")"
            ),
            name="ck_admin_target_notices_notice_type",
        ),
        CheckConstraint(
            "notice_status IN ('active', 'dismissed')",
            name="ck_admin_target_notices_notice_status",
        ),
        CheckConstraint(
            (
                "target_game_id IS NOT NULL "
                "OR target_sub_post_id IS NOT NULL "
                "OR target_sub_post_request_id IS NOT NULL "
                "OR target_user_id IS NOT NULL"
            ),
            name="ck_admin_target_notices_target_required",
        ),
        Index("ix_admin_target_notices_recipient_user_id", "recipient_user_id"),
        Index("ix_admin_target_notices_target_user_id", "target_user_id"),
        Index("ix_admin_target_notices_target_game_id", "target_game_id"),
        Index("ix_admin_target_notices_target_sub_post_id", "target_sub_post_id"),
        Index(
            "ix_admin_target_notices_target_sub_post_request_id",
            "target_sub_post_request_id",
        ),
        Index("ix_admin_target_notices_admin_action_id", "admin_action_id"),
        Index("ix_admin_target_notices_notice_type", "notice_type"),
        Index("ix_admin_target_notices_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    recipient_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_game_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="CASCADE"),
        nullable=True,
    )
    target_sub_post_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sub_posts.id", ondelete="CASCADE"),
        nullable=True,
    )
    target_sub_post_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sub_post_requests.id", ondelete="CASCADE"),
        nullable=True,
    )
    admin_action_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_actions.id", ondelete="SET NULL"),
        nullable=True,
    )
    notice_type: Mapped[str] = mapped_column(String(60), nullable=False)
    notice_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'active'")
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    user_safe_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notice_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
