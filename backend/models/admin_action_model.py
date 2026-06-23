import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


# Admin actions store audit rows for important admin/support actions across
# users, games, payments, venues, and chat messages.
class AdminAction(Base):
    __tablename__ = "admin_actions"
    __table_args__ = (
        CheckConstraint(
            (
                "action_type IN ("
                "'cancel_game', 'refund_booking', 'create_refund', "
                "'update_refund', 'mark_no_show', "
                "'create_payment', 'update_payment', "
                "'reverse_no_show', 'suspend_user', 'unsuspend_user', "
                "'restrict_hosting', 'restore_hosting', 'approve_venue', "
                "'delete_user', "
                "'reject_venue', 'create_venue_image', 'update_venue_image', "
                "'remove_venue_image', 'remove_chat_message', 'hide_chat_message', "
                "'update_game', 'create_game_chat', 'update_game_chat', "
                "'update_booking', "
                "'update_participant', 'issue_credit', 'reverse_credit', "
                "'create_official_game', 'update_official_game', "
                "'assign_official_host', 'remove_official_host', "
                "'admin_add_player', 'admin_remove_player', 'waive_payment', "
                "'remove_sub_post', 'hide_unsafe_community_payment_text', "
                "'create_notification', 'update_notification', "
                "'create_platform_notice_campaign', "
                "'update_platform_notice_campaign', "
                "'send_platform_notice_campaign', "
                "'retry_platform_notice_campaign', "
                "'change_staff_role', 'append_audit_note', "
                "'resolve_support_flag'"
                ")"
            ),
            name="ck_admin_actions_action_type",
        ),
        CheckConstraint(
            (
                "target_user_id IS NOT NULL "
                "OR target_game_id IS NOT NULL "
                "OR target_booking_id IS NOT NULL "
                "OR target_participant_id IS NOT NULL "
                "OR target_payment_id IS NOT NULL "
                "OR target_refund_id IS NOT NULL "
                "OR target_game_credit_id IS NOT NULL "
                "OR target_venue_id IS NOT NULL "
                "OR target_venue_image_id IS NOT NULL "
                "OR target_message_id IS NOT NULL "
                "OR target_sub_post_id IS NOT NULL "
                "OR target_sub_post_request_id IS NOT NULL "
                "OR target_sub_post_position_id IS NOT NULL "
                "OR target_sub_chat_message_id IS NOT NULL "
                "OR target_notification_id IS NOT NULL "
                "OR target_platform_notice_campaign_id IS NOT NULL "
                "OR target_admin_action_id IS NOT NULL "
                "OR target_support_flag_id IS NOT NULL"
            ),
            name="ck_admin_actions_target_required",
        ),
        Index("ix_admin_actions_admin_user_id", "admin_user_id"),
        Index("ix_admin_actions_action_type", "action_type"),
        Index("ix_admin_actions_created_at", "created_at"),
        Index("ix_admin_actions_target_user_id", "target_user_id"),
        Index("ix_admin_actions_target_game_id", "target_game_id"),
        Index("ix_admin_actions_target_booking_id", "target_booking_id"),
        Index("ix_admin_actions_target_participant_id", "target_participant_id"),
        Index("ix_admin_actions_target_payment_id", "target_payment_id"),
        Index("ix_admin_actions_target_refund_id", "target_refund_id"),
        Index("ix_admin_actions_target_game_credit_id", "target_game_credit_id"),
        Index("ix_admin_actions_target_venue_id", "target_venue_id"),
        Index("ix_admin_actions_target_venue_image_id", "target_venue_image_id"),
        Index("ix_admin_actions_target_message_id", "target_message_id"),
        Index("ix_admin_actions_target_sub_post_id", "target_sub_post_id"),
        Index(
            "ix_admin_actions_target_sub_post_request_id",
            "target_sub_post_request_id",
        ),
        Index(
            "ix_admin_actions_target_sub_post_position_id",
            "target_sub_post_position_id",
        ),
        Index(
            "ix_admin_actions_target_sub_chat_message_id",
            "target_sub_chat_message_id",
        ),
        Index("ix_admin_actions_target_notification_id", "target_notification_id"),
        Index(
            "ix_admin_actions_target_platform_notice_campaign_id",
            "target_platform_notice_campaign_id",
        ),
        Index("ix_admin_actions_target_admin_action_id", "target_admin_action_id"),
        Index("ix_admin_actions_target_support_flag_id", "target_support_flag_id"),
        Index("ix_admin_actions_idempotency_key", "idempotency_key"),
        Index(
            "uq_admin_actions_audit_note_idempotency",
            "admin_user_id",
            "target_admin_action_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text(
                "action_type = 'append_audit_note' AND idempotency_key IS NOT NULL"
            ),
        ),
        Index(
            "uq_admin_actions_suspend_user_idempotency",
            "admin_user_id",
            "target_user_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text(
                "action_type = 'suspend_user' AND idempotency_key IS NOT NULL"
            ),
        ),
        Index(
            "uq_admin_actions_unsuspend_user_idempotency",
            "admin_user_id",
            "target_user_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text(
                "action_type = 'unsuspend_user' AND idempotency_key IS NOT NULL"
            ),
        ),
        Index(
            "uq_admin_actions_restrict_hosting_idempotency",
            "admin_user_id",
            "target_user_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text(
                "action_type = 'restrict_hosting' AND idempotency_key IS NOT NULL"
            ),
        ),
        Index(
            "uq_admin_actions_restore_hosting_idempotency",
            "admin_user_id",
            "target_user_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text(
                "action_type = 'restore_hosting' AND idempotency_key IS NOT NULL"
            ),
        ),
        Index(
            "uq_admin_actions_change_staff_role_idempotency",
            "admin_user_id",
            "target_user_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text(
                "action_type = 'change_staff_role' AND idempotency_key IS NOT NULL"
            ),
        ),
        Index(
            "uq_admin_actions_delete_user_idempotency",
            "admin_user_id",
            "target_user_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text(
                "action_type = 'delete_user' AND idempotency_key IS NOT NULL"
            ),
        ),
        Index(
            "uq_admin_actions_hide_unsafe_community_payment_text_idempotency",
            "admin_user_id",
            "target_game_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text(
                "action_type = 'hide_unsafe_community_payment_text' "
                "AND idempotency_key IS NOT NULL"
            ),
        ),
        Index(
            "uq_admin_actions_remove_sub_post_idempotency",
            "admin_user_id",
            "target_sub_post_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text(
                "action_type = 'remove_sub_post' AND idempotency_key IS NOT NULL"
            ),
        ),
        Index(
            "uq_admin_actions_hide_sub_chat_message_idempotency",
            "admin_user_id",
            "target_sub_chat_message_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text(
                "action_type = 'hide_chat_message' "
                "AND target_sub_chat_message_id IS NOT NULL "
                "AND idempotency_key IS NOT NULL"
            ),
        ),
        Index(
            "uq_admin_actions_remove_sub_chat_message_idempotency",
            "admin_user_id",
            "target_sub_chat_message_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text(
                "action_type = 'remove_chat_message' "
                "AND target_sub_chat_message_id IS NOT NULL "
                "AND idempotency_key IS NOT NULL"
            ),
        ),
        Index(
            "ix_admin_actions_admin_user_id_created_at",
            "admin_user_id",
            "created_at",
        ),
        Index(
            "ix_admin_actions_action_type_created_at",
            "action_type",
            "created_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)

    admin_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )

    action_type: Mapped[str] = mapped_column(String(60), nullable=False)

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

    target_participant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("game_participants.id", ondelete="SET NULL"),
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

    target_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_messages.id", ondelete="SET NULL"),
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

    target_sub_post_position_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sub_post_positions.id", ondelete="SET NULL"),
        nullable=True,
    )

    target_sub_chat_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sub_post_chat_messages.id", ondelete="SET NULL"),
        nullable=True,
    )

    target_notification_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notifications.id", ondelete="SET NULL"),
        nullable=True,
    )

    target_platform_notice_campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform_notice_campaigns.id", ondelete="SET NULL"),
        nullable=True,
    )

    target_admin_action_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_actions.id", ondelete="RESTRICT"),
        nullable=True,
    )

    target_support_flag_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("support_flags.id", ondelete="SET NULL"),
        nullable=True,
    )

    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    metadata_: Mapped[dict | None] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
    )

    idempotency_key: Mapped[str | None] = mapped_column(String(160), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
