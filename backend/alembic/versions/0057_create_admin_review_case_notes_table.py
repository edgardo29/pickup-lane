"""create admin_review_case_notes table"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0057_admin_review_case_notes"
down_revision = "0056_admin_content_findings"
branch_labels = None
depends_on = None

CREATE_REVIEW_CASE_NOTE_GUARD_SQL = """
CREATE OR REPLACE FUNCTION reject_admin_review_case_note_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'review case notes are immutable';
END;
$$;
CREATE TRIGGER trg_admin_review_case_notes_immutable
BEFORE UPDATE OR DELETE ON admin_review_case_notes
FOR EACH ROW EXECUTE FUNCTION reject_admin_review_case_note_mutation();
"""
DROP_REVIEW_CASE_NOTE_GUARD_SQL = (
    "DROP FUNCTION IF EXISTS reject_admin_review_case_note_mutation() CASCADE"
)


def upgrade() -> None:
    op.create_table(
        "admin_review_case_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("review_case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["review_case_id"], ["admin_review_cases.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_admin_review_case_notes_author_user_id",
        "admin_review_case_notes",
        ["author_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_review_case_notes_created_at",
        "admin_review_case_notes",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_admin_review_case_notes_review_case_id",
        "admin_review_case_notes",
        ["review_case_id"],
        unique=False,
    )
    op.get_bind().exec_driver_sql(CREATE_REVIEW_CASE_NOTE_GUARD_SQL)


def downgrade() -> None:
    op.get_bind().exec_driver_sql(DROP_REVIEW_CASE_NOTE_GUARD_SQL)
    op.drop_table("admin_review_case_notes")
