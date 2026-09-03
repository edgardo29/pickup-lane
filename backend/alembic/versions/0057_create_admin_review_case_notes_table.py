"""create admin_review_case_notes table"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0057_admin_review_case_notes"
down_revision = "0056_admin_content_findings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_review_case_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("review_case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("corrects_note_id", postgresql.UUID(as_uuid=True)),
        sa.Column(
            "note_status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column("edited_at", sa.DateTime(timezone=True)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
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
            "note_status = 'active' AND edited_at IS NULL AND deleted_at IS NULL",
            name="ck_admin_review_case_notes_note_status",
        ),
        sa.CheckConstraint(
            "corrects_note_id IS NULL OR corrects_note_id <> id",
            name="ck_admin_review_case_notes_no_self_correction",
        ),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["corrects_note_id"], ["admin_review_case_notes.id"], ondelete="RESTRICT"
        ),
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
        "ix_admin_review_case_notes_corrects_note_id",
        "admin_review_case_notes",
        ["corrects_note_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_review_case_notes_review_case_id",
        "admin_review_case_notes",
        ["review_case_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("admin_review_case_notes")
