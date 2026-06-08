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


# Notifications store inbox/activity feed records for one user and may point
# back to the domain records that caused them.
class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(
            (
                "notification_type IN ("
                "'booking_confirmed', 'booking_cancelled', 'booking_refunded', "
                "'payment_failed', 'game_cancelled', 'game_updated', "
                "'game_reminder', 'waitlist_joined', 'waitlist_promoted', "
                "'waitlist_expired', 'host_update', 'chat_message', "
                "'deposit_paid', 'deposit_released', 'deposit_forfeited', "
                "'admin_notice', 'support_reply', 'account_security', "
                "'policy_update', 'game_player_added_by_admin', "
                "'game_player_removed_by_admin', 'game_host_assigned', "
                "'game_host_removed', 'game_roster_update', "
                "'sub_request_received', 'sub_request_confirmed', "
                "'sub_request_declined', 'sub_waitlist_promoted_to_pending', "
                "'sub_request_canceled_by_player', "
                "'sub_request_canceled_by_owner', 'sub_post_canceled', "
                "'sub_post_removed', 'sub_post_updated'"
                ")"
            ),
            name="ck_notifications_notification_type",
        ),
        CheckConstraint(
            "notification_category IN ('app', 'game_activity')",
            name="ck_notifications_notification_category",
        ),
        CheckConstraint(
            (
                "notification_domain IN ("
                "'app', 'account', 'admin', 'support', 'game', 'need_a_sub'"
                ")"
            ),
            name="ck_notifications_notification_domain",
        ),
        CheckConstraint(
            (
                "((notification_category = 'app' "
                "AND notification_domain IN ('app', 'account', 'admin', 'support')) "
                "OR (notification_category = 'game_activity' "
                "AND notification_domain IN ('game', 'need_a_sub')))"
            ),
            name="ck_notifications_category_domain_match",
        ),
        CheckConstraint(
            (
                "source_type IN ("
                "'need_a_sub', 'official_game', 'community_game', 'game', "
                "'pickup_lane', 'policy', 'support', 'account', 'payment'"
                ")"
            ),
            name="ck_notifications_source_type",
        ),
        CheckConstraint(
            (
                "((notification_domain = 'need_a_sub' "
                "AND source_type = 'need_a_sub') "
                "OR (notification_domain = 'game' "
                "AND source_type IN ('official_game', 'community_game', 'game')) "
                "OR (notification_domain = 'support' "
                "AND source_type = 'support') "
                "OR (notification_domain = 'account' "
                "AND source_type IN ('account', 'payment')) "
                "OR (notification_domain IN ('app', 'admin') "
                "AND source_type IN ('pickup_lane', 'policy', 'payment')))"
            ),
            name="ck_notifications_source_domain_match",
        ),
        CheckConstraint(
            (
                "action_key IS NULL OR action_key IN ("
                "'view_game', 'view_sub_post', 'view_policy', "
                "'payment_methods', 'view_profile'"
                ")"
            ),
            name="ck_notifications_action_key",
        ),
        CheckConstraint(
            (
                "((notification_type IN ('admin_notice', 'policy_update') "
                "AND notification_category = 'app' "
                "AND notification_domain IN ('app', 'admin')) "
                "OR (notification_type = 'support_reply' "
                "AND notification_category = 'app' "
                "AND notification_domain = 'support') "
                "OR (notification_type = 'account_security' "
                "AND notification_category = 'app' "
                "AND notification_domain = 'account') "
                "OR (notification_type IN ("
                "'sub_request_received', 'sub_request_confirmed', "
                "'sub_request_declined', 'sub_waitlist_promoted_to_pending', "
                "'sub_request_canceled_by_player', "
                "'sub_request_canceled_by_owner', 'sub_post_canceled', "
                "'sub_post_removed', 'sub_post_updated'"
                ") AND notification_category = 'game_activity' "
                "AND notification_domain = 'need_a_sub') "
                "OR (notification_type IN ("
                "'booking_confirmed', 'booking_cancelled', 'booking_refunded', "
                "'payment_failed', 'game_cancelled', 'game_updated', "
                "'game_reminder', 'waitlist_joined', 'waitlist_promoted', "
                "'waitlist_expired', 'host_update', 'chat_message', "
                "'deposit_paid', 'deposit_released', 'deposit_forfeited', "
                "'game_player_added_by_admin', "
                "'game_player_removed_by_admin', 'game_host_assigned', "
                "'game_host_removed', 'game_roster_update'"
                ") AND notification_category = 'game_activity' "
                "AND notification_domain = 'game'))"
            ),
            name="ck_notifications_type_category_domain_match",
        ),
        CheckConstraint(
            "char_length(btrim(title)) > 0",
            name="ck_notifications_title_not_empty",
        ),
        CheckConstraint(
            "char_length(btrim(subject_label)) > 0",
            name="ck_notifications_subject_label_not_empty",
        ),
        CheckConstraint(
            "char_length(btrim(summary)) > 0",
            name="ck_notifications_summary_not_empty",
        ),
        CheckConstraint(
            "char_length(btrim(body)) > 0",
            name="ck_notifications_body_not_empty",
        ),
        CheckConstraint(
            "subject_starts_at IS NULL OR subject_timezone IS NOT NULL",
            name="ck_notifications_subject_start_requires_timezone",
        ),
        CheckConstraint(
            "subject_timezone IS NULL OR char_length(btrim(subject_timezone)) > 0",
            name="ck_notifications_subject_timezone_not_empty",
        ),
        CheckConstraint(
            (
                "subject_ends_at IS NULL OR subject_starts_at IS NULL "
                "OR subject_ends_at >= subject_starts_at"
            ),
            name="ck_notifications_subject_time_order",
        ),
        CheckConstraint(
            "aggregation_key IS NULL OR char_length(btrim(aggregation_key)) > 0",
            name="ck_notifications_aggregation_key_not_empty",
        ),
        CheckConstraint(
            "aggregate_count IS NULL OR aggregate_count >= 1",
            name="ck_notifications_aggregate_count_positive",
        ),
        CheckConstraint(
            "aggregate_count IS NULL OR aggregation_key IS NOT NULL",
            name="ck_notifications_aggregate_count_requires_key",
        ),
        CheckConstraint(
            "((is_read = true AND read_at IS NOT NULL) "
            "OR (is_read = false AND read_at IS NULL))",
            name="ck_notifications_read_state_matches_read_at",
        ),
        Index("ix_notifications_user_id", "user_id"),
        Index("ix_notifications_actor_user_id", "actor_user_id"),
        Index("ix_notifications_notification_category", "notification_category"),
        Index("ix_notifications_notification_domain", "notification_domain"),
        Index("ix_notifications_notification_type", "notification_type"),
        Index("ix_notifications_source_type", "source_type"),
        Index("ix_notifications_action_key", "action_key"),
        Index("ix_notifications_is_read", "is_read"),
        Index("ix_notifications_created_at", "created_at"),
        Index("ix_notifications_event_at", "event_at"),
        Index("ix_notifications_aggregation_key", "aggregation_key"),
        Index(
            "ux_notifications_user_aggregation_key",
            "user_id",
            "aggregation_key",
            unique=True,
            postgresql_where=text("aggregation_key IS NOT NULL"),
        ),
        Index(
            "ix_notifications_user_id_is_read_created_at",
            "user_id",
            "is_read",
            "created_at",
        ),
        Index(
            "ix_notifications_user_category_created_at",
            "user_id",
            "notification_category",
            "created_at",
        ),
        Index(
            "ix_notifications_user_id_is_read_event_at",
            "user_id",
            "is_read",
            "event_at",
        ),
        Index(
            "ix_notifications_user_category_event_at",
            "user_id",
            "notification_category",
            "event_at",
        ),
        Index("ix_notifications_related_game_id", "related_game_id"),
        Index("ix_notifications_related_chat_id", "related_chat_id"),
        Index("ix_notifications_related_booking_id", "related_booking_id"),
        Index("ix_notifications_related_payment_id", "related_payment_id"),
        Index("ix_notifications_related_refund_id", "related_refund_id"),
        Index("ix_notifications_related_participant_id", "related_participant_id"),
        Index("ix_notifications_related_message_id", "related_message_id"),
        Index("ix_notifications_related_sub_post_id", "related_sub_post_id"),
        Index(
            "ix_notifications_related_sub_post_request_id",
            "related_sub_post_request_id",
        ),
        Index(
            "ix_notifications_related_sub_post_position_id",
            "related_sub_post_position_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)

    notification_category: Mapped[str] = mapped_column(String(30), nullable=False)

    notification_domain: Mapped[str] = mapped_column(String(40), nullable=False)

    source_type: Mapped[str] = mapped_column(String(40), nullable=False)

    title: Mapped[str] = mapped_column(String(150), nullable=False)

    subject_label: Mapped[str] = mapped_column(String(160), nullable=False)

    summary: Mapped[str] = mapped_column(Text, nullable=False)

    body: Mapped[str] = mapped_column(Text, nullable=False)

    action_key: Mapped[str | None] = mapped_column(String(40), nullable=True)

    subject_starts_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    subject_ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    subject_timezone: Mapped[str | None] = mapped_column(String(80), nullable=True)

    event_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    aggregation_key: Mapped[str | None] = mapped_column(String(180), nullable=True)

    aggregate_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    related_game_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="SET NULL"),
        nullable=True,
    )

    related_chat_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("game_chats.id", ondelete="SET NULL"),
        nullable=True,
    )

    related_booking_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="SET NULL"),
        nullable=True,
    )

    related_payment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
    )

    related_refund_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("refunds.id", ondelete="SET NULL"),
        nullable=True,
    )

    related_participant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("game_participants.id", ondelete="SET NULL"),
        nullable=True,
    )

    related_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_messages.id", ondelete="SET NULL"),
        nullable=True,
    )

    related_sub_post_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    related_sub_post_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    related_sub_post_position_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    is_read: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )

    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
