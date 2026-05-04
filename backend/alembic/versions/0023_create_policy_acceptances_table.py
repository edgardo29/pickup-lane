"""create policy acceptances table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0023_policy_acceptances"
down_revision = "0022_policy_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Twenty-third schema migration: create policy_acceptances as user-level
    # acceptance records for specific policy document versions.
    op.create_table(
        "policy_acceptances",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "accepted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["policy_document_id"],
            ["policy_documents.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "policy_document_id",
            name="uq_policy_acceptances_user_id_policy_document_id",
        ),
    )
    op.create_index(
        "ix_policy_acceptances_user_id",
        "policy_acceptances",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_policy_acceptances_policy_document_id",
        "policy_acceptances",
        ["policy_document_id"],
        unique=False,
    )
    op.create_index(
        "ix_policy_acceptances_accepted_at",
        "policy_acceptances",
        ["accepted_at"],
        unique=False,
    )


def downgrade() -> None:
    # Downgrade removes the policy_acceptances table and indexes because this
    # migration only introduces that single policy acceptance table.
    op.drop_index(
        "ix_policy_acceptances_accepted_at",
        table_name="policy_acceptances",
    )
    op.drop_index(
        "ix_policy_acceptances_policy_document_id",
        table_name="policy_acceptances",
    )
    op.drop_index("ix_policy_acceptances_user_id", table_name="policy_acceptances")
    op.drop_table("policy_acceptances")