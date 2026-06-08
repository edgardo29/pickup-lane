"""add paid waitlist auto-charge state"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0036_paid_waitlist_auto_charge"
down_revision = "0035_venue_images"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_waitlist_entries_waitlist_status",
        "waitlist_entries",
        type_="check",
    )
    op.drop_index(
        "ux_waitlist_entries_active_user_per_game",
        table_name="waitlist_entries",
        postgresql_where=sa.text("waitlist_status = 'active'"),
    )
    op.add_column(
        "waitlist_entries",
        sa.Column("auto_charge_consent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "waitlist_entries",
        sa.Column("auto_charge_consent_version", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "waitlist_entries",
        sa.Column(
            "authorized_payment_method_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "waitlist_entries",
        sa.Column(
            "authorized_stripe_payment_method_id",
            sa.String(length=255),
            nullable=True,
        ),
    )
    op.add_column(
        "waitlist_entries",
        sa.Column(
            "authorized_payment_method_brand",
            sa.String(length=50),
            nullable=True,
        ),
    )
    op.add_column(
        "waitlist_entries",
        sa.Column(
            "authorized_payment_method_last4",
            sa.String(length=4),
            nullable=True,
        ),
    )
    op.add_column(
        "waitlist_entries",
        sa.Column("authorized_amount_cents", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_waitlist_entries_authorized_payment_method",
        "waitlist_entries",
        "user_payment_methods",
        ["authorized_payment_method_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "ck_waitlist_entries_waitlist_status",
        "waitlist_entries",
        (
            "waitlist_status IN ("
            "'active', 'promoted', 'accepted', 'declined', 'expired', "
            "'cancelled', 'removed', 'payment_processing', 'payment_failed'"
            ")"
        ),
    )
    op.create_check_constraint(
        "ck_waitlist_entries_authorized_amount_non_negative",
        "waitlist_entries",
        "(authorized_amount_cents IS NULL OR authorized_amount_cents >= 0)",
    )
    op.create_index(
        "ux_waitlist_entries_active_user_per_game",
        "waitlist_entries",
        ["game_id", "user_id"],
        unique=True,
        postgresql_where=sa.text(
            "waitlist_status IN ('active', 'payment_processing')"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "ux_waitlist_entries_active_user_per_game",
        table_name="waitlist_entries",
        postgresql_where=sa.text(
            "waitlist_status IN ('active', 'payment_processing')"
        ),
    )
    op.drop_constraint(
        "ck_waitlist_entries_authorized_amount_non_negative",
        "waitlist_entries",
        type_="check",
    )
    op.drop_constraint(
        "ck_waitlist_entries_waitlist_status",
        "waitlist_entries",
        type_="check",
    )
    op.drop_constraint(
        "fk_waitlist_entries_authorized_payment_method",
        "waitlist_entries",
        type_="foreignkey",
    )
    op.drop_column("waitlist_entries", "authorized_amount_cents")
    op.drop_column("waitlist_entries", "authorized_payment_method_last4")
    op.drop_column("waitlist_entries", "authorized_payment_method_brand")
    op.drop_column("waitlist_entries", "authorized_stripe_payment_method_id")
    op.drop_column("waitlist_entries", "authorized_payment_method_id")
    op.drop_column("waitlist_entries", "auto_charge_consent_version")
    op.drop_column("waitlist_entries", "auto_charge_consent_at")
    op.create_check_constraint(
        "ck_waitlist_entries_waitlist_status",
        "waitlist_entries",
        (
            "waitlist_status IN ("
            "'active', 'promoted', 'accepted', 'declined', 'expired', "
            "'cancelled', 'removed'"
            ")"
        ),
    )
    op.create_index(
        "ux_waitlist_entries_active_user_per_game",
        "waitlist_entries",
        ["game_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("waitlist_status = 'active'"),
    )
