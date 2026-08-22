import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database_metadata import Base


class PlatformNotice(Base):
    __tablename__ = "platform_notices"
    __table_args__ = (
        CheckConstraint(
            "audience_type IN ('all_eligible_users', 'selected_users')",
            name="ck_platform_notices_audience_type",
        ),
        CheckConstraint(
            (
                "(audience_type = 'all_eligible_users' AND global_sequence IS NOT NULL) "
                "OR (audience_type = 'selected_users' AND global_sequence IS NULL)"
            ),
            name="ck_platform_notices_global_sequence_scope",
        ),
        CheckConstraint(
            "char_length(btrim(title)) > 0",
            name="ck_platform_notices_title_not_empty",
        ),
        CheckConstraint(
            "char_length(btrim(message)) > 0",
            name="ck_platform_notices_message_not_empty",
        ),
        CheckConstraint(
            (
                "(cancelled_at IS NULL AND cancelled_by_admin_id IS NULL "
                "AND cancellation_reason IS NULL) "
                "OR (cancelled_at IS NOT NULL AND cancelled_by_admin_id IS NOT NULL "
                "AND cancellation_reason IS NOT NULL)"
            ),
            name="ck_platform_notices_cancellation_integrity",
        ),
        Index(
            "uq_platform_notices_admin_idempotency_key",
            "created_by_admin_id",
            "idempotency_key_hash",
            unique=True,
        ),
        Index(
            "uq_platform_notices_global_sequence",
            "global_sequence",
            unique=True,
            postgresql_where=text("global_sequence IS NOT NULL"),
        ),
        Index(
            "ix_platform_notices_audience_cancelled_published_id",
            "audience_type",
            "cancelled_at",
            "published_at",
            "id",
        ),
        Index("ix_platform_notices_created_by_admin_id", "created_by_admin_id"),
        Index(
            "ix_platform_notices_history_order",
            text("published_at DESC"),
            text("id DESC"),
        ),
        Index("ix_platform_notices_cancelled_at", "cancelled_at"),
        Index(
            "ix_platform_notices_history_search_trgm",
            text("(coalesce(title, '') || ' ' || coalesce(message, '')) gin_trgm_ops"),
            postgresql_using="gin",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    audience_type: Mapped[str] = mapped_column(String(30), nullable=False)
    global_sequence: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    idempotency_key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancelled_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
