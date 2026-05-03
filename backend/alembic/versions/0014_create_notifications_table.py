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
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("related_game_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("related_booking_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "related_participant_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("related_message_id", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.CheckConstraint(
            (
                "notification_type IN ("
                "'booking_confirmed', 'booking_cancelled', 'booking_refunded', "
                "'payment_failed', 'game_cancelled', 'game_updated', "
                "'game_reminder', 'waitlist_joined', 'waitlist_promoted', "
                "'waitlist_expired', 'host_update', 'chat_message', "
                "'deposit_paid', 'deposit_released', 'deposit_forfeited', "
                "'admin_notice'"
                ")"
            ),
            name="ck_notifications_notification_type",
        ),
        sa.CheckConstraint(
            "char_length(btrim(title)) > 0",
            name="ck_notifications_title_not_empty",
        ),
        sa.CheckConstraint(
            "char_length(btrim(body)) > 0",
            name="ck_notifications_body_not_empty",
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
            ["related_game_id"],
            ["games.id"],
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
        "ix_notifications_notification_type",
        "notifications",
        ["notification_type"],
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
        "ix_notifications_user_id_is_read_created_at",
        "notifications",
        ["user_id", "is_read", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_related_game_id",
        "notifications",
        ["related_game_id"],
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


def downgrade() -> None:
    # Downgrade removes the notifications table and indexes because this
    # migration only introduces that single table.
    op.drop_index("ix_notifications_related_message_id", table_name="notifications")
    op.drop_index(
        "ix_notifications_related_participant_id",
        table_name="notifications",
    )
    op.drop_index("ix_notifications_related_booking_id", table_name="notifications")
    op.drop_index("ix_notifications_related_game_id", table_name="notifications")
    op.drop_index(
        "ix_notifications_user_id_is_read_created_at",
        table_name="notifications",
    )
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_index("ix_notifications_is_read", table_name="notifications")
    op.drop_index("ix_notifications_notification_type", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
