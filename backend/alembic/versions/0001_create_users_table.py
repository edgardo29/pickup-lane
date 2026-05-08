"""create users table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_create_users_table"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # First schema migration: create the core users table that ties Firebase
    # auth identities to Pickup Lane's internal user records.
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("auth_user_id", sa.String(length=128), nullable=True),
        sa.Column(
            "role",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'player'"),
        ),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("profile_photo_url", sa.Text(), nullable=True),
        sa.Column("home_city", sa.String(length=120), nullable=True),
        sa.Column("home_state", sa.String(length=120), nullable=True),
        sa.Column(
            "account_status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column(
            "hosting_status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'not_eligible'"),
        ),
        sa.Column("hosting_suspended_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
        sa.Column(
            "member_since",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "role IN ('player', 'admin', 'moderator')",
            name="ck_users_role",
        ),
        sa.CheckConstraint(
            "account_status IN ('active', 'suspended', 'pending_deletion', 'deleted')",
            name="ck_users_account_status",
        ),
        sa.CheckConstraint(
            (
                "hosting_status IN ("
                "'not_eligible', "
                "'pending_review', "
                "'eligible', "
                "'restricted', "
                "'suspended', "
                "'banned_from_hosting'"
                ")"
            ),
            name="ck_users_hosting_status",
        ),
        sa.UniqueConstraint("auth_user_id", name="uq_users_auth_user_id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("phone", name="uq_users_phone"),
        sa.UniqueConstraint(
            "stripe_customer_id",
            name="uq_users_stripe_customer_id",
        ),
    )


def downgrade() -> None:
    # Downgrade removes the users table entirely because this migration only
    # introduces that single table.
    op.drop_table("users")
