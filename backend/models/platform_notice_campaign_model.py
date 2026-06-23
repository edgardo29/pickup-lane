import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class PlatformNoticeCampaign(Base):
    __tablename__ = "platform_notice_campaigns"
    __table_args__ = (
        CheckConstraint(
            (
                "campaign_status IN ("
                "'draft', 'sending', 'completed', "
                "'completed_with_failures', 'failed', 'cancelled'"
                ")"
            ),
            name="ck_platform_notice_campaigns_status",
        ),
        CheckConstraint(
            "audience_type IN ('all_active_users', 'selected_users')",
            name="ck_platform_notice_campaigns_audience_type",
        ),
        CheckConstraint(
            "delivery_class IN ('mandatory', 'preference_controlled')",
            name="ck_platform_notice_campaigns_delivery_class",
        ),
        UniqueConstraint(
            "created_by_user_id",
            "creation_idempotency_key",
            name="uq_platform_notice_campaigns_creator_idempotency",
        ),
        Index("ix_platform_notice_campaigns_status", "campaign_status"),
        Index("ix_platform_notice_campaigns_audience_type", "audience_type"),
        Index("ix_platform_notice_campaigns_delivery_class", "delivery_class"),
        Index("ix_platform_notice_campaigns_created_by_user_id", "created_by_user_id"),
        Index("ix_platform_notice_campaigns_created_at", "created_at"),
        Index("ix_platform_notice_campaigns_first_sent_at", "first_sent_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    campaign_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'draft'")
    )
    audience_type: Mapped[str] = mapped_column(String(30), nullable=False)
    delivery_class: Mapped[str] = mapped_column(String(30), nullable=False)
    internal_name: Mapped[str] = mapped_column(String(160), nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    creation_idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    creation_request_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    first_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class PlatformNoticeCampaignTargetUser(Base):
    __tablename__ = "platform_notice_campaign_target_users"
    __table_args__ = (
        Index(
            "ix_platform_notice_campaign_target_users_user_id",
            "user_id",
        ),
    )

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform_notice_campaigns.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class PlatformNoticeCampaignAttempt(Base):
    __tablename__ = "platform_notice_campaign_attempts"
    __table_args__ = (
        CheckConstraint(
            "attempt_type IN ('initial_send', 'retry_failed')",
            name="ck_platform_notice_campaign_attempts_type",
        ),
        CheckConstraint(
            (
                "attempt_status IN ("
                "'in_progress', 'completed', 'completed_with_failures', 'failed'"
                ")"
            ),
            name="ck_platform_notice_campaign_attempts_status",
        ),
        CheckConstraint(
            (
                "targeted_count >= 0 AND delivered_count >= 0 "
                "AND skipped_count >= 0 AND failed_count >= 0"
            ),
            name="ck_platform_notice_campaign_attempts_counts_nonnegative",
        ),
        CheckConstraint(
            (
                "attempt_status = 'in_progress' OR "
                "targeted_count = delivered_count + skipped_count + failed_count"
            ),
            name="ck_platform_notice_campaign_attempts_counts_match",
        ),
        UniqueConstraint(
            "campaign_id",
            "idempotency_key",
            name="uq_platform_notice_campaign_attempts_idempotency",
        ),
        Index(
            "ix_platform_notice_campaign_attempts_campaign_id",
            "campaign_id",
        ),
        Index(
            "ix_platform_notice_campaign_attempts_created_at",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform_notice_campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_type: Mapped[str] = mapped_column(String(30), nullable=False)
    attempt_status: Mapped[str] = mapped_column(String(40), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    targeted_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    delivered_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    skipped_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    failed_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class PlatformNoticeCampaignDelivery(Base):
    __tablename__ = "platform_notice_campaign_deliveries"
    __table_args__ = (
        CheckConstraint(
            "delivery_status IN ('pending', 'delivered', 'skipped', 'failed')",
            name="ck_platform_notice_campaign_deliveries_status",
        ),
        CheckConstraint(
            "attempt_count >= 0",
            name="ck_platform_notice_campaign_deliveries_attempt_count",
        ),
        CheckConstraint(
            (
                "(delivery_status = 'delivered' "
                "AND delivered_at IS NOT NULL "
                "AND skip_reason IS NULL "
                "AND failure_code IS NULL) "
                "OR (delivery_status = 'skipped' "
                "AND notification_id IS NULL "
                "AND delivered_at IS NULL "
                "AND skip_reason IS NOT NULL "
                "AND failure_code IS NULL) "
                "OR (delivery_status = 'failed' "
                "AND notification_id IS NULL "
                "AND delivered_at IS NULL "
                "AND skip_reason IS NULL "
                "AND failure_code IS NOT NULL) "
                "OR (delivery_status = 'pending' "
                "AND notification_id IS NULL "
                "AND delivered_at IS NULL "
                "AND skip_reason IS NULL "
                "AND failure_code IS NULL)"
            ),
            name="ck_platform_notice_campaign_deliveries_state",
        ),
        UniqueConstraint(
            "campaign_id",
            "recipient_user_id_snapshot",
            name="uq_platform_notice_campaign_deliveries_recipient",
        ),
        Index(
            "ix_platform_notice_campaign_deliveries_campaign_id",
            "campaign_id",
        ),
        Index(
            "ix_platform_notice_campaign_deliveries_recipient_user_id",
            "recipient_user_id",
        ),
        Index(
            "ix_platform_notice_campaign_deliveries_status",
            "delivery_status",
        ),
        Index(
            "ix_platform_notice_campaign_deliveries_notification_id",
            "notification_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform_notice_campaigns.id", ondelete="CASCADE"),
        nullable=False,
    )
    recipient_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    recipient_user_id_snapshot: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    delivery_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'pending'")
    )
    skip_reason: Mapped[str | None] = mapped_column(String(60), nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    notification_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notifications.id", ondelete="SET NULL"),
        nullable=True,
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    last_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
