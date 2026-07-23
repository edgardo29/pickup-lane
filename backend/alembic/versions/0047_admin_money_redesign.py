"""admin money redesign"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0047_admin_money_redesign"
down_revision = "0046_admin_review_workflow"
branch_labels = None
depends_on = None


PREVIOUS_ADMIN_ACTION_TYPE_CHECK = (
    "action_type IN ("
    "'cancel_game', 'refund_booking', 'create_refund', "
    "'update_refund', 'mark_no_show', "
    "'create_payment', 'update_payment', "
    "'reverse_no_show', 'suspend_user', 'unsuspend_user', "
    "'restrict_hosting', 'restore_hosting', 'approve_venue', "
    "'delete_user', "
    "'reject_venue', 'create_venue_image', 'update_venue_image', "
    "'remove_venue_image', 'mark_chat_message_reviewed', "
    "'remove_chat_message', 'restore_chat_message', "
    "'update_game', 'create_game_chat', 'update_game_chat', "
    "'update_booking', "
    "'update_participant', 'issue_credit', 'reverse_credit', "
    "'create_financial_outcome', 'apply_financial_outcome', "
    "'create_official_game', 'update_official_game', "
    "'assign_official_host', 'remove_official_host', "
    "'admin_add_player', 'admin_remove_player', 'waive_payment', "
    "'remove_sub_post', 'hide_unsafe_community_payment_text', "
    "'hide_need_sub_post', 'restore_need_sub_post', "
    "'hide_community_game', 'restore_community_game', "
    "'pause_community_game_joining', "
    "'resume_community_game_joining', "
    "'admin_cancel_community_game', "
    "'restore_community_payment_text', "
    "'create_notification', 'update_notification', "
    "'create_platform_notice_campaign', "
    "'update_platform_notice_campaign', "
    "'send_platform_notice_campaign', "
    "'retry_platform_notice_campaign', "
    "'user_role_changed', 'append_audit_note', "
    "'resolve_support_flag', "
    "'create_review_case', 'close_review_case', "
    "'add_review_case_note'"
    ")"
)

ADMIN_ACTION_TYPE_CHECK = (
    "action_type IN ("
    "'cancel_game', 'refund_booking', 'create_refund', "
    "'update_refund', 'mark_no_show', "
    "'create_payment', 'update_payment', "
    "'reverse_no_show', 'suspend_user', 'unsuspend_user', "
    "'restrict_hosting', 'restore_hosting', 'approve_venue', "
    "'delete_user', "
    "'reject_venue', 'create_venue_image', 'update_venue_image', "
    "'remove_venue_image', 'mark_chat_message_reviewed', "
    "'remove_chat_message', 'restore_chat_message', "
    "'update_game', 'create_game_chat', 'update_game_chat', "
    "'update_booking', "
    "'update_participant', 'issue_credit', 'reverse_credit', "
    "'create_financial_outcome', 'apply_financial_outcome', "
    "'create_official_game', 'update_official_game', "
    "'assign_official_host', 'remove_official_host', "
    "'admin_add_player', 'admin_remove_player', 'waive_payment', "
    "'remove_sub_post', 'hide_unsafe_community_payment_text', "
    "'hide_need_sub_post', 'restore_need_sub_post', "
    "'hide_community_game', 'restore_community_game', "
    "'pause_community_game_joining', "
    "'resume_community_game_joining', "
    "'admin_cancel_community_game', "
    "'restore_community_payment_text', "
    "'create_notification', 'update_notification', "
    "'create_platform_notice_campaign', "
    "'update_platform_notice_campaign', "
    "'send_platform_notice_campaign', "
    "'retry_platform_notice_campaign', "
    "'user_role_changed', 'append_audit_note', "
    "'resolve_support_flag', "
    "'create_review_case', 'close_review_case', "
    "'add_review_case_note', "
    "'resolve_money_issue', 'retry_money_issue_credit', "
    "'reconcile_refund'"
    ")"
)

PREVIOUS_ADMIN_ACTION_TARGET_REQUIRED_CHECK = (
    "target_user_id IS NOT NULL "
    "OR target_game_id IS NOT NULL "
    "OR target_booking_id IS NOT NULL "
    "OR target_participant_id IS NOT NULL "
    "OR target_payment_id IS NOT NULL "
    "OR target_refund_id IS NOT NULL "
    "OR target_game_credit_id IS NOT NULL "
    "OR target_financial_outcome_id IS NOT NULL "
    "OR target_host_publish_fee_id IS NOT NULL "
    "OR target_host_publish_entitlement_id IS NOT NULL "
    "OR target_venue_id IS NOT NULL "
    "OR target_venue_image_id IS NOT NULL "
    "OR target_message_id IS NOT NULL "
    "OR target_sub_post_id IS NOT NULL "
    "OR target_sub_post_request_id IS NOT NULL "
    "OR target_sub_post_position_id IS NOT NULL "
    "OR target_sub_chat_message_id IS NOT NULL "
    "OR target_notification_id IS NOT NULL "
    "OR target_platform_notice_campaign_id IS NOT NULL "
    "OR target_admin_action_id IS NOT NULL "
    "OR target_support_flag_id IS NOT NULL "
    "OR target_review_case_id IS NOT NULL"
)

ADMIN_ACTION_TARGET_REQUIRED_CHECK = (
    PREVIOUS_ADMIN_ACTION_TARGET_REQUIRED_CHECK
    + " OR target_money_issue_id IS NOT NULL"
    + " OR target_credit_usage_id IS NOT NULL"
)


def upgrade() -> None:
    op.add_column(
        "refunds",
        sa.Column(
            "origin_workflow",
            sa.String(length=80),
            nullable=False,
            server_default=sa.text("'direct_admin_refund'"),
        ),
    )
    op.add_column(
        "refunds",
        sa.Column(
            "provider",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'stripe'"),
        ),
    )
    op.add_column(
        "refunds",
        sa.Column("provider_status", sa.String(length=30), nullable=True),
    )
    op.add_column(
        "refunds",
        sa.Column("provider_status_observed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "refunds",
        sa.Column("provider_charge_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "refunds",
        sa.Column("last_refund_event_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.drop_constraint("uq_refunds_provider_refund_id", "refunds", type_="unique")
    op.create_index(
        "uq_refunds_provider_refund_id",
        "refunds",
        ["provider", "provider_refund_id"],
        unique=True,
        postgresql_where=sa.text("provider_refund_id IS NOT NULL"),
    )
    op.create_check_constraint(
        "ck_refunds_origin_workflow",
        "refunds",
        (
            "origin_workflow IN ("
            "'player_removal', 'official_game_cancellation', "
            "'community_publish_fee_refund', 'direct_admin_refund', "
            "'official_game_checkout', 'pending_checkout_expiration', "
            "'pending_checkout_cancellation', 'admin_game_update'"
            ")"
        ),
    )
    op.create_check_constraint(
        "ck_refunds_provider",
        "refunds",
        "provider IN ('stripe')",
    )
    op.create_check_constraint(
        "ck_refunds_provider_status",
        "refunds",
        (
            "provider_status IS NULL OR provider_status IN ("
            "'processing', 'succeeded', 'failed', 'cancelled', 'unknown'"
            ")"
        ),
    )
    op.create_index(
        "ix_refunds_refund_status_created",
        "refunds",
        ["refund_status", "created_at", "id"],
    )
    op.create_index(
        "ix_refunds_origin_workflow_created",
        "refunds",
        ["origin_workflow", "created_at", "id"],
    )
    op.create_index(
        "ix_refunds_provider_status_created",
        "refunds",
        ["provider_status", "created_at", "id"],
    )
    op.create_index(
        "ix_refunds_amount_cents_id",
        "refunds",
        ["amount_cents", "id"],
    )
    op.create_index(
        "ix_refunds_last_refund_event_at",
        "refunds",
        ["last_refund_event_at", "id"],
    )
    op.create_index(
        "ix_refunds_provider_refund_id",
        "refunds",
        ["provider_refund_id"],
    )
    op.create_index(
        "ix_refunds_provider_charge_id",
        "refunds",
        ["provider_charge_id"],
    )

    op.create_table(
        "refund_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("refund_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("event_source", sa.String(length=30), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("admin_action_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("provider", sa.String(length=20), nullable=True),
        sa.Column("provider_event_id", sa.String(length=255), nullable=True),
        sa.Column("provider_refund_id", sa.String(length=255), nullable=True),
        sa.Column("provider_charge_id", sa.String(length=255), nullable=True),
        sa.Column("provider_status", sa.String(length=30), nullable=True),
        sa.Column("previous_refund_status", sa.String(length=30), nullable=True),
        sa.Column("new_refund_status", sa.String(length=30), nullable=True),
        sa.Column("reason_code", sa.String(length=80), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            (
                "event_type IN ("
                "'provider_result_recorded', 'reconciliation_checked', "
                "'local_status_changed', 'provider_outcome_unknown'"
                ")"
            ),
            name="ck_refund_events_event_type",
        ),
        sa.CheckConstraint(
            "event_source IN ('system', 'webhook', 'reconciliation', 'admin')",
            name="ck_refund_events_event_source",
        ),
        sa.CheckConstraint(
            "(provider IS NULL OR provider IN ('stripe'))",
            name="ck_refund_events_provider",
        ),
        sa.CheckConstraint(
            (
                "provider_status IS NULL OR provider_status IN ("
                "'processing', 'succeeded', 'failed', 'cancelled', 'unknown'"
                ")"
            ),
            name="ck_refund_events_provider_status",
        ),
        sa.ForeignKeyConstraint(["refund_id"], ["refunds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["admin_action_id"], ["admin_actions.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_refund_events_refund_id", "refund_events", ["refund_id"])
    op.create_index(
        "ix_refund_events_refund_id_occurred_id",
        "refund_events",
        ["refund_id", "occurred_at", "id"],
    )
    op.create_index(
        "ix_refund_events_provider_refund_id",
        "refund_events",
        ["provider_refund_id"],
    )
    op.create_index(
        "ix_refund_events_provider_charge_id",
        "refund_events",
        ["provider_charge_id"],
    )
    op.create_index(
        "uq_refund_events_provider_event_id",
        "refund_events",
        ["provider", "provider_event_id"],
        unique=True,
        postgresql_where=sa.text("provider_event_id IS NOT NULL"),
    )
    op.create_index(
        "uq_refund_events_idempotency_key",
        "refund_events",
        ["idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )

    op.create_table(
        "money_issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_key", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("issue_type", sa.String(length=80), nullable=False),
        sa.Column("origin_workflow", sa.String(length=80), nullable=False),
        sa.Column("value_kind", sa.String(length=40), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column(
            "currency",
            sa.CHAR(length=3),
            nullable=False,
            server_default=sa.text("'USD'"),
        ),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_game_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_booking_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_payment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_refund_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_game_credit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_credit_usage_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("latest_reason_code", sa.String(length=80), nullable=True),
        sa.Column("latest_summary", sa.Text(), nullable=True),
        sa.Column("recommended_action_code", sa.String(length=80), nullable=False),
        sa.Column("occurrence_count", sa.Integer(), nullable=False),
        sa.Column("reopen_count", sa.Integer(), nullable=False),
        sa.Column("first_detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolution_reason_code", sa.String(length=80), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column(
            "resolution_external_reference", sa.String(length=255), nullable=True
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
        sa.CheckConstraint("status IN ('open', 'resolved')", name="ck_money_issues_status"),
        sa.CheckConstraint(
            (
                "issue_type IN ("
                "'refund_missing_provider_reference', "
                "'refund_processing_overdue', 'refund_failed', "
                "'refund_cancelled', 'refund_outcome_unknown', "
                "'credit_restore_failed', 'credit_release_failed'"
                ")"
            ),
            name="ck_money_issues_issue_type",
        ),
        sa.CheckConstraint(
            (
                "origin_workflow IN ("
                "'player_removal', 'official_game_cancellation', "
                "'community_publish_fee_refund', 'direct_admin_refund', "
                "'official_game_checkout', 'pending_checkout_expiration', "
                "'pending_checkout_cancellation', 'admin_game_update'"
                ")"
            ),
            name="ck_money_issues_origin_workflow",
        ),
        sa.CheckConstraint(
            (
                "value_kind IN ("
                "'cash_refund', 'game_credit_restore', 'game_credit_release'"
                ")"
            ),
            name="ck_money_issues_value_kind",
        ),
        sa.CheckConstraint("amount_cents >= 0", name="ck_money_issues_amount_cents"),
        sa.CheckConstraint("currency = 'USD'", name="ck_money_issues_currency"),
        sa.CheckConstraint(
            (
                "recommended_action_code IN ("
                "'recover_provider_reference', 'retry_refund', "
                "'verify_provider_refund', 'retry_credit_restore', "
                "'retry_credit_release', 'review_unknown_outcome', "
                "'review_and_resolve_no_action', 'document_external_completion'"
                ")"
            ),
            name="ck_money_issues_recommended_action_code",
        ),
        sa.CheckConstraint(
            (
                "resolution_reason_code IS NULL OR resolution_reason_code IN ("
                "'retried_successfully', 'provider_completed_no_action_required', "
                "'handled_externally', 'invalid_issue', "
                "'unable_to_complete_documented'"
                ")"
            ),
            name="ck_money_issues_resolution_reason_code",
        ),
        sa.CheckConstraint(
            "occurrence_count >= 1", name="ck_money_issues_occurrence_count"
        ),
        sa.CheckConstraint("reopen_count >= 0", name="ck_money_issues_reopen_count"),
        sa.CheckConstraint(
            (
                "((status = 'open') AND resolved_at IS NULL "
                "AND resolved_by_user_id IS NULL "
                "AND resolution_reason_code IS NULL "
                "AND resolution_note IS NULL "
                "AND resolution_external_reference IS NULL) "
                "OR ((status = 'resolved') AND resolved_at IS NOT NULL "
                "AND resolved_by_user_id IS NOT NULL "
                "AND resolution_reason_code IS NOT NULL)"
            ),
            name="ck_money_issues_resolution_fields_match_status",
        ),
        sa.CheckConstraint(
            "(issue_type NOT LIKE 'refund_%' OR target_refund_id IS NOT NULL)",
            name="ck_money_issues_refund_requires_refund",
        ),
        sa.CheckConstraint(
            "(issue_type NOT LIKE 'credit_%' OR target_credit_usage_id IS NOT NULL)",
            name="ck_money_issues_credit_requires_usage",
        ),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_game_id"], ["games.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["target_booking_id"], ["bookings.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["target_payment_id"], ["payments.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["target_refund_id"], ["refunds.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["target_game_credit_id"], ["game_credits.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["target_credit_usage_id"], ["game_credit_usage.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["resolved_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("operation_key", name="uq_money_issues_operation_key"),
    )
    op.create_index("ix_money_issues_open_queue", "money_issues", ["status", "first_detected_at", "id"])
    op.create_index("ix_money_issues_resolved", "money_issues", ["resolved_at", "id"])
    op.create_index("ix_money_issues_activity", "money_issues", ["last_activity_at", "id"])
    op.create_index("ix_money_issues_issue_type_status", "money_issues", ["issue_type", "status"])
    op.create_index("ix_money_issues_origin_workflow_status", "money_issues", ["origin_workflow", "status"])
    op.create_index("ix_money_issues_target_user_id", "money_issues", ["target_user_id"])
    op.create_index("ix_money_issues_target_game_id", "money_issues", ["target_game_id"])
    op.create_index("ix_money_issues_target_booking_id", "money_issues", ["target_booking_id"])
    op.create_index("ix_money_issues_target_payment_id", "money_issues", ["target_payment_id"])
    op.create_index("ix_money_issues_target_refund_id", "money_issues", ["target_refund_id"])
    op.create_index("ix_money_issues_target_game_credit_id", "money_issues", ["target_game_credit_id"])
    op.create_index("ix_money_issues_target_credit_usage_id", "money_issues", ["target_credit_usage_id"])

    op.add_column(
        "admin_actions",
        sa.Column("target_money_issue_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "admin_actions",
        sa.Column(
            "target_credit_usage_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_admin_actions_target_money_issue_id",
        "admin_actions",
        "money_issues",
        ["target_money_issue_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_admin_actions_target_credit_usage_id",
        "admin_actions",
        "game_credit_usage",
        ["target_credit_usage_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_admin_actions_target_money_issue_id",
        "admin_actions",
        ["target_money_issue_id"],
    )
    op.create_index(
        "ix_admin_actions_target_credit_usage_id",
        "admin_actions",
        ["target_credit_usage_id"],
    )
    op.drop_constraint("ck_admin_actions_action_type", "admin_actions", type_="check")
    op.create_check_constraint(
        "ck_admin_actions_action_type",
        "admin_actions",
        ADMIN_ACTION_TYPE_CHECK,
    )
    op.drop_constraint("ck_admin_actions_target_required", "admin_actions", type_="check")
    op.create_check_constraint(
        "ck_admin_actions_target_required",
        "admin_actions",
        ADMIN_ACTION_TARGET_REQUIRED_CHECK,
    )
    op.create_index(
        "uq_admin_actions_money_issue_idempotency",
        "admin_actions",
        ["admin_user_id", "target_money_issue_id", "action_type", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "idempotency_key IS NOT NULL "
            "AND action_type IN ("
            "'resolve_money_issue', 'retry_money_issue_credit'"
            ")"
        ),
    )
    op.create_index(
        "uq_admin_actions_reconcile_refund_idempotency",
        "admin_actions",
        ["admin_user_id", "target_refund_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "idempotency_key IS NOT NULL AND action_type = 'reconcile_refund'"
        ),
    )
    op.create_index(
        "uq_admin_actions_update_refund_idempotency",
        "admin_actions",
        ["admin_user_id", "target_refund_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "idempotency_key IS NOT NULL AND action_type = 'update_refund'"
        ),
    )

    op.create_table(
        "money_issue_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("money_issue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=60), nullable=False),
        sa.Column("event_source", sa.String(length=20), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("admin_action_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("refund_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("result_credit_usage_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("previous_status", sa.String(length=20), nullable=True),
        sa.Column("new_status", sa.String(length=20), nullable=True),
        sa.Column("previous_issue_type", sa.String(length=80), nullable=True),
        sa.Column("new_issue_type", sa.String(length=80), nullable=True),
        sa.Column(
            "previous_recommended_action_code", sa.String(length=80), nullable=True
        ),
        sa.Column("new_recommended_action_code", sa.String(length=80), nullable=True),
        sa.Column("reason_code", sa.String(length=80), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            (
                "event_type IN ("
                "'issue_opened', 'issue_reopened', 'classification_changed', "
                "'recommended_action_changed', 'admin_retry_initiated', "
                "'refund_outcome_linked', 'credit_restore_failed', "
                "'credit_restore_succeeded', 'credit_release_failed', "
                "'credit_release_succeeded', 'issue_resolved'"
                ")"
            ),
            name="ck_money_issue_events_event_type",
        ),
        sa.CheckConstraint(
            "event_source IN ('system', 'admin')",
            name="ck_money_issue_events_event_source",
        ),
        sa.ForeignKeyConstraint(
            ["money_issue_id"], ["money_issues.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["admin_action_id"], ["admin_actions.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["refund_event_id"], ["refund_events.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["result_credit_usage_id"], ["game_credit_usage.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_money_issue_events_money_issue_id", "money_issue_events", ["money_issue_id"])
    op.create_index(
        "ix_money_issue_events_issue_occurred_id",
        "money_issue_events",
        ["money_issue_id", "occurred_at", "id"],
    )
    op.create_index("ix_money_issue_events_refund_event_id", "money_issue_events", ["refund_event_id"])
    op.create_index(
        "ix_money_issue_events_result_credit_usage_id",
        "money_issue_events",
        ["result_credit_usage_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_money_issue_events_result_credit_usage_id",
        table_name="money_issue_events",
    )
    op.drop_index("ix_money_issue_events_refund_event_id", table_name="money_issue_events")
    op.drop_index(
        "ix_money_issue_events_issue_occurred_id", table_name="money_issue_events"
    )
    op.drop_index("ix_money_issue_events_money_issue_id", table_name="money_issue_events")
    op.drop_table("money_issue_events")

    op.drop_index("uq_admin_actions_update_refund_idempotency", table_name="admin_actions")
    op.drop_index("uq_admin_actions_reconcile_refund_idempotency", table_name="admin_actions")
    op.drop_index("uq_admin_actions_money_issue_idempotency", table_name="admin_actions")
    op.drop_constraint("ck_admin_actions_target_required", "admin_actions", type_="check")
    op.create_check_constraint(
        "ck_admin_actions_target_required",
        "admin_actions",
        PREVIOUS_ADMIN_ACTION_TARGET_REQUIRED_CHECK,
    )
    op.drop_constraint("ck_admin_actions_action_type", "admin_actions", type_="check")
    op.create_check_constraint(
        "ck_admin_actions_action_type",
        "admin_actions",
        PREVIOUS_ADMIN_ACTION_TYPE_CHECK,
    )
    op.drop_index("ix_admin_actions_target_money_issue_id", table_name="admin_actions")
    op.drop_index(
        "ix_admin_actions_target_credit_usage_id",
        table_name="admin_actions",
    )
    op.drop_constraint(
        "fk_admin_actions_target_money_issue_id",
        "admin_actions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_admin_actions_target_credit_usage_id",
        "admin_actions",
        type_="foreignkey",
    )
    op.drop_column("admin_actions", "target_money_issue_id")
    op.drop_column("admin_actions", "target_credit_usage_id")

    op.drop_index("ix_money_issues_target_credit_usage_id", table_name="money_issues")
    op.drop_index("ix_money_issues_target_game_credit_id", table_name="money_issues")
    op.drop_index("ix_money_issues_target_refund_id", table_name="money_issues")
    op.drop_index("ix_money_issues_target_payment_id", table_name="money_issues")
    op.drop_index("ix_money_issues_target_booking_id", table_name="money_issues")
    op.drop_index("ix_money_issues_target_game_id", table_name="money_issues")
    op.drop_index("ix_money_issues_target_user_id", table_name="money_issues")
    op.drop_index("ix_money_issues_origin_workflow_status", table_name="money_issues")
    op.drop_index("ix_money_issues_issue_type_status", table_name="money_issues")
    op.drop_index("ix_money_issues_activity", table_name="money_issues")
    op.drop_index("ix_money_issues_resolved", table_name="money_issues")
    op.drop_index("ix_money_issues_open_queue", table_name="money_issues")
    op.drop_table("money_issues")

    op.drop_index("uq_refund_events_idempotency_key", table_name="refund_events")
    op.drop_index("uq_refund_events_provider_event_id", table_name="refund_events")
    op.drop_index("ix_refund_events_provider_charge_id", table_name="refund_events")
    op.drop_index("ix_refund_events_provider_refund_id", table_name="refund_events")
    op.drop_index("ix_refund_events_refund_id_occurred_id", table_name="refund_events")
    op.drop_index("ix_refund_events_refund_id", table_name="refund_events")
    op.drop_table("refund_events")

    op.drop_index("ix_refunds_provider_charge_id", table_name="refunds")
    op.drop_index("ix_refunds_provider_refund_id", table_name="refunds")
    op.drop_index("ix_refunds_last_refund_event_at", table_name="refunds")
    op.drop_index("ix_refunds_amount_cents_id", table_name="refunds")
    op.drop_index("ix_refunds_provider_status_created", table_name="refunds")
    op.drop_index("ix_refunds_origin_workflow_created", table_name="refunds")
    op.drop_index("ix_refunds_refund_status_created", table_name="refunds")
    op.drop_constraint("ck_refunds_provider_status", "refunds", type_="check")
    op.drop_constraint("ck_refunds_provider", "refunds", type_="check")
    op.drop_constraint("ck_refunds_origin_workflow", "refunds", type_="check")
    op.drop_index("uq_refunds_provider_refund_id", table_name="refunds")
    op.create_unique_constraint(
        "uq_refunds_provider_refund_id",
        "refunds",
        ["provider_refund_id"],
    )
    op.drop_column("refunds", "last_refund_event_at")
    op.drop_column("refunds", "provider_charge_id")
    op.drop_column("refunds", "provider_status_observed_at")
    op.drop_column("refunds", "provider_status")
    op.drop_column("refunds", "provider")
    op.drop_column("refunds", "origin_workflow")
