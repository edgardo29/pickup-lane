import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class SupportFlag(Base):
    __tablename__ = "support_flags"
    __table_args__ = (
        CheckConstraint(
            (
                "flag_type IN ("
                "'refund_follow_up_required', 'stripe_refund_failed', "
                "'missing_stripe_charge_id', 'credit_restore_failed', "
                "'credit_release_failed', 'venue_image_upload_failed', "
                "'venue_image_readiness_failed', 'account_delete_partial_failure', "
                "'official_cancel_partial_failure'"
                ")"
            ),
            name="ck_support_flags_flag_type",
        ),
        CheckConstraint(
            "flag_status IN ('open', 'resolved')",
            name="ck_support_flags_flag_status",
        ),
        CheckConstraint(
            "severity IN ('attention', 'urgent', 'critical')",
            name="ck_support_flags_severity",
        ),
        CheckConstraint(
            "source IN ('system', 'admin', 'stripe', 'venue_image', 'account', 'official_game')",
            name="ck_support_flags_source",
        ),
        CheckConstraint(
            (
                "resolution_outcome IS NULL OR resolution_outcome IN ("
                "'handled_externally', 'retried_successfully', "
                "'no_action_needed', 'duplicate', 'invalid_flag'"
                ")"
            ),
            name="ck_support_flags_resolution_outcome",
        ),
        CheckConstraint(
            (
                "target_user_id IS NOT NULL "
                "OR target_game_id IS NOT NULL "
                "OR target_booking_id IS NOT NULL "
                "OR target_payment_id IS NOT NULL "
                "OR target_refund_id IS NOT NULL "
                "OR target_game_credit_id IS NOT NULL "
                "OR target_venue_id IS NOT NULL "
                "OR target_venue_image_id IS NOT NULL "
                "OR target_notification_id IS NOT NULL"
            ),
            name="ck_support_flags_target_required",
        ),
        CheckConstraint(
            (
                "(flag_status = 'open' "
                "AND resolved_at IS NULL "
                "AND resolved_by_user_id IS NULL "
                "AND resolution_outcome IS NULL "
                "AND resolution_reason IS NULL) "
                "OR "
                "(flag_status = 'resolved' "
                "AND resolved_at IS NOT NULL "
                "AND resolved_by_user_id IS NOT NULL "
                "AND resolution_outcome IS NOT NULL "
                "AND resolution_reason IS NOT NULL)"
            ),
            name="ck_support_flags_resolution_state",
        ),
        Index("ix_support_flags_flag_type", "flag_type"),
        Index("ix_support_flags_flag_status", "flag_status"),
        Index("ix_support_flags_created_at", "created_at"),
        Index("ix_support_flags_resolved_at", "resolved_at"),
        Index("ix_support_flags_target_user_id", "target_user_id"),
        Index("ix_support_flags_target_game_id", "target_game_id"),
        Index("ix_support_flags_target_booking_id", "target_booking_id"),
        Index("ix_support_flags_target_payment_id", "target_payment_id"),
        Index("ix_support_flags_target_refund_id", "target_refund_id"),
        Index("ix_support_flags_target_game_credit_id", "target_game_credit_id"),
        Index("ix_support_flags_target_venue_id", "target_venue_id"),
        Index("ix_support_flags_target_venue_image_id", "target_venue_image_id"),
        Index("ix_support_flags_target_notification_id", "target_notification_id"),
        Index("ix_support_flags_source_admin_action_id", "source_admin_action_id"),
        Index("ix_support_flags_resolution_admin_action_id", "resolution_admin_action_id"),
        Index(
            "uq_support_flags_flag_type_idempotency_key",
            "flag_type",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    flag_type: Mapped[str] = mapped_column(String(80), nullable=False)
    flag_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default=text("'open'"),
    )
    severity: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default=text("'attention'"),
    )
    source: Mapped[str] = mapped_column(String(40), nullable=False)
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
    target_booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_payment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_refund_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("refunds.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_game_credit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("game_credits.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_venue_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("venues.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_venue_image_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("venue_images.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_notification_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notifications.id", ondelete="SET NULL"),
        nullable=True,
    )

    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(160), nullable=True)
    source_admin_action_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_actions.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolution_outcome: Mapped[str | None] = mapped_column(String(60), nullable=True)
    resolution_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution_admin_action_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_actions.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
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
