"""create game participants table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0007_game_participants"
down_revision = "0006_bookings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Seventh schema migration: create the game_participants table as the
    # roster source of truth without trying to encode capacity logic here.
    op.create_table(
        "game_participants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("participant_type", sa.String(length=20), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("guest_of_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("guest_name", sa.String(length=120), nullable=True),
        sa.Column("guest_email", sa.String(length=255), nullable=True),
        sa.Column("guest_phone", sa.String(length=30), nullable=True),
        sa.Column("display_name_snapshot", sa.String(length=150), nullable=False),
        sa.Column(
            "participant_status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'pending_payment'"),
        ),
        sa.Column(
            "attendance_status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'unknown'"),
        ),
        sa.Column(
            "cancellation_type",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'none'"),
        ),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column(
            "currency",
            sa.CHAR(length=3),
            nullable=False,
            server_default=sa.text("'USD'"),
        ),
        sa.Column("roster_order", sa.Integer(), nullable=True),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checked_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "marked_attendance_by_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("attendance_decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attendance_notes", sa.Text(), nullable=True),
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
            "participant_type IN ('registered_user', 'guest', 'host', 'admin_added')",
            name="ck_game_participants_participant_type",
        ),
        sa.CheckConstraint(
            (
                "participant_status IN ("
                "'pending_payment', 'confirmed', 'waitlisted', 'cancelled', "
                "'late_cancelled', 'removed', 'refunded'"
                ")"
            ),
            name="ck_game_participants_participant_status",
        ),
        sa.CheckConstraint(
            (
                "attendance_status IN ("
                "'unknown', 'attended', 'no_show', 'excused_absence', "
                "'not_applicable'"
                ")"
            ),
            name="ck_game_participants_attendance_status",
        ),
        sa.CheckConstraint(
            (
                "cancellation_type IN ("
                "'none', 'on_time', 'late', 'host_cancelled', "
                "'admin_cancelled', 'payment_failed'"
                ")"
            ),
            name="ck_game_participants_cancellation_type",
        ),
        sa.CheckConstraint(
            "currency = 'USD'",
            name="ck_game_participants_currency",
        ),
        sa.CheckConstraint(
            "price_cents >= 0",
            name="ck_game_participants_price_cents",
        ),
        sa.CheckConstraint(
            "(roster_order IS NULL OR roster_order > 0)",
            name="ck_game_participants_roster_order",
        ),
        sa.CheckConstraint(
            "(participant_type <> 'guest' OR guest_name IS NOT NULL)",
            name="ck_game_participants_guest_requires_guest_name",
        ),
        sa.CheckConstraint(
            "(participant_type <> 'guest' OR guest_of_user_id IS NOT NULL)",
            name="ck_game_participants_guest_requires_owner",
        ),
        sa.CheckConstraint(
            "(participant_type = 'guest' OR guest_of_user_id IS NULL)",
            name="ck_game_participants_owner_only_for_guest",
        ),
        sa.CheckConstraint(
            (
                "(participant_type NOT IN ('registered_user', 'host', 'admin_added') "
                "OR user_id IS NOT NULL)"
            ),
            name="ck_game_participants_non_guest_requires_user",
        ),
        sa.CheckConstraint(
            "(participant_status <> 'confirmed' OR confirmed_at IS NOT NULL)",
            name="ck_game_participants_confirmed_requires_confirmed_at",
        ),
        sa.CheckConstraint(
            (
                "(participant_status NOT IN ('cancelled', 'late_cancelled', "
                "'removed', 'refunded') OR cancelled_at IS NOT NULL)"
            ),
            name="ck_game_participants_cancelled_requires_cancelled_at",
        ),
        sa.CheckConstraint(
            (
                "(attendance_status NOT IN ('attended', 'no_show', "
                "'excused_absence') OR attendance_decided_at IS NOT NULL)"
            ),
            name="ck_game_participants_attendance_requires_decided_at",
        ),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["games.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["booking_id"],
            ["bookings.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["guest_of_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["marked_attendance_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_game_participants_game_id",
        "game_participants",
        ["game_id"],
        unique=False,
    )
    op.create_index(
        "ix_game_participants_booking_id",
        "game_participants",
        ["booking_id"],
        unique=False,
    )
    op.create_index(
        "ix_game_participants_user_id",
        "game_participants",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_game_participants_guest_of_user_id",
        "game_participants",
        ["guest_of_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_game_participants_participant_status",
        "game_participants",
        ["participant_status"],
        unique=False,
    )
    op.create_index(
        "ix_game_participants_attendance_status",
        "game_participants",
        ["attendance_status"],
        unique=False,
    )
    op.create_index(
        "ix_game_participants_game_id_participant_status",
        "game_participants",
        ["game_id", "participant_status"],
        unique=False,
    )
    op.create_index(
        "ix_game_participants_booking_id_participant_status",
        "game_participants",
        ["booking_id", "participant_status"],
        unique=False,
    )
    op.create_index(
        "ix_game_participants_user_id_participant_status",
        "game_participants",
        ["user_id", "participant_status"],
        unique=False,
    )
    op.create_index(
        "ux_game_participants_active_registered_user_per_game",
        "game_participants",
        ["game_id", "user_id"],
        unique=True,
        postgresql_where=sa.text(
            "user_id IS NOT NULL AND participant_status IN "
            "('pending_payment', 'confirmed', 'waitlisted')"
        ),
    )


def downgrade() -> None:
    # Downgrade removes the game_participants table and its indexes because
    # this migration only introduces that single table.
    op.drop_index(
        "ux_game_participants_active_registered_user_per_game",
        table_name="game_participants",
    )
    op.drop_index(
        "ix_game_participants_user_id_participant_status",
        table_name="game_participants",
    )
    op.drop_index(
        "ix_game_participants_booking_id_participant_status",
        table_name="game_participants",
    )
    op.drop_index(
        "ix_game_participants_game_id_participant_status",
        table_name="game_participants",
    )
    op.drop_index(
        "ix_game_participants_attendance_status",
        table_name="game_participants",
    )
    op.drop_index(
        "ix_game_participants_participant_status",
        table_name="game_participants",
    )
    op.execute("DROP INDEX IF EXISTS ix_game_participants_guest_of_user_id")
    op.drop_index("ix_game_participants_user_id", table_name="game_participants")
    op.drop_index("ix_game_participants_booking_id", table_name="game_participants")
    op.drop_index("ix_game_participants_game_id", table_name="game_participants")
    op.drop_table("game_participants")
