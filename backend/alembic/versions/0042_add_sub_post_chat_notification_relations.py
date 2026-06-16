"""add sub post chat notification relations"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0042_sub_chat_notifs"
down_revision = "0041_sub_post_chat_reads"
branch_labels = None
depends_on = None


NOTIFICATION_TYPE_CHECK = (
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
    "'sub_post_removed', 'sub_post_updated', 'sub_chat_message'"
    ")"
)


NOTIFICATION_TYPE_DOMAIN_CHECK = (
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
    "'sub_post_removed', 'sub_post_updated', 'sub_chat_message'"
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
)


OLD_NOTIFICATION_TYPE_CHECK = (
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
)


OLD_NOTIFICATION_TYPE_DOMAIN_CHECK = (
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
)


def upgrade() -> None:
    op.drop_constraint(
        "ck_notifications_notification_type",
        "notifications",
        type_="check",
    )
    op.drop_constraint(
        "ck_notifications_type_category_domain_match",
        "notifications",
        type_="check",
    )
    op.add_column(
        "notifications",
        sa.Column(
            "related_sub_post_chat_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "notifications",
        sa.Column(
            "related_sub_post_chat_message_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_notifications_related_sub_post_chat_id",
        "notifications",
        "sub_post_chats",
        ["related_sub_post_chat_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_notifications_related_sub_post_chat_message_id",
        "notifications",
        "sub_post_chat_messages",
        ["related_sub_post_chat_message_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_notifications_related_sub_post_chat_id",
        "notifications",
        ["related_sub_post_chat_id"],
    )
    op.create_index(
        "ix_notifications_related_sub_post_chat_message_id",
        "notifications",
        ["related_sub_post_chat_message_id"],
    )
    op.create_check_constraint(
        "ck_notifications_notification_type",
        "notifications",
        NOTIFICATION_TYPE_CHECK,
    )
    op.create_check_constraint(
        "ck_notifications_type_category_domain_match",
        "notifications",
        NOTIFICATION_TYPE_DOMAIN_CHECK,
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_notifications_type_category_domain_match",
        "notifications",
        type_="check",
    )
    op.drop_constraint(
        "ck_notifications_notification_type",
        "notifications",
        type_="check",
    )
    op.drop_index(
        "ix_notifications_related_sub_post_chat_message_id",
        table_name="notifications",
    )
    op.drop_index(
        "ix_notifications_related_sub_post_chat_id",
        table_name="notifications",
    )
    op.drop_constraint(
        "fk_notifications_related_sub_post_chat_message_id",
        "notifications",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_notifications_related_sub_post_chat_id",
        "notifications",
        type_="foreignkey",
    )
    op.drop_column("notifications", "related_sub_post_chat_message_id")
    op.drop_column("notifications", "related_sub_post_chat_id")
    op.create_check_constraint(
        "ck_notifications_notification_type",
        "notifications",
        OLD_NOTIFICATION_TYPE_CHECK,
    )
    op.create_check_constraint(
        "ck_notifications_type_category_domain_match",
        "notifications",
        OLD_NOTIFICATION_TYPE_DOMAIN_CHECK,
    )
