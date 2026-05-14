"""create community hosting model"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0032_community_hosting_model"
down_revision = "0031_sub_post_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the host setup/defaults table, community game details snapshots,
    # and paid/waived community publish fees.
    op.create_table(
        "host_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("phone_number_e164", sa.String(length=30), nullable=True),
        sa.Column("phone_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("host_rules_accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("host_rules_version", sa.String(length=30), nullable=True),
        sa.Column("host_setup_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("host_age_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "default_payment_methods",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("default_payment_instructions", sa.Text(), nullable=True),
        sa.Column("default_payment_due_timing", sa.String(length=30), nullable=True),
        sa.Column("default_refund_policy", sa.Text(), nullable=True),
        sa.Column("default_game_rules", sa.Text(), nullable=True),
        sa.Column("default_arrival_expectations", sa.Text(), nullable=True),
        sa.Column("default_equipment_notes", sa.Text(), nullable=True),
        sa.Column("default_behavior_rules", sa.Text(), nullable=True),
        sa.Column("default_no_show_policy", sa.Text(), nullable=True),
        sa.Column("default_player_message", sa.Text(), nullable=True),
        sa.Column("first_free_game_used_at", sa.DateTime(timezone=True), nullable=True),
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
            "jsonb_typeof(default_payment_methods) = 'array'",
            name="ck_host_profiles_default_payment_methods_array",
        ),
        sa.CheckConstraint(
            (
                "default_payment_due_timing IS NULL OR "
                "default_payment_due_timing IN ("
                "'before_game', 'at_arrival', 'after_confirmation', 'custom'"
                ")"
            ),
            name="ck_host_profiles_default_payment_due_timing",
        ),
        sa.CheckConstraint(
            "(phone_verified_at IS NULL OR phone_number_e164 IS NOT NULL)",
            name="ck_host_profiles_phone_verified_requires_phone",
        ),
        sa.CheckConstraint(
            "(host_rules_accepted_at IS NULL OR host_rules_version IS NOT NULL)",
            name="ck_host_profiles_rules_acceptance_requires_version",
        ),
        sa.CheckConstraint(
            (
                "host_setup_completed_at IS NULL OR ("
                "phone_verified_at IS NOT NULL "
                "AND host_rules_accepted_at IS NOT NULL "
                "AND host_age_confirmed_at IS NOT NULL)"
            ),
            name="ck_host_profiles_setup_completion_requirements",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_host_profiles_user_id"),
        sa.UniqueConstraint("phone_number_e164", name="uq_host_profiles_phone_number_e164"),
    )
    op.create_index("ix_host_profiles_user_id", "host_profiles", ["user_id"])
    op.create_index(
        "ix_host_profiles_host_setup_completed_at",
        "host_profiles",
        ["host_setup_completed_at"],
    )

    op.create_table(
        "community_game_details",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "payment_methods_snapshot",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("payment_instructions_snapshot", sa.Text(), nullable=True),
        sa.Column("payment_due_timing_snapshot", sa.String(length=30), nullable=True),
        sa.Column("price_note_snapshot", sa.Text(), nullable=True),
        sa.Column("refund_policy_snapshot", sa.Text(), nullable=True),
        sa.Column("cancellation_policy_snapshot", sa.Text(), nullable=True),
        sa.Column("no_show_policy_snapshot", sa.Text(), nullable=True),
        sa.Column("arrival_expectations_snapshot", sa.Text(), nullable=True),
        sa.Column("equipment_notes_snapshot", sa.Text(), nullable=True),
        sa.Column("behavior_rules_snapshot", sa.Text(), nullable=True),
        sa.Column("player_message_snapshot", sa.Text(), nullable=True),
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
            "jsonb_typeof(payment_methods_snapshot) = 'array'",
            name="ck_community_game_details_payment_methods_array",
        ),
        sa.CheckConstraint(
            (
                "payment_due_timing_snapshot IS NULL OR "
                "payment_due_timing_snapshot IN ("
                "'before_game', 'at_arrival', 'after_confirmation', 'custom'"
                ")"
            ),
            name="ck_community_game_details_payment_due_timing",
        ),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["games.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("game_id", name="uq_community_game_details_game_id"),
    )
    op.create_index(
        "ix_community_game_details_game_id",
        "community_game_details",
        ["game_id"],
    )

    op.create_table(
        "host_publish_fees",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("host_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column(
            "currency",
            sa.CHAR(length=3),
            nullable=False,
            server_default=sa.text("'USD'"),
        ),
        sa.Column(
            "fee_status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "waiver_reason",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'none'"),
        ),
        sa.Column(
            "required_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
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
            "amount_cents >= 0",
            name="ck_host_publish_fees_amount_cents",
        ),
        sa.CheckConstraint(
            "currency = 'USD'",
            name="ck_host_publish_fees_currency",
        ),
        sa.CheckConstraint(
            "fee_status IN ('pending', 'paid', 'waived', 'failed', 'refunded')",
            name="ck_host_publish_fees_fee_status",
        ),
        sa.CheckConstraint(
            "waiver_reason IN ('none', 'first_game_free', 'admin_comp')",
            name="ck_host_publish_fees_waiver_reason",
        ),
        sa.CheckConstraint(
            (
                "fee_status <> 'paid' OR ("
                "payment_id IS NOT NULL AND paid_at IS NOT NULL "
                "AND amount_cents > 0)"
            ),
            name="ck_host_publish_fees_paid_requires_payment",
        ),
        sa.CheckConstraint(
            (
                "fee_status <> 'waived' OR ("
                "amount_cents = 0 AND waiver_reason <> 'none' "
                "AND payment_id IS NULL)"
            ),
            name="ck_host_publish_fees_waived_requirements",
        ),
        sa.CheckConstraint(
            "(fee_status <> 'failed' OR failed_at IS NOT NULL)",
            name="ck_host_publish_fees_failed_requires_failed_at",
        ),
        sa.CheckConstraint(
            (
                "fee_status <> 'refunded' OR ("
                "payment_id IS NOT NULL AND refunded_at IS NOT NULL)"
            ),
            name="ck_host_publish_fees_refunded_requires_payment",
        ),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["games.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["host_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["payment_id"],
            ["payments.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("game_id", name="uq_host_publish_fees_game_id"),
        sa.UniqueConstraint("payment_id", name="uq_host_publish_fees_payment_id"),
    )
    op.create_index("ix_host_publish_fees_game_id", "host_publish_fees", ["game_id"])
    op.create_index(
        "ix_host_publish_fees_host_user_id",
        "host_publish_fees",
        ["host_user_id"],
    )
    op.create_index(
        "ix_host_publish_fees_fee_status",
        "host_publish_fees",
        ["fee_status"],
    )
    op.create_index(
        "ix_host_publish_fees_payment_id",
        "host_publish_fees",
        ["payment_id"],
    )
    op.create_index(
        "ux_host_publish_fees_one_first_free_per_host",
        "host_publish_fees",
        ["host_user_id"],
        unique=True,
        postgresql_where=sa.text("waiver_reason = 'first_game_free'"),
    )


def downgrade() -> None:
    op.drop_index(
        "ux_host_publish_fees_one_first_free_per_host",
        table_name="host_publish_fees",
        postgresql_where=sa.text("waiver_reason = 'first_game_free'"),
    )
    op.drop_index("ix_host_publish_fees_payment_id", table_name="host_publish_fees")
    op.drop_index("ix_host_publish_fees_fee_status", table_name="host_publish_fees")
    op.drop_index("ix_host_publish_fees_host_user_id", table_name="host_publish_fees")
    op.drop_index("ix_host_publish_fees_game_id", table_name="host_publish_fees")
    op.drop_table("host_publish_fees")

    op.drop_index(
        "ix_community_game_details_game_id",
        table_name="community_game_details",
    )
    op.drop_table("community_game_details")

    op.drop_index(
        "ix_host_profiles_host_setup_completed_at",
        table_name="host_profiles",
    )
    op.drop_index("ix_host_profiles_user_id", table_name="host_profiles")
    op.drop_table("host_profiles")
