import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class SubPostRequest(Base):
    __tablename__ = "sub_post_requests"
    __table_args__ = (
        CheckConstraint(
            (
                "request_status IN ('pending', 'confirmed', 'declined', "
                "'sub_waitlist', 'canceled_by_player', 'canceled_by_owner', "
                "'no_show_reported', 'expired')"
            ),
            name="ck_sub_post_requests_request_status",
        ),
        CheckConstraint(
            "request_status != 'confirmed' OR confirmed_at IS NOT NULL",
            name="ck_sub_post_requests_confirmed_requires_confirmed_at",
        ),
        CheckConstraint(
            "request_status != 'declined' OR declined_at IS NOT NULL",
            name="ck_sub_post_requests_declined_requires_declined_at",
        ),
        CheckConstraint(
            "request_status != 'sub_waitlist' OR sub_waitlisted_at IS NOT NULL",
            name="ck_sub_post_requests_waitlist_requires_waitlisted_at",
        ),
        CheckConstraint(
            (
                "request_status NOT IN ('canceled_by_player', 'canceled_by_owner') "
                "OR canceled_at IS NOT NULL"
            ),
            name="ck_sub_post_requests_canceled_requires_canceled_at",
        ),
        CheckConstraint(
            "request_status != 'expired' OR expired_at IS NOT NULL",
            name="ck_sub_post_requests_expired_requires_expired_at",
        ),
        CheckConstraint(
            "request_status != 'no_show_reported' OR no_show_reported_at IS NOT NULL",
            name="ck_sub_post_requests_no_show_requires_reported_at",
        ),
        ForeignKeyConstraint(
            ["sub_post_position_id", "sub_post_id"],
            ["sub_post_positions.id", "sub_post_positions.sub_post_id"],
            ondelete="RESTRICT",
        ),
        Index(
            "uq_sub_post_requests_active_post_requester",
            "sub_post_id",
            "requester_user_id",
            unique=True,
            postgresql_where=text(
                "request_status IN ('pending', 'confirmed', 'sub_waitlist')"
            ),
        ),
        Index("ix_sub_post_requests_sub_post_id", "sub_post_id"),
        Index("ix_sub_post_requests_sub_post_position_id", "sub_post_position_id"),
        Index("ix_sub_post_requests_requester_user_id", "requester_user_id"),
        Index("ix_sub_post_requests_post_status", "sub_post_id", "request_status"),
        Index(
            "ix_sub_post_requests_position_status",
            "sub_post_position_id",
            "request_status",
        ),
        Index(
            "ix_sub_post_requests_requester_status",
            "requester_user_id",
            "request_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    sub_post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sub_posts.id", ondelete="CASCADE"),
        nullable=False,
    )
    sub_post_position_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sub_post_positions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    requester_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    request_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'pending'")
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    declined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sub_waitlisted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    no_show_reported_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
