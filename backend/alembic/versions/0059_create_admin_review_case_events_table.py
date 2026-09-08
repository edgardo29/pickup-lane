"""create admin_review_case_events table"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0059_admin_review_case_events"
down_revision = "0058_admin_review_signals"
branch_labels = None
depends_on = None

CREATE_REVIEW_CASE_EVENT_GUARD_SQL = """
CREATE OR REPLACE FUNCTION reject_admin_review_case_event_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'review case events are immutable';
END;
$$;
CREATE TRIGGER trg_admin_review_case_events_immutable
BEFORE UPDATE OR DELETE ON admin_review_case_events
FOR EACH ROW EXECUTE FUNCTION reject_admin_review_case_event_mutation();
"""
DROP_REVIEW_CASE_EVENT_GUARD_SQL = (
    "DROP FUNCTION IF EXISTS reject_admin_review_case_event_mutation() CASCADE"
)


def upgrade() -> None:
    op.create_table(
        "admin_review_case_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("review_case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_version", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=60), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("admin_action_id", postgresql.UUID(as_uuid=True)),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True)),
        sa.Column("content_moderation_finding_id", postgresql.UUID(as_uuid=True)),
        sa.Column("note_id", postgresql.UUID(as_uuid=True)),
        sa.Column("event_metadata", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "event_type IN ('case_created', 'signal_attached', 'signal_superseded', 'signal_reactivated', 'finding_attached', 'finding_cleared', 'note_added', 'enforcement_action_linked', 'closed')",
            name="ck_admin_review_case_events_event_type",
        ),
        sa.CheckConstraint(
            "(event_type = 'case_created' AND signal_id IS NULL AND content_moderation_finding_id IS NULL AND note_id IS NULL AND admin_action_id IS NULL) OR (event_type IN ('signal_attached', 'signal_superseded', 'signal_reactivated') AND signal_id IS NOT NULL AND content_moderation_finding_id IS NULL AND note_id IS NULL AND admin_action_id IS NULL) OR (event_type IN ('finding_attached', 'finding_cleared') AND signal_id IS NULL AND content_moderation_finding_id IS NOT NULL AND note_id IS NULL AND admin_action_id IS NULL) OR (event_type = 'note_added' AND signal_id IS NULL AND content_moderation_finding_id IS NULL AND note_id IS NOT NULL AND admin_action_id IS NOT NULL) OR (event_type = 'enforcement_action_linked' AND signal_id IS NULL AND content_moderation_finding_id IS NULL AND note_id IS NULL AND admin_action_id IS NOT NULL) OR (event_type = 'closed' AND signal_id IS NULL AND content_moderation_finding_id IS NULL AND note_id IS NULL)",
            name="ck_admin_review_case_events_reference_shape",
        ),
        sa.CheckConstraint(
            "case_version > 0", name="ck_admin_review_case_events_case_version_positive"
        ),
        sa.CheckConstraint(
            "event_type = 'closed' OR event_metadata IS NULL",
            name="ck_admin_review_case_events_metadata_scope",
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["admin_action_id"], ["admin_actions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["content_moderation_finding_id"],
            ["admin_content_moderation_findings.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["note_id"], ["admin_review_case_notes.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["review_case_id"], ["admin_review_cases.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["signal_id"], ["admin_review_signals.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "review_case_id",
            "case_version",
            name="uq_admin_review_case_events_case_version",
        ),
    )
    op.create_index(
        "ix_admin_review_case_events_actor_user_id",
        "admin_review_case_events",
        ["actor_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_review_case_events_admin_action_id",
        "admin_review_case_events",
        ["admin_action_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_review_case_events_content_moderation_finding_id",
        "admin_review_case_events",
        ["content_moderation_finding_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_review_case_events_created_at",
        "admin_review_case_events",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_admin_review_case_events_event_type",
        "admin_review_case_events",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        "ix_admin_review_case_events_note_id",
        "admin_review_case_events",
        ["note_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_review_case_events_review_case_id",
        "admin_review_case_events",
        ["review_case_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_review_case_events_signal_id",
        "admin_review_case_events",
        ["signal_id"],
        unique=False,
    )
    op.get_bind().exec_driver_sql(CREATE_REVIEW_CASE_EVENT_GUARD_SQL)


def downgrade() -> None:
    op.get_bind().exec_driver_sql(DROP_REVIEW_CASE_EVENT_GUARD_SQL)
    op.drop_table("admin_review_case_events")
