"""create game status history table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0015_game_status_history"
down_revision = "0014_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fifteenth schema migration: create game_status_history as append-only
    # audit rows for game publish/status lifecycle changes.
    op.create_table(
        "game_status_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("old_publish_status", sa.String(length=30), nullable=True),
        sa.Column("new_publish_status", sa.String(length=30), nullable=False),
        sa.Column("old_game_status", sa.String(length=30), nullable=True),
        sa.Column("new_game_status", sa.String(length=30), nullable=False),
        sa.Column("changed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "change_source",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'user'"),
        ),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            (
                "(old_publish_status IS NULL OR old_publish_status IN "
                "('draft', 'published', 'archived'))"
            ),
            name="ck_game_status_history_old_publish_status",
        ),
        sa.CheckConstraint(
            "new_publish_status IN ('draft', 'published', 'archived')",
            name="ck_game_status_history_new_publish_status",
        ),
        sa.CheckConstraint(
            (
                "(old_game_status IS NULL OR old_game_status IN "
                "('scheduled', 'full', 'cancelled', 'completed', 'abandoned'))"
            ),
            name="ck_game_status_history_old_game_status",
        ),
        sa.CheckConstraint(
            (
                "new_game_status IN "
                "('scheduled', 'full', 'cancelled', 'completed', 'abandoned')"
            ),
            name="ck_game_status_history_new_game_status",
        ),
        sa.CheckConstraint(
            (
                "change_source IN ("
                "'user', 'host', 'admin', 'system', 'payment_webhook', "
                "'scheduled_job'"
                ")"
            ),
            name="ck_game_status_history_change_source",
        ),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["games.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["changed_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_game_status_history_game_id",
        "game_status_history",
        ["game_id"],
        unique=False,
    )
    op.create_index(
        "ix_game_status_history_changed_by_user_id",
        "game_status_history",
        ["changed_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_game_status_history_change_source",
        "game_status_history",
        ["change_source"],
        unique=False,
    )
    op.create_index(
        "ix_game_status_history_created_at",
        "game_status_history",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_game_status_history_game_id_created_at",
        "game_status_history",
        ["game_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    # Downgrade removes the game_status_history table and indexes because this
    # migration only introduces that single table.
    op.drop_index(
        "ix_game_status_history_game_id_created_at",
        table_name="game_status_history",
    )
    op.drop_index("ix_game_status_history_created_at", table_name="game_status_history")
    op.drop_index(
        "ix_game_status_history_change_source",
        table_name="game_status_history",
    )
    op.drop_index(
        "ix_game_status_history_changed_by_user_id",
        table_name="game_status_history",
    )
    op.drop_index("ix_game_status_history_game_id", table_name="game_status_history")
    op.drop_table("game_status_history")
