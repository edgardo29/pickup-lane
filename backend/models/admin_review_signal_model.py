import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class AdminReviewSignal(Base):
    __tablename__ = "admin_review_signals"
    __table_args__ = (
        CheckConstraint(
            "signal_category IN ('chat_moderation')",
            name="ck_admin_review_signals_signal_category",
        ),
        CheckConstraint(
            "source IN ('chat_moderation')",
            name="ck_admin_review_signals_source",
        ),
        CheckConstraint(
            "signal_status IN ('open', 'attached', 'dismissed')",
            name="ck_admin_review_signals_signal_status",
        ),
        CheckConstraint(
            "priority IN ('attention', 'urgent', 'critical')",
            name="ck_admin_review_signals_priority",
        ),
        Index("ix_admin_review_signals_review_case_id", "review_case_id"),
        Index("ix_admin_review_signals_signal_category", "signal_category"),
        Index("ix_admin_review_signals_signal_status", "signal_status"),
        Index("ix_admin_review_signals_priority", "priority"),
        Index("ix_admin_review_signals_created_at", "created_at"),
        Index("ix_admin_review_signals_target_user_id", "target_user_id"),
        Index("ix_admin_review_signals_target_game_id", "target_game_id"),
        Index("ix_admin_review_signals_target_sub_post_id", "target_sub_post_id"),
        Index(
            "ix_admin_review_signals_target_sub_post_request_id",
            "target_sub_post_request_id",
        ),
        Index("ix_admin_review_signals_target_payment_id", "target_payment_id"),
        Index(
            "ix_admin_review_signals_target_financial_outcome_id",
            "target_financial_outcome_id",
        ),
        Index(
            "uq_admin_review_signals_source_idempotency_key",
            "source",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    review_case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_review_cases.id", ondelete="SET NULL"),
        nullable=True,
    )
    signal_category: Mapped[str] = mapped_column(String(60), nullable=False)
    source: Mapped[str] = mapped_column(String(60), nullable=False)
    signal_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default=text("'open'"),
    )
    priority: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default=text("'attention'"),
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)

    target_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_game_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_sub_post_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sub_posts.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_sub_post_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sub_post_requests.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_payment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_financial_outcome_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_financial_outcomes.id", ondelete="SET NULL"),
        nullable=True,
    )

    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
