"""create admin_review_case_resolution_references table"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0066_review_case_resolution_refs"
down_revision = "0065_payment_method_ops"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_review_case_resolution_references",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("closure_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reference_type", sa.String(length=30), nullable=False),
        sa.Column("content_moderation_finding_id", postgresql.UUID(as_uuid=True)),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True)),
        sa.Column("admin_action_id", postgresql.UUID(as_uuid=True)),
        sa.Column("source_case_id", postgresql.UUID(as_uuid=True)),
        sa.Column("was_current", sa.Boolean()),
        sa.CheckConstraint(
            "reference_type IN ('finding', 'signal', 'enforcement_action', 'source_case')",
            name="ck_admin_review_case_resolution_refs_type",
        ),
        sa.CheckConstraint(
            "(reference_type = 'finding' AND content_moderation_finding_id IS NOT NULL AND signal_id IS NULL AND admin_action_id IS NULL AND source_case_id IS NULL AND was_current IS NOT NULL) OR "
            "(reference_type = 'signal' AND signal_id IS NOT NULL AND content_moderation_finding_id IS NULL AND admin_action_id IS NULL AND source_case_id IS NULL AND was_current IS NOT NULL) OR "
            "(reference_type = 'enforcement_action' AND admin_action_id IS NOT NULL AND content_moderation_finding_id IS NULL AND signal_id IS NULL AND source_case_id IS NULL AND was_current IS NULL) OR "
            "(reference_type = 'source_case' AND source_case_id IS NOT NULL AND content_moderation_finding_id IS NULL AND signal_id IS NULL AND admin_action_id IS NULL AND was_current IS NULL)",
            name="ck_admin_review_case_resolution_refs_shape",
        ),
        sa.ForeignKeyConstraint(
            ["closure_event_id"], ["admin_review_case_events.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["content_moderation_finding_id"],
            ["admin_content_moderation_findings.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["signal_id"], ["admin_review_signals.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["admin_action_id"], ["admin_actions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["source_case_id"], ["admin_review_cases.id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint(
            "closure_event_id",
            "content_moderation_finding_id",
            name="uq_admin_review_case_resolution_refs_finding",
        ),
        sa.UniqueConstraint(
            "closure_event_id",
            "signal_id",
            name="uq_admin_review_case_resolution_refs_signal",
        ),
        sa.UniqueConstraint(
            "closure_event_id",
            "admin_action_id",
            name="uq_admin_review_case_resolution_refs_action",
        ),
        sa.UniqueConstraint(
            "closure_event_id",
            "source_case_id",
            name="uq_admin_review_case_resolution_refs_source_case",
        ),
    )
    op.create_index(
        "ix_admin_review_case_resolution_refs_closure_event_id",
        "admin_review_case_resolution_references",
        ["closure_event_id"],
    )
    op.execute("""
        CREATE FUNCTION validate_admin_review_case_resolution_ref_insert()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            owning_case_id uuid;
            owning_event_type text;
            owning_event_action_id uuid;
            owning_event_xmin xid;
            referenced_case_id uuid;
            referenced_current boolean;
            referenced_action_type text;
        BEGIN
            SELECT review_case_id, event_type, admin_action_id, xmin
            INTO owning_case_id, owning_event_type, owning_event_action_id,
                 owning_event_xmin
            FROM admin_review_case_events
            WHERE id = NEW.closure_event_id;

            IF owning_event_type IS NULL OR owning_event_type <> 'closed' THEN
                RAISE EXCEPTION 'resolution references require a closure event';
            END IF;
            IF NEW.reference_type = 'finding' THEN
                SELECT review_case_id, current_match
                INTO referenced_case_id, referenced_current
                FROM admin_content_moderation_findings
                WHERE id = NEW.content_moderation_finding_id;
                IF referenced_case_id IS NULL
                   OR (
                       referenced_case_id <> owning_case_id
                       AND NOT EXISTS (
                           SELECT 1 FROM admin_review_cases
                           WHERE id = referenced_case_id
                             AND merged_into_case_id = owning_case_id
                       )
                   )
                   OR NEW.was_current IS DISTINCT FROM referenced_current THEN
                    RAISE EXCEPTION 'resolution finding ownership is invalid';
                END IF;
            ELSIF NEW.reference_type = 'signal' THEN
                SELECT review_case_id,
                       CASE
                           WHEN jsonb_typeof(metadata->'current_match') = 'boolean'
                           THEN (metadata->>'current_match')::boolean
                           ELSE true
                       END
                INTO referenced_case_id, referenced_current
                FROM admin_review_signals
                WHERE id = NEW.signal_id;
                IF referenced_case_id IS NULL
                   OR (
                       referenced_case_id <> owning_case_id
                       AND NOT EXISTS (
                           SELECT 1 FROM admin_review_cases
                           WHERE id = referenced_case_id
                             AND merged_into_case_id = owning_case_id
                       )
                   )
                   OR NEW.was_current IS DISTINCT FROM referenced_current THEN
                    RAISE EXCEPTION 'resolution signal ownership is invalid';
                END IF;
            ELSIF NEW.reference_type = 'enforcement_action' THEN
                SELECT target_review_case_id, action_type
                INTO referenced_case_id, referenced_action_type
                FROM admin_actions
                WHERE id = NEW.admin_action_id;
                IF referenced_case_id IS NULL
                   OR referenced_action_type IN (
                       'create_review_case', 'close_review_case',
                       'add_review_case_note', 'assign_review_case',
                       'reopen_review_case', 'merge_review_case'
                   )
                   OR (
                       referenced_case_id <> owning_case_id
                       AND NOT EXISTS (
                           SELECT 1 FROM admin_review_cases
                           WHERE id = referenced_case_id
                             AND merged_into_case_id = owning_case_id
                       )
                   )
                   OR (
                       NEW.admin_action_id IS DISTINCT FROM owning_event_action_id
                       AND NOT EXISTS (
                           SELECT 1 FROM admin_review_case_events
                           WHERE review_case_id = referenced_case_id
                             AND event_type = 'enforcement_action_linked'
                             AND admin_action_id = NEW.admin_action_id
                       )
                   ) THEN
                    RAISE EXCEPTION 'resolution enforcement action ownership is invalid';
                END IF;
            ELSIF NEW.reference_type = 'source_case' THEN
                IF NEW.source_case_id = owning_case_id
                   OR NOT EXISTS (
                       SELECT 1 FROM admin_review_cases
                       WHERE id = NEW.source_case_id
                         AND merged_into_case_id = owning_case_id
                   ) THEN
                    RAISE EXCEPTION 'resolution source case ownership is invalid';
                END IF;
            END IF;
            IF owning_event_xmin IS DISTINCT FROM pg_current_xact_id()::xid THEN
                RAISE EXCEPTION 'closure resolution reference set is sealed';
            END IF;
            RETURN NEW;
        END;
        $$
    """)
    op.execute("""
        CREATE TRIGGER trg_admin_review_case_resolution_refs_validate_insert
        BEFORE INSERT ON admin_review_case_resolution_references
        FOR EACH ROW EXECUTE FUNCTION validate_admin_review_case_resolution_ref_insert()
    """)
    op.execute("""
        CREATE FUNCTION reject_admin_review_case_resolution_ref_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'admin review case resolution references are immutable';
        END;
        $$
    """)
    op.execute("""
        CREATE TRIGGER trg_admin_review_case_resolution_refs_immutable
        BEFORE UPDATE OR DELETE ON admin_review_case_resolution_references
        FOR EACH ROW EXECUTE FUNCTION reject_admin_review_case_resolution_ref_mutation()
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_admin_review_case_resolution_refs_validate_insert "
        "ON admin_review_case_resolution_references"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS validate_admin_review_case_resolution_ref_insert()"
    )
    op.execute(
        "DROP TRIGGER trg_admin_review_case_resolution_refs_immutable "
        "ON admin_review_case_resolution_references"
    )
    op.execute("DROP FUNCTION reject_admin_review_case_resolution_ref_mutation()")
    op.drop_table("admin_review_case_resolution_references")
