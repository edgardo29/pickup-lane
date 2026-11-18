"""create game_change_removal_requests table"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0066_change_removal_requests"
down_revision = "0065_payment_method_ops"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "game_change_removal_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("booking_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requester_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("processed_by_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("relief_choice", sa.String(length=30), nullable=False),
        sa.Column(
            "request_status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("processing_started_at", sa.DateTime(timezone=True)),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
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
            "relief_choice IN ('original_payment_method', 'game_credit')",
            name="ck_game_change_removal_requests_relief_choice",
        ),
        sa.CheckConstraint(
            "request_status IN ('pending', 'processing', 'completed', 'rejected', 'failed')",
            name="ck_game_change_removal_requests_status",
        ),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"]),
        sa.ForeignKeyConstraint(["requester_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["processed_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
    )
    op.create_index(
        "ix_game_change_removal_requests_booking_submitted",
        "game_change_removal_requests",
        ["booking_id", "submitted_at"],
    )
    op.create_index(
        "uq_game_change_removal_requests_active_booking",
        "game_change_removal_requests",
        ["booking_id"],
        unique=True,
        postgresql_where=sa.text(
            "request_status IN ('pending', 'processing', 'failed')"
        ),
    )


def downgrade() -> None:
    op.drop_table("game_change_removal_requests")
