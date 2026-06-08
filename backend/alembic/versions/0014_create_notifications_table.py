"""create notifications table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0014_notifications"
down_revision = "0013_chat_messages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fourteenth schema migration: create notifications as user inbox/activity
    # feed records with optional links back to domain objects.
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("notification_type", sa.String(length=50), nullable=False),
        sa.Column("notification_category", sa.String(length=30), nullable=False),
        sa.Column("notification_domain", sa.String(length=40), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("subject_label", sa.String(length=160), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("action_key", sa.String(length=40), nullable=True),
        sa.Column("subject_starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("subject_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("subject_timezone", sa.String(length=80), nullable=True),
        sa.Column(
            "event_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("aggregation_key", sa.String(length=180), nullable=True),
        sa.Column("aggregate_count", sa.Integer(), nullable=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("related_game_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("related_chat_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("related_booking_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "related_participant_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("related_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("related_sub_post_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "related_sub_post_request_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "related_sub_post_position_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "is_read",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
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
                "'sub_post_removed'"
                ")"
            ),
            name="ck_notifications_notification_type",
        ),
        sa.CheckConstraint(
            "notification_category IN ('app', 'game_activity')",
            name="ck_notifications_notification_category",
        ),
        sa.CheckConstraint(
            (
                "notification_domain IN ("
                "'app', 'account', 'admin', 'support', 'game', 'need_a_sub'"
                ")"
            ),
            name="ck_notifications_notification_domain",
        ),
        sa.CheckConstraint(
            (
                "((notification_category = 'app' "
                "AND notification_domain IN ('app', 'account', 'admin', 'support')) "
                "OR (notification_category = 'game_activity' "
                "AND notification_domain IN ('game', 'need_a_sub')))"
            ),
            name="ck_notifications_category_domain_match",
        ),
        sa.CheckConstraint(
            (
                "source_type IN ("
                "'need_a_sub', 'official_game', 'community_game', 'game', "
                "'pickup_lane', 'policy', 'support', 'account', 'payment'"
                ")"
            ),
            name="ck_notifications_source_type",
        ),
        sa.CheckConstraint(
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
        sa.CheckConstraint(
            (
                "action_key IS NULL OR action_key IN ("
                "'view_game', 'view_sub_post', 'view_policy', "
                "'payment_methods', 'view_profile'"
                ")"
            ),
            name="ck_notifications_action_key",
        ),
        sa.CheckConstraint(
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
                "'sub_post_removed'"
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
        sa.CheckConstraint(
            "char_length(btrim(title)) > 0",
            name="ck_notifications_title_not_empty",
        ),
        sa.CheckConstraint(
            "char_length(btrim(subject_label)) > 0",
            name="ck_notifications_subject_label_not_empty",
        ),
        sa.CheckConstraint(
            "char_length(btrim(summary)) > 0",
            name="ck_notifications_summary_not_empty",
        ),
        sa.CheckConstraint(
            "char_length(btrim(body)) > 0",
            name="ck_notifications_body_not_empty",
        ),
        sa.CheckConstraint(
            "subject_starts_at IS NULL OR subject_timezone IS NOT NULL",
            name="ck_notifications_subject_start_requires_timezone",
        ),
        sa.CheckConstraint(
            "subject_timezone IS NULL OR char_length(btrim(subject_timezone)) > 0",
            name="ck_notifications_subject_timezone_not_empty",
        ),
        sa.CheckConstraint(
            (
                "subject_ends_at IS NULL OR subject_starts_at IS NULL "
                "OR subject_ends_at >= subject_starts_at"
            ),
            name="ck_notifications_subject_time_order",
        ),
        sa.CheckConstraint(
            "aggregation_key IS NULL OR char_length(btrim(aggregation_key)) > 0",
            name="ck_notifications_aggregation_key_not_empty",
        ),
        sa.CheckConstraint(
            "aggregate_count IS NULL OR aggregate_count >= 1",
            name="ck_notifications_aggregate_count_positive",
        ),
        sa.CheckConstraint(
            "aggregate_count IS NULL OR aggregation_key IS NOT NULL",
            name="ck_notifications_aggregate_count_requires_key",
        ),
        sa.CheckConstraint(
            "((is_read = true AND read_at IS NOT NULL) "
            "OR (is_read = false AND read_at IS NULL))",
            name="ck_notifications_read_state_matches_read_at",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["related_game_id"],
            ["games.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["related_chat_id"],
            ["game_chats.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["related_booking_id"],
            ["bookings.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["related_participant_id"],
            ["game_participants.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["related_message_id"],
            ["chat_messages.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notifications_user_id",
        "notifications",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_actor_user_id",
        "notifications",
        ["actor_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_notification_category",
        "notifications",
        ["notification_category"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_notification_domain",
        "notifications",
        ["notification_domain"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_notification_type",
        "notifications",
        ["notification_type"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_source_type",
        "notifications",
        ["source_type"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_action_key",
        "notifications",
        ["action_key"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_is_read",
        "notifications",
        ["is_read"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_created_at",
        "notifications",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_event_at",
        "notifications",
        ["event_at"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_aggregation_key",
        "notifications",
        ["aggregation_key"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_user_id_is_read_created_at",
        "notifications",
        ["user_id", "is_read", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_user_category_created_at",
        "notifications",
        ["user_id", "notification_category", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_user_id_is_read_event_at",
        "notifications",
        ["user_id", "is_read", "event_at"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_user_category_event_at",
        "notifications",
        ["user_id", "notification_category", "event_at"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_related_game_id",
        "notifications",
        ["related_game_id"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_related_chat_id",
        "notifications",
        ["related_chat_id"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_related_booking_id",
        "notifications",
        ["related_booking_id"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_related_participant_id",
        "notifications",
        ["related_participant_id"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_related_message_id",
        "notifications",
        ["related_message_id"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_related_sub_post_id",
        "notifications",
        ["related_sub_post_id"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_related_sub_post_request_id",
        "notifications",
        ["related_sub_post_request_id"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_related_sub_post_position_id",
        "notifications",
        ["related_sub_post_position_id"],
        unique=False,
    )


def downgrade() -> None:
    # Downgrade removes the notifications table and indexes because this
    # migration only introduces that single table. Some dev databases may have
    # applied an older copy of this migration before these indexes were added.
    op.drop_index(
        "ix_notifications_user_category_event_at",
        table_name="notifications",
        if_exists=True,
    )
    op.drop_index(
        "ix_notifications_user_id_is_read_event_at",
        table_name="notifications",
        if_exists=True,
    )
    op.drop_index(
        "ix_notifications_related_sub_post_position_id",
        table_name="notifications",
        if_exists=True,
    )
    op.drop_index(
        "ix_notifications_related_sub_post_request_id",
        table_name="notifications",
        if_exists=True,
    )
    op.drop_index(
        "ix_notifications_related_sub_post_id",
        table_name="notifications",
        if_exists=True,
    )
    op.drop_index(
        "ix_notifications_related_message_id",
        table_name="notifications",
        if_exists=True,
    )
    op.drop_index(
        "ix_notifications_related_participant_id",
        table_name="notifications",
        if_exists=True,
    )
    op.drop_index(
        "ix_notifications_related_booking_id",
        table_name="notifications",
        if_exists=True,
    )
    op.drop_index(
        "ix_notifications_related_chat_id",
        table_name="notifications",
        if_exists=True,
    )
    op.drop_index(
        "ix_notifications_related_game_id",
        table_name="notifications",
        if_exists=True,
    )
    op.drop_index(
        "ix_notifications_user_id_is_read_created_at",
        table_name="notifications",
        if_exists=True,
    )
    op.drop_index(
        "ix_notifications_user_category_created_at",
        table_name="notifications",
        if_exists=True,
    )
    op.drop_index(
        "ix_notifications_created_at",
        table_name="notifications",
        if_exists=True,
    )
    op.drop_index(
        "ix_notifications_aggregation_key",
        table_name="notifications",
        if_exists=True,
    )
    op.drop_index(
        "ix_notifications_event_at",
        table_name="notifications",
        if_exists=True,
    )
    op.drop_index(
        "ix_notifications_is_read",
        table_name="notifications",
        if_exists=True,
    )
    op.drop_index(
        "ix_notifications_action_key",
        table_name="notifications",
        if_exists=True,
    )
    op.drop_index(
        "ix_notifications_source_type",
        table_name="notifications",
        if_exists=True,
    )
    op.drop_index(
        "ix_notifications_notification_type",
        table_name="notifications",
        if_exists=True,
    )
    op.drop_index(
        "ix_notifications_notification_domain",
        table_name="notifications",
        if_exists=True,
    )
    op.drop_index(
        "ix_notifications_notification_category",
        table_name="notifications",
        if_exists=True,
    )
    op.drop_index(
        "ix_notifications_actor_user_id",
        table_name="notifications",
        if_exists=True,
    )
    op.drop_index(
        "ix_notifications_user_id",
        table_name="notifications",
        if_exists=True,
    )
    op.drop_table("notifications")
