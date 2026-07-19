"""create host publish fees table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0033_host_publish_fees"
down_revision = "0032_community_game_details"
branch_labels = None
depends_on = None


def _in_check(column_name: str, values: tuple[str, ...]) -> str:
    quoted_values = ", ".join(f"'{value}'" for value in values)
    return f"{column_name} IN ({quoted_values})"


def _target_required_check(columns: tuple[str, ...]) -> str:
    return " OR ".join(f"{column} IS NOT NULL" for column in columns)


PREVIOUS_ADMIN_ACTION_TYPES = (
    "cancel_game",
    "refund_booking",
    "create_refund",
    "update_refund",
    "mark_no_show",
    "create_payment",
    "update_payment",
    "reverse_no_show",
    "suspend_user",
    "unsuspend_user",
    "restrict_hosting",
    "restore_hosting",
    "approve_venue",
    "delete_user",
    "reject_venue",
    "mark_chat_message_reviewed",
    "remove_chat_message",
    "restore_chat_message",
    "update_game",
    "create_game_chat",
    "update_game_chat",
    "update_booking",
    "update_participant",
    "create_official_game",
    "update_official_game",
    "assign_official_host",
    "remove_official_host",
    "admin_add_player",
    "admin_remove_player",
    "waive_payment",
    "create_notification",
    "update_notification",
    "change_staff_role",
    "append_audit_note",
    "remove_sub_post",
    "hide_unsafe_community_payment_text",
    "restore_community_payment_text",
    "hide_community_game",
    "restore_community_game",
    "pause_community_game_joining",
    "resume_community_game_joining",
    "admin_cancel_community_game",
    "hide_need_sub_post",
    "restore_need_sub_post",
)
ADMIN_ACTION_TYPES = (
    *PREVIOUS_ADMIN_ACTION_TYPES,
    "create_financial_outcome",
    "apply_financial_outcome",
)
PREVIOUS_ADMIN_ACTION_TYPE_CHECK = _in_check(
    "action_type",
    PREVIOUS_ADMIN_ACTION_TYPES,
)
ADMIN_ACTION_TYPE_CHECK = _in_check("action_type", ADMIN_ACTION_TYPES)

PREVIOUS_ADMIN_ACTION_TARGET_COLUMNS = (
    "target_user_id",
    "target_game_id",
    "target_booking_id",
    "target_participant_id",
    "target_payment_id",
    "target_refund_id",
    "target_venue_id",
    "target_message_id",
    "target_notification_id",
    "target_admin_action_id",
    "target_sub_post_id",
    "target_sub_post_position_id",
    "target_sub_post_request_id",
)
ADMIN_ACTION_TARGET_COLUMNS = (
    *PREVIOUS_ADMIN_ACTION_TARGET_COLUMNS,
    "target_financial_outcome_id",
    "target_host_publish_fee_id",
    "target_host_publish_entitlement_id",
)
PREVIOUS_ADMIN_ACTION_TARGET_REQUIRED_CHECK = _target_required_check(
    PREVIOUS_ADMIN_ACTION_TARGET_COLUMNS
)
ADMIN_ACTION_TARGET_REQUIRED_CHECK = _target_required_check(
    ADMIN_ACTION_TARGET_COLUMNS
)


def upgrade() -> None:
    op.create_table(
        "community_publish_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("host_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_game_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("attempt_status", sa.String(length=30), nullable=False),
        sa.Column("publish_payload", postgresql.JSONB(), nullable=False),
        sa.Column("payment_method_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("starts_on_local", sa.Date(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column(
            "currency",
            sa.CHAR(length=3),
            nullable=False,
            server_default=sa.text("'USD'"),
        ),
        sa.Column("failure_code", sa.String(length=100), nullable=True),
        sa.Column("failure_message", sa.Text(), nullable=True),
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
                "attempt_status IN ("
                "'requires_payment_method', 'requires_action', 'processing', "
                "'succeeded', 'failed', 'cancelled', 'expired'"
                ")"
            ),
            name="ck_community_publish_attempts_status",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(publish_payload) = 'object'",
            name="ck_community_publish_attempts_payload_object",
        ),
        sa.CheckConstraint(
            "amount_cents >= 0",
            name="ck_community_publish_attempts_amount_cents",
        ),
        sa.CheckConstraint(
            "currency = 'USD'",
            name="ck_community_publish_attempts_currency",
        ),
        sa.CheckConstraint(
            "(attempt_status <> 'succeeded' OR created_game_id IS NOT NULL)",
            name="ck_community_publish_attempts_succeeded_requires_game",
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
        sa.ForeignKeyConstraint(
            ["created_game_id"],
            ["games.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["payment_method_id"],
            ["user_payment_methods.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "payment_id",
            name="uq_community_publish_attempts_payment_id",
        ),
        sa.UniqueConstraint(
            "created_game_id",
            name="uq_community_publish_attempts_created_game_id",
        ),
    )
    op.create_index(
        "ix_community_publish_attempts_host_user_id",
        "community_publish_attempts",
        ["host_user_id"],
    )
    op.create_index(
        "ix_community_publish_attempts_payment_id",
        "community_publish_attempts",
        ["payment_id"],
    )
    op.create_index(
        "ix_community_publish_attempts_created_game_id",
        "community_publish_attempts",
        ["created_game_id"],
    )
    op.create_index(
        "ix_community_publish_attempts_attempt_status",
        "community_publish_attempts",
        ["attempt_status"],
    )
    op.create_index(
        "ix_community_publish_attempts_host_date",
        "community_publish_attempts",
        ["host_user_id", "starts_on_local"],
    )
    op.create_index(
        "ux_community_publish_attempts_one_active_paid_per_host_date",
        "community_publish_attempts",
        ["host_user_id", "starts_on_local"],
        unique=True,
        postgresql_where=sa.text(
            "attempt_status IN ("
            "'requires_payment_method', 'requires_action', 'processing'"
            ")"
        ),
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
        ),
        sa.Column(
            "waiver_reason",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'none'"),
        ),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
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

    op.add_column(
        "refunds",
        sa.Column("host_publish_fee_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_refunds_host_publish_fee_id",
        "refunds",
        "host_publish_fees",
        ["host_publish_fee_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_refunds_host_publish_fee_id",
        "refunds",
        ["host_publish_fee_id"],
    )
    op.drop_constraint(
        "ck_refunds_refund_reason",
        "refunds",
        type_="check",
    )
    op.create_check_constraint(
        "ck_refunds_refund_reason",
        "refunds",
        (
            "refund_reason IN ("
            "'player_cancelled', 'late_cancel', 'host_cancelled', "
            "'game_cancelled', 'weather', 'admin_refund', "
            "'duplicate_payment', 'dispute_resolution', "
            "'publish_fee_refund'"
            ")"
        ),
    )
    op.drop_constraint(
        "ck_refunds_booking_or_participant_required",
        "refunds",
        type_="check",
    )
    op.create_check_constraint(
        "ck_refunds_target_required",
        "refunds",
        (
            "booking_id IS NOT NULL "
            "OR participant_id IS NOT NULL "
            "OR host_publish_fee_id IS NOT NULL"
        ),
    )

    op.create_table(
        "host_publish_entitlements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("host_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entitlement_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column(
            "source_admin_action_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "source_financial_outcome_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "reserved_by_attempt_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("used_by_game_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "used_by_host_publish_fee_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("revoke_reason", sa.Text(), nullable=True),
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
                "entitlement_type IN ("
                "'first_free', 'admin_grant', 'refund_replacement', 'courtesy'"
                ")"
            ),
            name="ck_host_publish_entitlements_type",
        ),
        sa.CheckConstraint(
            "status IN ('available', 'reserved', 'used', 'revoked', 'expired')",
            name="ck_host_publish_entitlements_status",
        ),
        sa.CheckConstraint(
            "source IN ('system', 'admin', 'financial_outcome')",
            name="ck_host_publish_entitlements_source",
        ),
        sa.CheckConstraint(
            (
                "status <> 'reserved' OR "
                "(reserved_by_attempt_id IS NOT NULL AND used_at IS NULL)"
            ),
            name="ck_host_publish_entitlements_reserved_requirements",
        ),
        sa.CheckConstraint(
            (
                "status <> 'used' OR ("
                "used_by_game_id IS NOT NULL "
                "AND used_by_host_publish_fee_id IS NOT NULL "
                "AND used_at IS NOT NULL)"
            ),
            name="ck_host_publish_entitlements_used_requirements",
        ),
        sa.CheckConstraint(
            (
                "status <> 'revoked' OR ("
                "revoked_at IS NOT NULL "
                "AND NULLIF(BTRIM(revoke_reason), '') IS NOT NULL)"
            ),
            name="ck_host_publish_entitlements_revoked_requirements",
        ),
        sa.ForeignKeyConstraint(
            ["host_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_admin_action_id"],
            ["admin_actions.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["reserved_by_attempt_id"],
            ["community_publish_attempts.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["used_by_game_id"],
            ["games.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["used_by_host_publish_fee_id"],
            ["host_publish_fees.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["revoked_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_host_publish_entitlements_host_user_id",
        "host_publish_entitlements",
        ["host_user_id"],
    )
    op.create_index(
        "ix_host_publish_entitlements_status",
        "host_publish_entitlements",
        ["status"],
    )
    op.create_index(
        "ix_host_publish_entitlements_host_status",
        "host_publish_entitlements",
        ["host_user_id", "status"],
    )
    op.create_index(
        "ix_host_publish_entitlements_reserved_by_attempt_id",
        "host_publish_entitlements",
        ["reserved_by_attempt_id"],
    )
    op.create_index(
        "ix_host_publish_entitlements_used_by_game_id",
        "host_publish_entitlements",
        ["used_by_game_id"],
    )
    op.create_index(
        "ix_host_publish_entitlements_used_by_fee_id",
        "host_publish_entitlements",
        ["used_by_host_publish_fee_id"],
    )
    op.create_index(
        "ux_host_publish_entitlements_one_first_free_per_host",
        "host_publish_entitlements",
        ["host_user_id"],
        unique=True,
        postgresql_where=sa.text("entitlement_type = 'first_free'"),
    )
    op.create_table(
        "admin_financial_outcomes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_game_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_sub_post_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("host_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "host_publish_fee_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("refund_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "host_publish_entitlement_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("admin_action_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("review_case_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("outcome", sa.String(length=40), nullable=False),
        sa.Column("applied_status", sa.String(length=30), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column(
            "currency",
            sa.CHAR(length=3),
            nullable=False,
            server_default=sa.text("'USD'"),
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("internal_note", sa.Text(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("applied_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
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
                "outcome IN ('no_fee_charged', 'refund', 'credit', "
                "'forfeit', 'manual_review')"
            ),
            name="ck_admin_financial_outcomes_outcome",
        ),
        sa.CheckConstraint(
            "applied_status IN ('pending', 'applied', 'failed', 'not_applicable')",
            name="ck_admin_financial_outcomes_applied_status",
        ),
        sa.CheckConstraint(
            "amount_cents >= 0",
            name="ck_admin_financial_outcomes_amount_cents",
        ),
        sa.CheckConstraint(
            "currency = 'USD'",
            name="ck_admin_financial_outcomes_currency",
        ),
        sa.CheckConstraint(
            (
                "host_user_id IS NOT NULL AND ("
                "target_game_id IS NOT NULL "
                "OR target_sub_post_id IS NOT NULL "
                "OR host_publish_fee_id IS NOT NULL "
                "OR payment_id IS NOT NULL)"
            ),
            name="ck_admin_financial_outcomes_target_required",
        ),
        sa.CheckConstraint(
            (
                "applied_status NOT IN ('applied', 'failed') "
                "OR applied_at IS NOT NULL"
            ),
            name="ck_admin_financial_outcomes_terminal_requires_applied_at",
        ),
        sa.ForeignKeyConstraint(
            ["target_game_id"],
            ["games.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_sub_post_id"],
            ["sub_posts.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["host_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["host_publish_fee_id"],
            ["host_publish_fees.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["payment_id"],
            ["payments.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["refund_id"],
            ["refunds.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["host_publish_entitlement_id"],
            ["host_publish_entitlements.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["admin_action_id"],
            ["admin_actions.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["applied_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_admin_financial_outcomes_target_game_id",
        "admin_financial_outcomes",
        ["target_game_id"],
    )
    op.create_index(
        "ix_admin_financial_outcomes_target_sub_post_id",
        "admin_financial_outcomes",
        ["target_sub_post_id"],
    )
    op.create_index(
        "ix_admin_financial_outcomes_host_user_id",
        "admin_financial_outcomes",
        ["host_user_id"],
    )
    op.create_index(
        "ix_admin_financial_outcomes_host_publish_fee_id",
        "admin_financial_outcomes",
        ["host_publish_fee_id"],
    )
    op.create_index(
        "ix_admin_financial_outcomes_payment_id",
        "admin_financial_outcomes",
        ["payment_id"],
    )
    op.create_index(
        "ix_admin_financial_outcomes_refund_id",
        "admin_financial_outcomes",
        ["refund_id"],
    )
    op.create_index(
        "ix_admin_financial_outcomes_entitlement_id",
        "admin_financial_outcomes",
        ["host_publish_entitlement_id"],
    )
    op.create_index(
        "ix_admin_financial_outcomes_admin_action_id",
        "admin_financial_outcomes",
        ["admin_action_id"],
    )
    op.create_index(
        "ix_admin_financial_outcomes_outcome",
        "admin_financial_outcomes",
        ["outcome"],
    )
    op.create_index(
        "ix_admin_financial_outcomes_applied_status",
        "admin_financial_outcomes",
        ["applied_status"],
    )
    op.create_index(
        "ix_admin_financial_outcomes_created_by_user_id",
        "admin_financial_outcomes",
        ["created_by_user_id"],
    )
    op.create_index(
        "uq_admin_financial_outcomes_active_fee_decision",
        "admin_financial_outcomes",
        ["host_publish_fee_id"],
        unique=True,
        postgresql_where=sa.text(
            "host_publish_fee_id IS NOT NULL "
            "AND applied_status IN ('pending', 'applied', 'not_applicable')"
        ),
    )
    op.create_index(
        "uq_admin_financial_outcomes_active_game_no_fee_decision",
        "admin_financial_outcomes",
        ["host_user_id", "target_game_id"],
        unique=True,
        postgresql_where=sa.text(
            "target_game_id IS NOT NULL "
            "AND host_publish_fee_id IS NULL "
            "AND applied_status IN ('pending', 'applied', 'not_applicable')"
        ),
    )

    op.add_column(
        "admin_actions",
        sa.Column(
            "target_financial_outcome_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "admin_actions",
        sa.Column(
            "target_host_publish_fee_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "admin_actions",
        sa.Column(
            "target_host_publish_entitlement_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_admin_actions_target_financial_outcome_id",
        "admin_actions",
        ["target_financial_outcome_id"],
    )
    op.create_index(
        "ix_admin_actions_target_host_publish_fee_id",
        "admin_actions",
        ["target_host_publish_fee_id"],
    )
    op.create_index(
        "ix_admin_actions_target_host_publish_entitlement_id",
        "admin_actions",
        ["target_host_publish_entitlement_id"],
    )
    op.create_index(
        "uq_admin_actions_create_financial_outcome_idempotency",
        "admin_actions",
        ["admin_user_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "action_type = 'create_financial_outcome' "
            "AND idempotency_key IS NOT NULL"
        ),
    )
    op.create_foreign_key(
        "fk_admin_actions_target_financial_outcome_id",
        "admin_actions",
        "admin_financial_outcomes",
        ["target_financial_outcome_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_admin_actions_target_host_publish_fee_id",
        "admin_actions",
        "host_publish_fees",
        ["target_host_publish_fee_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_admin_actions_target_host_publish_entitlement_id",
        "admin_actions",
        "host_publish_entitlements",
        ["target_host_publish_entitlement_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_constraint(
        "ck_admin_actions_target_required",
        "admin_actions",
        type_="check",
    )
    op.create_check_constraint(
        "ck_admin_actions_target_required",
        "admin_actions",
        ADMIN_ACTION_TARGET_REQUIRED_CHECK,
    )
    op.drop_constraint(
        "ck_admin_actions_action_type",
        "admin_actions",
        type_="check",
    )
    op.create_check_constraint(
        "ck_admin_actions_action_type",
        "admin_actions",
        ADMIN_ACTION_TYPE_CHECK,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_admin_actions_create_financial_outcome_idempotency",
        table_name="admin_actions",
    )
    op.execute(
        "DELETE FROM admin_actions "
        "WHERE action_type IN ("
        "'create_financial_outcome', 'apply_financial_outcome'"
        ") "
        "OR target_financial_outcome_id IS NOT NULL "
        "OR target_host_publish_fee_id IS NOT NULL "
        "OR target_host_publish_entitlement_id IS NOT NULL"
    )
    op.drop_constraint(
        "ck_admin_actions_action_type",
        "admin_actions",
        type_="check",
    )
    op.create_check_constraint(
        "ck_admin_actions_action_type",
        "admin_actions",
        PREVIOUS_ADMIN_ACTION_TYPE_CHECK,
    )
    op.drop_constraint(
        "ck_admin_actions_target_required",
        "admin_actions",
        type_="check",
    )
    op.create_check_constraint(
        "ck_admin_actions_target_required",
        "admin_actions",
        PREVIOUS_ADMIN_ACTION_TARGET_REQUIRED_CHECK,
    )
    op.drop_constraint(
        "fk_admin_actions_target_host_publish_entitlement_id",
        "admin_actions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_admin_actions_target_host_publish_fee_id",
        "admin_actions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_admin_actions_target_financial_outcome_id",
        "admin_actions",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_admin_actions_target_host_publish_entitlement_id",
        table_name="admin_actions",
    )
    op.drop_index(
        "ix_admin_actions_target_host_publish_fee_id",
        table_name="admin_actions",
    )
    op.drop_index(
        "ix_admin_actions_target_financial_outcome_id",
        table_name="admin_actions",
    )
    op.drop_column("admin_actions", "target_host_publish_entitlement_id")
    op.drop_column("admin_actions", "target_host_publish_fee_id")
    op.drop_column("admin_actions", "target_financial_outcome_id")

    op.drop_index(
        "ix_admin_financial_outcomes_created_by_user_id",
        table_name="admin_financial_outcomes",
    )
    op.drop_index(
        "uq_admin_financial_outcomes_active_game_no_fee_decision",
        table_name="admin_financial_outcomes",
    )
    op.drop_index(
        "uq_admin_financial_outcomes_active_fee_decision",
        table_name="admin_financial_outcomes",
    )
    op.drop_index(
        "ix_admin_financial_outcomes_applied_status",
        table_name="admin_financial_outcomes",
    )
    op.drop_index(
        "ix_admin_financial_outcomes_outcome",
        table_name="admin_financial_outcomes",
    )
    op.drop_index(
        "ix_admin_financial_outcomes_admin_action_id",
        table_name="admin_financial_outcomes",
    )
    op.drop_index(
        "ix_admin_financial_outcomes_entitlement_id",
        table_name="admin_financial_outcomes",
    )
    op.drop_index(
        "ix_admin_financial_outcomes_refund_id",
        table_name="admin_financial_outcomes",
    )
    op.drop_index(
        "ix_admin_financial_outcomes_payment_id",
        table_name="admin_financial_outcomes",
    )
    op.drop_index(
        "ix_admin_financial_outcomes_host_publish_fee_id",
        table_name="admin_financial_outcomes",
    )
    op.drop_index(
        "ix_admin_financial_outcomes_host_user_id",
        table_name="admin_financial_outcomes",
    )
    op.drop_index(
        "ix_admin_financial_outcomes_target_sub_post_id",
        table_name="admin_financial_outcomes",
    )
    op.drop_index(
        "ix_admin_financial_outcomes_target_game_id",
        table_name="admin_financial_outcomes",
    )
    op.drop_table("admin_financial_outcomes")

    op.drop_index(
        "ux_host_publish_entitlements_one_first_free_per_host",
        table_name="host_publish_entitlements",
        postgresql_where=sa.text("entitlement_type = 'first_free'"),
    )
    op.drop_index(
        "ix_host_publish_entitlements_used_by_fee_id",
        table_name="host_publish_entitlements",
    )
    op.drop_index(
        "ix_host_publish_entitlements_used_by_game_id",
        table_name="host_publish_entitlements",
    )
    op.drop_index(
        "ix_host_publish_entitlements_reserved_by_attempt_id",
        table_name="host_publish_entitlements",
    )
    op.drop_index(
        "ix_host_publish_entitlements_host_status",
        table_name="host_publish_entitlements",
    )
    op.drop_index(
        "ix_host_publish_entitlements_status",
        table_name="host_publish_entitlements",
    )
    op.drop_index(
        "ix_host_publish_entitlements_host_user_id",
        table_name="host_publish_entitlements",
    )
    op.drop_table("host_publish_entitlements")
    op.drop_index(
        "ix_host_publish_fees_payment_id", table_name="host_publish_fees"
    )
    op.execute(
        "DELETE FROM refunds "
        "WHERE host_publish_fee_id IS NOT NULL "
        "OR refund_reason = 'publish_fee_refund'"
    )
    op.drop_constraint(
        "ck_refunds_target_required",
        "refunds",
        type_="check",
    )
    op.create_check_constraint(
        "ck_refunds_booking_or_participant_required",
        "refunds",
        "(booking_id IS NOT NULL OR participant_id IS NOT NULL)",
    )
    op.drop_constraint(
        "ck_refunds_refund_reason",
        "refunds",
        type_="check",
    )
    op.create_check_constraint(
        "ck_refunds_refund_reason",
        "refunds",
        (
            "refund_reason IN ("
            "'player_cancelled', 'late_cancel', 'host_cancelled', "
            "'game_cancelled', 'weather', 'admin_refund', "
            "'duplicate_payment', 'dispute_resolution'"
            ")"
        ),
    )
    op.drop_constraint(
        "fk_refunds_host_publish_fee_id",
        "refunds",
        type_="foreignkey",
    )
    op.drop_index("ix_refunds_host_publish_fee_id", table_name="refunds")
    op.drop_column("refunds", "host_publish_fee_id")
    op.drop_index("ix_host_publish_fees_fee_status", table_name="host_publish_fees")
    op.drop_index("ix_host_publish_fees_host_user_id", table_name="host_publish_fees")
    op.drop_index("ix_host_publish_fees_game_id", table_name="host_publish_fees")
    op.drop_table("host_publish_fees")
    op.drop_index(
        "ux_community_publish_attempts_one_active_paid_per_host_date",
        table_name="community_publish_attempts",
        postgresql_where=sa.text(
            "attempt_status IN ("
            "'requires_payment_method', 'requires_action', 'processing'"
            ")"
        ),
    )
    op.drop_index(
        "ix_community_publish_attempts_host_date",
        table_name="community_publish_attempts",
    )
    op.drop_index(
        "ix_community_publish_attempts_attempt_status",
        table_name="community_publish_attempts",
    )
    op.drop_index(
        "ix_community_publish_attempts_created_game_id",
        table_name="community_publish_attempts",
    )
    op.drop_index(
        "ix_community_publish_attempts_payment_id",
        table_name="community_publish_attempts",
    )
    op.drop_index(
        "ix_community_publish_attempts_host_user_id",
        table_name="community_publish_attempts",
    )
    op.drop_table("community_publish_attempts")
