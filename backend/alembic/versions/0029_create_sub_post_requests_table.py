"""create sub post requests table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0029_sub_post_requests"
down_revision = "0028_sub_post_positions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Twenty-ninth schema migration: create player requests for Need a Sub
    # posts, tied to both the parent post and an exact position row.
    op.create_table(
        "sub_post_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sub_post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sub_post_position_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requester_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "request_status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("declined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sub_waitlisted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("no_show_reported_at", sa.DateTime(timezone=True), nullable=True),
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
                "request_status IN ('pending', 'confirmed', 'declined', "
                "'sub_waitlist', 'canceled_by_player', "
                "'canceled_by_owner', 'no_show_reported', 'expired')"
            ),
            name="ck_sub_post_requests_request_status",
        ),
        sa.CheckConstraint(
            "request_status != 'confirmed' OR confirmed_at IS NOT NULL",
            name="ck_sub_post_requests_confirmed_requires_confirmed_at",
        ),
        sa.CheckConstraint(
            "request_status != 'declined' OR declined_at IS NOT NULL",
            name="ck_sub_post_requests_declined_requires_declined_at",
        ),
        sa.CheckConstraint(
            "request_status != 'sub_waitlist' OR sub_waitlisted_at IS NOT NULL",
            name="ck_sub_post_requests_waitlist_requires_waitlisted_at",
        ),
        sa.CheckConstraint(
            (
                "request_status NOT IN ('canceled_by_player', 'canceled_by_owner') "
                "OR canceled_at IS NOT NULL"
            ),
            name="ck_sub_post_requests_canceled_requires_canceled_at",
        ),
        sa.CheckConstraint(
            "request_status != 'expired' OR expired_at IS NOT NULL",
            name="ck_sub_post_requests_expired_requires_expired_at",
        ),
        sa.CheckConstraint(
            "request_status != 'no_show_reported' OR no_show_reported_at IS NOT NULL",
            name="ck_sub_post_requests_no_show_requires_reported_at",
        ),
        sa.ForeignKeyConstraint(
            ["sub_post_id"],
            ["sub_posts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sub_post_position_id"],
            ["sub_post_positions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["sub_post_position_id", "sub_post_id"],
            ["sub_post_positions.id", "sub_post_positions.sub_post_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["requester_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sub_post_requests_sub_post_id", "sub_post_requests", ["sub_post_id"])
    op.create_index(
        "ix_sub_post_requests_sub_post_position_id",
        "sub_post_requests",
        ["sub_post_position_id"],
    )
    op.create_index(
        "ix_sub_post_requests_requester_user_id",
        "sub_post_requests",
        ["requester_user_id"],
    )
    op.create_index(
        "ix_sub_post_requests_post_status",
        "sub_post_requests",
        ["sub_post_id", "request_status"],
    )
    op.create_index(
        "ix_sub_post_requests_position_status",
        "sub_post_requests",
        ["sub_post_position_id", "request_status"],
    )
    op.create_index(
        "ix_sub_post_requests_requester_status",
        "sub_post_requests",
        ["requester_user_id", "request_status"],
    )
    op.create_index(
        "uq_sub_post_requests_active_post_requester",
        "sub_post_requests",
        ["sub_post_id", "requester_user_id"],
        unique=True,
        postgresql_where=sa.text(
            "request_status IN ('pending', 'confirmed', 'sub_waitlist')"
        ),
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_sub_post_requests_active_post_requester")
    op.drop_index("ix_sub_post_requests_requester_status", table_name="sub_post_requests")
    op.drop_index("ix_sub_post_requests_position_status", table_name="sub_post_requests")
    op.drop_index("ix_sub_post_requests_post_status", table_name="sub_post_requests")
    op.drop_index(
        "ix_sub_post_requests_requester_user_id",
        table_name="sub_post_requests",
    )
    op.drop_index(
        "ix_sub_post_requests_sub_post_position_id",
        table_name="sub_post_requests",
    )
    op.drop_index("ix_sub_post_requests_sub_post_id", table_name="sub_post_requests")
    op.drop_table("sub_post_requests")
