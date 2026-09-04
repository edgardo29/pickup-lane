"""create admin_review_cases table"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0053_admin_review_cases"
down_revision = "0052_refund_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_review_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
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
        sa.Column(
            "case_version", sa.Integer(), nullable=False, server_default=sa.text("1")
        ),
        sa.Column("creation_reason", sa.String(length=80), nullable=False),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("target_game_id", postgresql.UUID(as_uuid=True)),
        sa.Column("target_sub_post_id", postgresql.UUID(as_uuid=True)),
        sa.Column("target_sub_post_request_id", postgresql.UUID(as_uuid=True)),
        sa.Column("target_payment_id", postgresql.UUID(as_uuid=True)),
        sa.Column("target_financial_outcome_id", postgresql.UUID(as_uuid=True)),
        sa.Column("opened_by_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("closed_by_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("closure_outcome", sa.String(length=60)),
        sa.Column("closure_reason", sa.Text()),
        sa.Column("closure_mode", sa.String(length=30)),
        sa.Column("closure_rule_id", sa.String(length=120)),
        sa.Column("closure_rule_version", sa.String(length=40)),
        sa.Column("assigned_to_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("assigned_at", sa.DateTime(timezone=True)),
        sa.Column("merged_into_case_id", postgresql.UUID(as_uuid=True)),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
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
            "case_category IN ('content_moderation', 'chat_moderation')",
            name="ck_admin_review_cases_case_category",
        ),
        sa.CheckConstraint(
            "case_status IN ('open', 'closed')",
            name="ck_admin_review_cases_case_status",
        ),
        sa.CheckConstraint(
            "case_type IN ('community_game', 'need_a_sub', 'money', 'user', 'system')",
            name="ck_admin_review_cases_case_type",
        ),
        sa.CheckConstraint(
            "closure_outcome IS NULL OR closure_outcome IN ('enforcement_applied', 'no_action_needed', 'invalid_signal')",
            name="ck_admin_review_cases_closure_outcome",
        ),
        sa.CheckConstraint(
            "(case_status = 'open' AND closed_by_user_id IS NULL AND closure_outcome IS NULL AND closure_reason IS NULL AND closure_mode IS NULL AND closure_rule_id IS NULL AND closure_rule_version IS NULL AND closed_at IS NULL AND merged_into_case_id IS NULL) OR (case_status = 'closed' AND closure_outcome IS NOT NULL AND closure_reason IS NOT NULL AND btrim(closure_reason) <> '' AND closure_mode IS NOT NULL AND closed_at IS NOT NULL)",
            name="ck_admin_review_cases_closure_state",
        ),
        sa.CheckConstraint(
            "(closure_mode IS NULL) OR (closure_mode = 'manual' AND closure_outcome IN ('enforcement_applied', 'no_action_needed', 'invalid_signal') AND closed_by_user_id IS NOT NULL AND closure_rule_id IS NULL AND closure_rule_version IS NULL) OR (closure_mode = 'automatic' AND closure_outcome IN ('enforcement_applied', 'no_action_needed', 'invalid_signal') AND closure_rule_id IS NOT NULL AND btrim(closure_rule_id) <> '' AND closure_rule_version IS NOT NULL AND btrim(closure_rule_version) <> '')",
            name="ck_admin_review_cases_resolution_shape",
        ),
        sa.CheckConstraint(
            "closure_mode IS NULL OR closure_mode IN ('manual', 'automatic')",
            name="ck_admin_review_cases_closure_mode",
        ),
        sa.CheckConstraint(
            "case_version > 0", name="ck_admin_review_cases_case_version_positive"
        ),
        sa.CheckConstraint(
            "btrim(creation_reason) <> ''",
            name="ck_admin_review_cases_creation_reason_nonblank",
        ),
        sa.CheckConstraint(
            "(assigned_to_user_id IS NULL AND assigned_at IS NULL) OR (case_status = 'open' AND assigned_to_user_id IS NOT NULL AND assigned_at IS NOT NULL)",
            name="ck_admin_review_cases_assignment_shape",
        ),
        sa.CheckConstraint(
            "merged_into_case_id IS NULL OR merged_into_case_id <> id",
            name="ck_admin_review_cases_no_self_merge",
        ),
        sa.CheckConstraint(
            "merged_into_case_id IS NULL OR (case_status = 'closed' AND closure_mode IN ('manual', 'automatic') AND closure_outcome IN ('enforcement_applied', 'no_action_needed', 'invalid_signal') AND closure_reason IS NOT NULL AND btrim(closure_reason) <> '' AND closed_at IS NOT NULL)",
            name="ck_admin_review_cases_merged_source_resolved",
        ),
        sa.CheckConstraint(
            "priority IN ('attention', 'urgent', 'critical')",
            name="ck_admin_review_cases_priority",
        ),
        sa.CheckConstraint(
            "case_status = 'closed' OR target_user_id IS NOT NULL OR target_game_id IS NOT NULL OR target_sub_post_id IS NOT NULL OR target_sub_post_request_id IS NOT NULL OR target_payment_id IS NOT NULL OR target_financial_outcome_id IS NOT NULL",
            name="ck_admin_review_cases_target_required",
        ),
        sa.CheckConstraint(
            "case_type <> 'community_game' OR (target_game_id IS NOT NULL AND target_user_id IS NULL AND target_sub_post_id IS NULL AND target_sub_post_request_id IS NULL AND target_payment_id IS NULL AND target_financial_outcome_id IS NULL)",
            name="ck_admin_review_cases_community_game_target",
        ),
        sa.CheckConstraint(
            "case_type <> 'need_a_sub' OR (target_sub_post_id IS NOT NULL AND target_user_id IS NULL AND target_game_id IS NULL AND target_sub_post_request_id IS NULL AND target_payment_id IS NULL AND target_financial_outcome_id IS NULL)",
            name="ck_admin_review_cases_need_sub_target",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_to_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["closed_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["merged_into_case_id"], ["admin_review_cases.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["opened_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["target_financial_outcome_id"],
            ["admin_financial_outcomes.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["target_game_id"], ["games.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["target_payment_id"], ["payments.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["target_sub_post_id"], ["sub_posts.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["target_sub_post_request_id"],
            ["sub_post_requests.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute("""
        CREATE FUNCTION reject_admin_review_case_identity_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.case_type IS DISTINCT FROM OLD.case_type
               OR NEW.case_category IS DISTINCT FROM OLD.case_category
               OR NEW.target_user_id IS DISTINCT FROM OLD.target_user_id
               OR NEW.target_game_id IS DISTINCT FROM OLD.target_game_id
               OR NEW.target_sub_post_id IS DISTINCT FROM OLD.target_sub_post_id
               OR NEW.target_sub_post_request_id
                    IS DISTINCT FROM OLD.target_sub_post_request_id
               OR NEW.target_payment_id IS DISTINCT FROM OLD.target_payment_id
               OR NEW.target_financial_outcome_id
                    IS DISTINCT FROM OLD.target_financial_outcome_id THEN
                RAISE EXCEPTION 'admin review case identity is immutable';
            END IF;
            RETURN NEW;
        END;
        $$
    """)
    op.execute("""
        CREATE TRIGGER trg_admin_review_cases_identity_immutable
        BEFORE UPDATE ON admin_review_cases
        FOR EACH ROW EXECUTE FUNCTION reject_admin_review_case_identity_mutation()
    """)
    op.create_index(
        "ix_admin_review_cases_case_category",
        "admin_review_cases",
        ["case_category"],
        unique=False,
    )
    op.create_index(
        "ix_admin_review_cases_case_status",
        "admin_review_cases",
        ["case_status"],
        unique=False,
    )
    op.create_index(
        "ix_admin_review_cases_case_type",
        "admin_review_cases",
        ["case_type"],
        unique=False,
    )
    op.create_index(
        "ix_admin_review_cases_assigned_to_user_id",
        "admin_review_cases",
        ["assigned_to_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_review_cases_closed_at",
        "admin_review_cases",
        ["closed_at"],
        unique=False,
    )
    op.create_index(
        "ix_admin_review_cases_created_at",
        "admin_review_cases",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_admin_review_cases_priority",
        "admin_review_cases",
        ["priority"],
        unique=False,
    )
    op.create_index(
        "ix_admin_review_cases_merged_into_case_id",
        "admin_review_cases",
        ["merged_into_case_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_review_cases_status_updated_id",
        "admin_review_cases",
        ["case_status", "updated_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_review_cases_target_financial_outcome_id",
        "admin_review_cases",
        ["target_financial_outcome_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_review_cases_target_game_id",
        "admin_review_cases",
        ["target_game_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_review_cases_target_payment_id",
        "admin_review_cases",
        ["target_payment_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_review_cases_target_sub_post_id",
        "admin_review_cases",
        ["target_sub_post_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_review_cases_target_sub_post_request_id",
        "admin_review_cases",
        ["target_sub_post_request_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_review_cases_target_user_id",
        "admin_review_cases",
        ["target_user_id"],
        unique=False,
    )
    op.create_index(
        "uq_admin_review_cases_open_community_game_moderation",
        "admin_review_cases",
        ["target_game_id", "case_category"],
        unique=True,
        postgresql_where=sa.text(
            "target_game_id IS NOT NULL AND case_type = 'community_game' AND case_category IN ('content_moderation', 'chat_moderation') AND case_status = 'open'"
        ),
    )
    op.create_index(
        "uq_admin_review_cases_open_need_sub_moderation",
        "admin_review_cases",
        ["target_sub_post_id", "case_category"],
        unique=True,
        postgresql_where=sa.text(
            "target_sub_post_id IS NOT NULL AND case_type = 'need_a_sub' AND case_category IN ('content_moderation', 'chat_moderation') AND case_status = 'open'"
        ),
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER trg_admin_review_cases_identity_immutable ON admin_review_cases"
    )
    op.execute("DROP FUNCTION reject_admin_review_case_identity_mutation()")
    op.drop_table("admin_review_cases")
