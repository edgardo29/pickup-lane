"""create admin review workflow tables"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0046_admin_review_workflow"
down_revision = "0045_platform_notice_campaigns"
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
    "'resolve_support_flag'"
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
    "'add_review_case_note'"
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
    "OR target_support_flag_id IS NOT NULL"
)

ADMIN_ACTION_TARGET_REQUIRED_CHECK = (
    PREVIOUS_ADMIN_ACTION_TARGET_REQUIRED_CHECK
    + " OR target_review_case_id IS NOT NULL"
)

REVIEW_ACTION_TYPES = (
    "create_review_case",
    "close_review_case",
    "add_review_case_note",
)


def upgrade() -> None:
    op.create_table(
        "admin_review_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_type", sa.String(length=40), nullable=False),
        sa.Column(
            "case_status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'open'"),
        ),
        sa.Column("case_category", sa.String(length=60), nullable=False),
        sa.Column(
            "priority",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'attention'"),
        ),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_game_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_sub_post_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "target_sub_post_request_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("target_payment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "target_financial_outcome_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("opened_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("closed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("closure_outcome", sa.String(length=60), nullable=True),
        sa.Column("closure_reason", sa.Text(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
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
            "case_type IN ('community_game', 'need_a_sub', 'money', 'user', 'system')",
            name="ck_admin_review_cases_case_type",
        ),
        sa.CheckConstraint(
            "case_status IN ('open', 'closed')",
            name="ck_admin_review_cases_case_status",
        ),
        sa.CheckConstraint(
            "priority IN ('attention', 'urgent', 'critical')",
            name="ck_admin_review_cases_priority",
        ),
        sa.CheckConstraint(
            (
                "case_category IN ("
                "'content_moderation', 'chat_moderation')"
            ),
            name="ck_admin_review_cases_case_category",
        ),
        sa.CheckConstraint(
            (
                "closure_outcome IS NULL OR closure_outcome IN ("
                "'enforcement_applied', 'no_action_needed', 'invalid_signal')"
            ),
            name="ck_admin_review_cases_closure_outcome",
        ),
        sa.CheckConstraint(
            (
                "(case_status = 'open' "
                "AND closed_by_user_id IS NULL "
                "AND closure_outcome IS NULL "
                "AND closure_reason IS NULL "
                "AND closed_at IS NULL) "
                "OR (case_status = 'closed' "
                "AND closure_outcome IS NOT NULL "
                "AND closure_reason IS NOT NULL "
                "AND closed_at IS NOT NULL)"
            ),
            name="ck_admin_review_cases_closure_state",
        ),
        sa.CheckConstraint(
            (
                "case_status = 'closed' "
                "OR target_user_id IS NOT NULL "
                "OR target_game_id IS NOT NULL "
                "OR target_sub_post_id IS NOT NULL "
                "OR target_sub_post_request_id IS NOT NULL "
                "OR target_payment_id IS NOT NULL "
                "OR target_financial_outcome_id IS NOT NULL"
            ),
            name="ck_admin_review_cases_target_required",
        ),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_game_id"], ["games.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["target_sub_post_id"],
            ["sub_posts.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_sub_post_request_id"],
            ["sub_post_requests.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_payment_id"],
            ["payments.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_financial_outcome_id"],
            ["admin_financial_outcomes.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["opened_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["closed_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for index_name, columns in (
        ("ix_admin_review_cases_case_status", ["case_status"]),
        ("ix_admin_review_cases_case_type", ["case_type"]),
        ("ix_admin_review_cases_case_category", ["case_category"]),
        ("ix_admin_review_cases_priority", ["priority"]),
        ("ix_admin_review_cases_created_at", ["created_at"]),
        (
            "ix_admin_review_cases_status_updated_id",
            ["case_status", "updated_at", "id"],
        ),
        ("ix_admin_review_cases_closed_at", ["closed_at"]),
        ("ix_admin_review_cases_target_user_id", ["target_user_id"]),
        ("ix_admin_review_cases_target_game_id", ["target_game_id"]),
        ("ix_admin_review_cases_target_sub_post_id", ["target_sub_post_id"]),
        (
            "ix_admin_review_cases_target_sub_post_request_id",
            ["target_sub_post_request_id"],
        ),
        ("ix_admin_review_cases_target_payment_id", ["target_payment_id"]),
        (
            "ix_admin_review_cases_target_financial_outcome_id",
            ["target_financial_outcome_id"],
        ),
    ):
        op.create_index(index_name, "admin_review_cases", columns)
    op.create_index(
        "uq_admin_review_cases_open_community_game_content_moderation",
        "admin_review_cases",
        ["target_game_id"],
        unique=True,
        postgresql_where=sa.text(
            "target_game_id IS NOT NULL "
            "AND case_type = 'community_game' "
            "AND case_category = 'content_moderation' "
            "AND case_status = 'open'"
        ),
    )
    op.create_index(
        "uq_admin_review_cases_open_need_sub_content_moderation",
        "admin_review_cases",
        ["target_sub_post_id"],
        unique=True,
        postgresql_where=sa.text(
            "target_sub_post_id IS NOT NULL "
            "AND case_type = 'need_a_sub' "
            "AND case_category = 'content_moderation' "
            "AND case_status = 'open'"
        ),
    )
    op.create_foreign_key(
        "fk_admin_financial_outcomes_review_case_id_admin_review_cases",
        "admin_financial_outcomes",
        "admin_review_cases",
        ["review_case_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_admin_financial_outcomes_review_case_id",
        "admin_financial_outcomes",
        ["review_case_id"],
    )

    op.create_table(
        "admin_review_signals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("review_case_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("signal_category", sa.String(length=60), nullable=False),
        sa.Column("source", sa.String(length=60), nullable=False),
        sa.Column(
            "signal_status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'open'"),
        ),
        sa.Column(
            "priority",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'attention'"),
        ),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_game_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_sub_post_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "target_sub_post_request_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("target_payment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "target_financial_outcome_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=160), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
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
            "signal_category IN ('chat_moderation')",
            name="ck_admin_review_signals_signal_category",
        ),
        sa.CheckConstraint(
            "source IN ('chat_moderation')",
            name="ck_admin_review_signals_source",
        ),
        sa.CheckConstraint(
            "signal_status IN ('open', 'attached', 'dismissed')",
            name="ck_admin_review_signals_signal_status",
        ),
        sa.CheckConstraint(
            "priority IN ('attention', 'urgent', 'critical')",
            name="ck_admin_review_signals_priority",
        ),
        sa.ForeignKeyConstraint(
            ["review_case_id"],
            ["admin_review_cases.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_game_id"], ["games.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["target_sub_post_id"],
            ["sub_posts.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_sub_post_request_id"],
            ["sub_post_requests.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_payment_id"],
            ["payments.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_financial_outcome_id"],
            ["admin_financial_outcomes.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for index_name, columns in (
        ("ix_admin_review_signals_review_case_id", ["review_case_id"]),
        ("ix_admin_review_signals_signal_category", ["signal_category"]),
        ("ix_admin_review_signals_signal_status", ["signal_status"]),
        ("ix_admin_review_signals_priority", ["priority"]),
        ("ix_admin_review_signals_created_at", ["created_at"]),
        ("ix_admin_review_signals_target_user_id", ["target_user_id"]),
        ("ix_admin_review_signals_target_game_id", ["target_game_id"]),
        ("ix_admin_review_signals_target_sub_post_id", ["target_sub_post_id"]),
        (
            "ix_admin_review_signals_target_sub_post_request_id",
            ["target_sub_post_request_id"],
        ),
        ("ix_admin_review_signals_target_payment_id", ["target_payment_id"]),
        (
            "ix_admin_review_signals_target_financial_outcome_id",
            ["target_financial_outcome_id"],
        ),
    ):
        op.create_index(index_name, "admin_review_signals", columns)
    op.create_index(
        "uq_admin_review_signals_source_idempotency_key",
        "admin_review_signals",
        ["source", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )

    op.create_table(
        "admin_content_moderation_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("review_case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("risk_area", sa.String(length=60), nullable=False),
        sa.Column("finding_type", sa.String(length=60), nullable=False),
        sa.Column(
            "priority",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'attention'"),
        ),
        sa.Column("source_field", sa.String(length=80), nullable=False),
        sa.Column("source_content_hash", sa.String(length=64), nullable=False),
        sa.Column("evidence_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False),
        sa.Column(
            "current_match",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("first_detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cleared_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scanner_version", sa.String(length=80), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
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
            "risk_area IN ('unsafe_post_text', 'unsafe_payment_text')",
            name="ck_admin_content_moderation_findings_risk_area",
        ),
        sa.CheckConstraint(
            (
                "finding_type IN ("
                "'off_app_contact', 'payment_pressure', 'spam_or_scam', "
                "'threat_or_violence', 'harassment_or_abuse', "
                "'slur_or_hate', 'sexual_or_explicit')"
            ),
            name="ck_admin_content_moderation_findings_finding_type",
        ),
        sa.CheckConstraint(
            "priority IN ('attention', 'urgent', 'critical')",
            name="ck_admin_content_moderation_findings_priority",
        ),
        sa.CheckConstraint(
            "length(trim(source_field)) > 0",
            name="ck_admin_content_moderation_findings_source_field_present",
        ),
        sa.CheckConstraint(
            "length(trim(source_content_hash)) > 0",
            name="ck_admin_content_moderation_findings_source_hash_present",
        ),
        sa.CheckConstraint(
            "length(trim(evidence_fingerprint)) > 0",
            name="ck_admin_content_moderation_findings_fingerprint_present",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(evidence) = 'array' AND jsonb_array_length(evidence) > 0",
            name="ck_admin_content_moderation_findings_evidence_nonempty",
        ),
        sa.CheckConstraint(
            (
                "(current_match = true AND cleared_at IS NULL) "
                "OR (current_match = false AND cleared_at IS NOT NULL)"
            ),
            name="ck_admin_content_moderation_findings_current_clear_state",
        ),
        sa.CheckConstraint(
            "first_detected_at <= last_detected_at",
            name="ck_admin_content_moderation_findings_detected_order",
        ),
        sa.ForeignKeyConstraint(
            ["review_case_id"],
            ["admin_review_cases.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for index_name, columns in (
        (
            "ix_admin_content_moderation_findings_review_case_id",
            ["review_case_id"],
        ),
        ("ix_admin_content_moderation_findings_current_match", ["current_match"]),
        ("ix_admin_content_moderation_findings_finding_type", ["finding_type"]),
        (
            "ix_admin_content_moderation_findings_case_current_type",
            ["review_case_id", "current_match", "finding_type"],
        ),
    ):
        op.create_index(index_name, "admin_content_moderation_findings", columns)
    op.create_index(
        "uq_admin_content_moderation_findings_current_identity",
        "admin_content_moderation_findings",
        ["review_case_id", "source_field", "finding_type", "evidence_fingerprint"],
        unique=True,
        postgresql_where=sa.text("current_match = true"),
    )

    op.create_table(
        "admin_review_case_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("review_case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "note_status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
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
            "note_status IN ('active', 'deleted')",
            name="ck_admin_review_case_notes_note_status",
        ),
        sa.ForeignKeyConstraint(
            ["review_case_id"],
            ["admin_review_cases.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["author_user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_admin_review_case_notes_review_case_id",
        "admin_review_case_notes",
        ["review_case_id"],
    )
    op.create_index(
        "ix_admin_review_case_notes_author_user_id",
        "admin_review_case_notes",
        ["author_user_id"],
    )
    op.create_index(
        "ix_admin_review_case_notes_created_at",
        "admin_review_case_notes",
        ["created_at"],
    )

    op.create_table(
        "admin_review_case_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("review_case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=60), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("admin_action_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "content_moderation_finding_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("note_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            (
                "event_type IN ("
                "'case_created', 'signal_attached', "
                "'finding_attached', 'finding_cleared', "
                "'note_added', 'enforcement_action_linked', "
                "'closed')"
            ),
            name="ck_admin_review_case_events_event_type",
        ),
        sa.CheckConstraint(
            "signal_id IS NULL OR content_moderation_finding_id IS NULL",
            name="ck_admin_review_case_events_one_child_ref",
        ),
        sa.ForeignKeyConstraint(
            ["review_case_id"],
            ["admin_review_cases.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["admin_action_id"],
            ["admin_actions.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["signal_id"],
            ["admin_review_signals.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["content_moderation_finding_id"],
            ["admin_content_moderation_findings.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["note_id"],
            ["admin_review_case_notes.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for index_name, columns in (
        ("ix_admin_review_case_events_review_case_id", ["review_case_id"]),
        ("ix_admin_review_case_events_event_type", ["event_type"]),
        ("ix_admin_review_case_events_actor_user_id", ["actor_user_id"]),
        ("ix_admin_review_case_events_admin_action_id", ["admin_action_id"]),
        ("ix_admin_review_case_events_signal_id", ["signal_id"]),
        (
            "ix_admin_review_case_events_content_moderation_finding_id",
            ["content_moderation_finding_id"],
        ),
        ("ix_admin_review_case_events_note_id", ["note_id"]),
        ("ix_admin_review_case_events_created_at", ["created_at"]),
    ):
        op.create_index(index_name, "admin_review_case_events", columns)

    op.add_column(
        "admin_actions",
        sa.Column("target_review_case_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_admin_actions_target_review_case_id_admin_review_cases",
        "admin_actions",
        "admin_review_cases",
        ["target_review_case_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_admin_actions_target_review_case_id",
        "admin_actions",
        ["target_review_case_id"],
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
    op.create_index(
        "uq_admin_actions_review_case_idempotency",
        "admin_actions",
        ["admin_user_id", "target_review_case_id", "action_type", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text(
            "action_type IN ("
            "'create_review_case', 'close_review_case', "
            "'add_review_case_note'"
            ") AND idempotency_key IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_admin_financial_outcomes_review_case_id",
        table_name="admin_financial_outcomes",
    )
    op.drop_constraint(
        "fk_admin_financial_outcomes_review_case_id_admin_review_cases",
        "admin_financial_outcomes",
        type_="foreignkey",
    )

    review_action_list = ", ".join(f"'{action}'" for action in REVIEW_ACTION_TYPES)
    op.execute(
        sa.text(
            f"DELETE FROM admin_actions WHERE action_type IN ({review_action_list})"
        )
    )
    op.drop_index(
        "uq_admin_actions_review_case_idempotency",
        table_name="admin_actions",
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
        "ck_admin_actions_action_type",
        "admin_actions",
        type_="check",
    )
    op.create_check_constraint(
        "ck_admin_actions_action_type",
        "admin_actions",
        PREVIOUS_ADMIN_ACTION_TYPE_CHECK,
    )
    op.drop_index(
        "ix_admin_actions_target_review_case_id",
        table_name="admin_actions",
    )
    op.drop_constraint(
        "fk_admin_actions_target_review_case_id_admin_review_cases",
        "admin_actions",
        type_="foreignkey",
    )
    op.drop_column("admin_actions", "target_review_case_id")

    for index_name in (
        "ix_admin_review_case_events_created_at",
        "ix_admin_review_case_events_note_id",
        "ix_admin_review_case_events_content_moderation_finding_id",
        "ix_admin_review_case_events_signal_id",
        "ix_admin_review_case_events_admin_action_id",
        "ix_admin_review_case_events_actor_user_id",
        "ix_admin_review_case_events_event_type",
        "ix_admin_review_case_events_review_case_id",
    ):
        op.drop_index(index_name, table_name="admin_review_case_events")
    op.drop_table("admin_review_case_events")

    op.drop_index(
        "ix_admin_review_case_notes_created_at",
        table_name="admin_review_case_notes",
    )
    op.drop_index(
        "ix_admin_review_case_notes_author_user_id",
        table_name="admin_review_case_notes",
    )
    op.drop_index(
        "ix_admin_review_case_notes_review_case_id",
        table_name="admin_review_case_notes",
    )
    op.drop_table("admin_review_case_notes")

    op.drop_index(
        "uq_admin_content_moderation_findings_current_identity",
        table_name="admin_content_moderation_findings",
    )
    for index_name in (
        "ix_admin_content_moderation_findings_case_current_type",
        "ix_admin_content_moderation_findings_finding_type",
        "ix_admin_content_moderation_findings_current_match",
        "ix_admin_content_moderation_findings_review_case_id",
    ):
        op.drop_index(index_name, table_name="admin_content_moderation_findings")
    op.drop_table("admin_content_moderation_findings")

    op.drop_index(
        "uq_admin_review_signals_source_idempotency_key",
        table_name="admin_review_signals",
    )
    for index_name in (
        "ix_admin_review_signals_target_financial_outcome_id",
        "ix_admin_review_signals_target_payment_id",
        "ix_admin_review_signals_target_sub_post_request_id",
        "ix_admin_review_signals_target_sub_post_id",
        "ix_admin_review_signals_target_game_id",
        "ix_admin_review_signals_target_user_id",
        "ix_admin_review_signals_created_at",
        "ix_admin_review_signals_priority",
        "ix_admin_review_signals_signal_status",
        "ix_admin_review_signals_signal_category",
        "ix_admin_review_signals_review_case_id",
    ):
        op.drop_index(index_name, table_name="admin_review_signals")
    op.drop_table("admin_review_signals")

    for index_name in (
        "uq_admin_review_cases_open_need_sub_content_moderation",
        "uq_admin_review_cases_open_community_game_content_moderation",
    ):
        op.drop_index(index_name, table_name="admin_review_cases")
    for index_name in (
        "ix_admin_review_cases_target_financial_outcome_id",
        "ix_admin_review_cases_target_payment_id",
        "ix_admin_review_cases_target_sub_post_request_id",
        "ix_admin_review_cases_target_sub_post_id",
        "ix_admin_review_cases_target_game_id",
        "ix_admin_review_cases_target_user_id",
        "ix_admin_review_cases_closed_at",
        "ix_admin_review_cases_status_updated_id",
        "ix_admin_review_cases_created_at",
        "ix_admin_review_cases_priority",
        "ix_admin_review_cases_case_category",
        "ix_admin_review_cases_case_type",
        "ix_admin_review_cases_case_status",
    ):
        op.drop_index(index_name, table_name="admin_review_cases")
    op.drop_table("admin_review_cases")
