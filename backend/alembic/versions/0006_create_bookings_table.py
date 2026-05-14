"""create bookings table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0006_bookings"
down_revision = "0005_games"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Sixth schema migration: create the bookings table for buyer orders and
    # reservation state without introducing participant or refund tables yet.
    op.create_table(
        "bookings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("buyer_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "booking_status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'pending_payment'"),
        ),
        sa.Column(
            "payment_status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'unpaid'"),
        ),
        sa.Column("participant_count", sa.Integer(), nullable=False),
        sa.Column("subtotal_cents", sa.Integer(), nullable=False),
        sa.Column(
            "platform_fee_cents",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "discount_cents",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("total_cents", sa.Integer(), nullable=False),
        sa.Column(
            "currency",
            sa.CHAR(length=3),
            nullable=False,
            server_default=sa.text("'USD'"),
        ),
        sa.Column("price_per_player_snapshot_cents", sa.Integer(), nullable=False),
        sa.Column(
            "platform_fee_snapshot_cents",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("booked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
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
                "booking_status IN ("
                "'pending_payment', 'confirmed', 'waitlisted', 'partially_cancelled', "
                "'cancelled', 'expired', 'failed'"
                ")"
            ),
            name="ck_bookings_booking_status",
        ),
        sa.CheckConstraint(
            (
                "payment_status IN ("
                "'not_required', 'unpaid', 'requires_action', 'processing', "
                "'paid', 'failed', 'partially_refunded', 'refunded', 'disputed'"
                ")"
            ),
            name="ck_bookings_payment_status",
        ),
        sa.CheckConstraint(
            "currency = 'USD'",
            name="ck_bookings_currency",
        ),
        sa.CheckConstraint(
            "participant_count > 0",
            name="ck_bookings_participant_count",
        ),
        sa.CheckConstraint(
            "subtotal_cents >= 0",
            name="ck_bookings_subtotal_cents",
        ),
        sa.CheckConstraint(
            "platform_fee_cents >= 0",
            name="ck_bookings_platform_fee_cents",
        ),
        sa.CheckConstraint(
            "discount_cents >= 0",
            name="ck_bookings_discount_cents",
        ),
        sa.CheckConstraint(
            "total_cents >= 0",
            name="ck_bookings_total_cents",
        ),
        sa.CheckConstraint(
            "price_per_player_snapshot_cents >= 0",
            name="ck_bookings_price_per_player_snapshot_cents",
        ),
        sa.CheckConstraint(
            "platform_fee_snapshot_cents >= 0",
            name="ck_bookings_platform_fee_snapshot_cents",
        ),
        sa.CheckConstraint(
            "total_cents = subtotal_cents + platform_fee_cents - discount_cents",
            name="ck_bookings_total_cents_formula",
        ),
        sa.CheckConstraint(
            "(booking_status <> 'confirmed' OR booked_at IS NOT NULL)",
            name="ck_bookings_confirmed_requires_booked_at",
        ),
        sa.CheckConstraint(
            "(booking_status <> 'cancelled' OR cancelled_at IS NOT NULL)",
            name="ck_bookings_cancelled_requires_cancelled_at",
        ),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["games.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["buyer_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["cancelled_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bookings_game_id", "bookings", ["game_id"], unique=False)
    op.create_index(
        "ix_bookings_buyer_user_id", "bookings", ["buyer_user_id"], unique=False
    )
    op.create_index(
        "ix_bookings_booking_status", "bookings", ["booking_status"], unique=False
    )
    op.create_index(
        "ix_bookings_payment_status", "bookings", ["payment_status"], unique=False
    )
    op.create_index(
        "ix_bookings_buyer_user_id_booking_status",
        "bookings",
        ["buyer_user_id", "booking_status"],
        unique=False,
    )
    op.create_index(
        "ix_bookings_game_id_booking_status",
        "bookings",
        ["game_id", "booking_status"],
        unique=False,
    )


def downgrade() -> None:
    # Downgrade removes the bookings table and its indexes because this
    # migration only introduces that single table.
    op.drop_index("ix_bookings_game_id_booking_status", table_name="bookings")
    op.drop_index("ix_bookings_buyer_user_id_booking_status", table_name="bookings")
    op.drop_index("ix_bookings_payment_status", table_name="bookings")
    op.drop_index("ix_bookings_booking_status", table_name="bookings")
    op.drop_index("ix_bookings_buyer_user_id", table_name="bookings")
    op.drop_index("ix_bookings_game_id", table_name="bookings")
    op.drop_table("bookings")
