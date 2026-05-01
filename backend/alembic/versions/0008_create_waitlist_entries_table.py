"""create waitlist entries table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0008_waitlist_entries"
down_revision = "0007_game_participants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Eighth schema migration: create waitlist_entries as the lifecycle record
    # for users waiting on game capacity and short-lived promotion windows.
    op.create_table(
        "waitlist_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "party_size",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "waitlist_status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column(
            "promoted_booking_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("promotion_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
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
                "waitlist_status IN ("
                "'active', 'promoted', 'accepted', 'declined', 'expired', "
                "'cancelled', 'removed'"
                ")"
            ),
            name="ck_waitlist_entries_waitlist_status",
        ),
        sa.CheckConstraint(
            "party_size > 0",
            name="ck_waitlist_entries_party_size",
        ),
        sa.CheckConstraint(
            "position > 0",
            name="ck_waitlist_entries_position",
        ),
        sa.CheckConstraint(
            "(waitlist_status <> 'promoted' OR promoted_at IS NOT NULL)",
            name="ck_waitlist_entries_promoted_requires_promoted_at",
        ),
        sa.CheckConstraint(
            "(waitlist_status <> 'promoted' OR promotion_expires_at IS NOT NULL)",
            name="ck_waitlist_entries_promoted_requires_promotion_expires_at",
        ),
        sa.CheckConstraint(
            "(waitlist_status <> 'cancelled' OR cancelled_at IS NOT NULL)",
            name="ck_waitlist_entries_cancelled_requires_cancelled_at",
        ),
        sa.CheckConstraint(
            "(waitlist_status <> 'expired' OR expired_at IS NOT NULL)",
            name="ck_waitlist_entries_expired_requires_expired_at",
        ),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["games.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["promoted_booking_id"],
            ["bookings.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_waitlist_entries_game_id",
        "waitlist_entries",
        ["game_id"],
        unique=False,
    )
    op.create_index(
        "ix_waitlist_entries_user_id",
        "waitlist_entries",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_waitlist_entries_waitlist_status",
        "waitlist_entries",
        ["waitlist_status"],
        unique=False,
    )
    op.create_index(
        "ix_waitlist_entries_game_id_waitlist_status_position",
        "waitlist_entries",
        ["game_id", "waitlist_status", "position"],
        unique=False,
    )
    op.create_index(
        "ix_waitlist_entries_user_id_waitlist_status",
        "waitlist_entries",
        ["user_id", "waitlist_status"],
        unique=False,
    )
    op.create_index(
        "ux_waitlist_entries_active_user_per_game",
        "waitlist_entries",
        ["game_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("waitlist_status = 'active'"),
    )
    op.create_index(
        "ux_waitlist_entries_active_position_per_game",
        "waitlist_entries",
        ["game_id", "position"],
        unique=True,
        postgresql_where=sa.text("waitlist_status = 'active'"),
    )


def downgrade() -> None:
    # Downgrade removes the waitlist_entries table and its indexes because
    # this migration only introduces that single table.
    op.drop_index(
        "ux_waitlist_entries_active_position_per_game",
        table_name="waitlist_entries",
    )
    op.drop_index(
        "ux_waitlist_entries_active_user_per_game",
        table_name="waitlist_entries",
    )
    op.drop_index(
        "ix_waitlist_entries_user_id_waitlist_status",
        table_name="waitlist_entries",
    )
    op.drop_index(
        "ix_waitlist_entries_game_id_waitlist_status_position",
        table_name="waitlist_entries",
    )
    op.drop_index(
        "ix_waitlist_entries_waitlist_status",
        table_name="waitlist_entries",
    )
    op.drop_index("ix_waitlist_entries_user_id", table_name="waitlist_entries")
    op.drop_index("ix_waitlist_entries_game_id", table_name="waitlist_entries")
    op.drop_table("waitlist_entries")
