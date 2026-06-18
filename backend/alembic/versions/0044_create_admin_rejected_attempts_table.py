"""create admin rejected attempts table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0044_admin_rejected_attempts"
down_revision = "0043_support_flags"
branch_labels = None
depends_on = None


ADMIN_REJECTED_ATTEMPT_TYPE_CHECK = (
    "attempt_type IN ('issue_credit_rejected', 'reverse_credit_rejected')"
)


ADMIN_REJECTED_ATTEMPT_REJECTION_MODE_CHECK = (
    "rejection_mode IN ('permission_denied_preload', 'domain_rejected_postload')"
)


def upgrade() -> None:
    op.create_table(
        "admin_rejected_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("admin_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("attempt_type", sa.String(length=80), nullable=False),
        sa.Column("rejection_mode", sa.String(length=40), nullable=False),
        sa.Column("response_status_code", sa.Integer(), nullable=False),
        sa.Column("route_method", sa.String(length=10), nullable=False),
        sa.Column("route_path", sa.String(length=240), nullable=False),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "target_game_credit_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            ADMIN_REJECTED_ATTEMPT_TYPE_CHECK,
            name="ck_admin_rejected_attempts_attempt_type",
        ),
        sa.CheckConstraint(
            ADMIN_REJECTED_ATTEMPT_REJECTION_MODE_CHECK,
            name="ck_admin_rejected_attempts_rejection_mode",
        ),
        sa.CheckConstraint(
            "response_status_code BETWEEN 400 AND 599",
            name="ck_admin_rejected_attempts_response_status_code",
        ),
        sa.ForeignKeyConstraint(
            ["admin_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_game_credit_id"],
            ["game_credits.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_admin_rejected_attempts_admin_user_id",
        "admin_rejected_attempts",
        ["admin_user_id"],
    )
    op.create_index(
        "ix_admin_rejected_attempts_attempt_type",
        "admin_rejected_attempts",
        ["attempt_type"],
    )
    op.create_index(
        "ix_admin_rejected_attempts_rejection_mode",
        "admin_rejected_attempts",
        ["rejection_mode"],
    )
    op.create_index(
        "ix_admin_rejected_attempts_created_at",
        "admin_rejected_attempts",
        ["created_at"],
    )
    op.create_index(
        "ix_admin_rejected_attempts_target_user_id",
        "admin_rejected_attempts",
        ["target_user_id"],
    )
    op.create_index(
        "ix_admin_rejected_attempts_target_game_credit_id",
        "admin_rejected_attempts",
        ["target_game_credit_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_admin_rejected_attempts_target_game_credit_id",
        table_name="admin_rejected_attempts",
    )
    op.drop_index(
        "ix_admin_rejected_attempts_target_user_id",
        table_name="admin_rejected_attempts",
    )
    op.drop_index(
        "ix_admin_rejected_attempts_created_at",
        table_name="admin_rejected_attempts",
    )
    op.drop_index(
        "ix_admin_rejected_attempts_rejection_mode",
        table_name="admin_rejected_attempts",
    )
    op.drop_index(
        "ix_admin_rejected_attempts_attempt_type",
        table_name="admin_rejected_attempts",
    )
    op.drop_index(
        "ix_admin_rejected_attempts_admin_user_id",
        table_name="admin_rejected_attempts",
    )
    op.drop_table("admin_rejected_attempts")
