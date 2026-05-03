"""create admin actions table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0019_admin_actions"
down_revision = "0018_user_stats"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nineteenth schema migration: create admin_actions as an audit trail for
    # important admin/support actions across users, games, payments, and chats.
    op.create_table(
        "admin_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("admin_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_type", sa.String(length=60), nullable=False),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_game_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_booking_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "target_participant_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("target_payment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_venue_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "target_host_deposit_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            (
                "action_type IN ("
                "'cancel_game', 'refund_booking', 'mark_no_show', "
                "'reverse_no_show', 'suspend_user', 'unsuspend_user', "
                "'restrict_hosting', 'restore_hosting', 'approve_venue', "
                "'reject_venue', 'remove_chat_message', 'hide_chat_message', "
                "'forfeit_host_deposit', 'release_host_deposit', "
                "'waive_host_deposit', 'update_game', 'update_booking', "
                "'update_participant'"
                ")"
            ),
            name="ck_admin_actions_action_type",
        ),
        sa.CheckConstraint(
            (
                "target_user_id IS NOT NULL "
                "OR target_game_id IS NOT NULL "
                "OR target_booking_id IS NOT NULL "
                "OR target_participant_id IS NOT NULL "
                "OR target_payment_id IS NOT NULL "
                "OR target_venue_id IS NOT NULL "
                "OR target_message_id IS NOT NULL "
                "OR target_host_deposit_id IS NOT NULL"
            ),
            name="ck_admin_actions_target_required",
        ),
        sa.ForeignKeyConstraint(
            ["admin_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_game_id"],
            ["games.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_booking_id"],
            ["bookings.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_participant_id"],
            ["game_participants.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_payment_id"],
            ["payments.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_venue_id"],
            ["venues.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_message_id"],
            ["chat_messages.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_host_deposit_id"],
            ["host_deposits.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_admin_actions_admin_user_id",
        "admin_actions",
        ["admin_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_action_type",
        "admin_actions",
        ["action_type"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_created_at",
        "admin_actions",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_user_id",
        "admin_actions",
        ["target_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_game_id",
        "admin_actions",
        ["target_game_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_booking_id",
        "admin_actions",
        ["target_booking_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_participant_id",
        "admin_actions",
        ["target_participant_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_payment_id",
        "admin_actions",
        ["target_payment_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_venue_id",
        "admin_actions",
        ["target_venue_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_message_id",
        "admin_actions",
        ["target_message_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_target_host_deposit_id",
        "admin_actions",
        ["target_host_deposit_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_admin_user_id_created_at",
        "admin_actions",
        ["admin_user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_admin_actions_action_type_created_at",
        "admin_actions",
        ["action_type", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    # Downgrade removes the admin_actions table and indexes because this
    # migration only introduces that single audit table.
    op.drop_index(
        "ix_admin_actions_action_type_created_at",
        table_name="admin_actions",
    )
    op.drop_index(
        "ix_admin_actions_admin_user_id_created_at",
        table_name="admin_actions",
    )
    op.drop_index(
        "ix_admin_actions_target_host_deposit_id",
        table_name="admin_actions",
    )
    op.drop_index("ix_admin_actions_target_message_id", table_name="admin_actions")
    op.drop_index("ix_admin_actions_target_venue_id", table_name="admin_actions")
    op.drop_index("ix_admin_actions_target_payment_id", table_name="admin_actions")
    op.drop_index(
        "ix_admin_actions_target_participant_id",
        table_name="admin_actions",
    )
    op.drop_index("ix_admin_actions_target_booking_id", table_name="admin_actions")
    op.drop_index("ix_admin_actions_target_game_id", table_name="admin_actions")
    op.drop_index("ix_admin_actions_target_user_id", table_name="admin_actions")
    op.drop_index("ix_admin_actions_created_at", table_name="admin_actions")
    op.drop_index("ix_admin_actions_action_type", table_name="admin_actions")
    op.drop_index("ix_admin_actions_admin_user_id", table_name="admin_actions")
    op.drop_table("admin_actions")