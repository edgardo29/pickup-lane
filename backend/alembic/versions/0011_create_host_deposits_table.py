"""retire host deposits table"""

from alembic import op


revision = "0011_host_deposits"
down_revision = "0010_refunds"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Host deposits were replaced by host_publish_fees before production data.
    # Keep this revision as a no-op so the existing migration chain remains
    # stable while rebuilt development databases omit the old table.
    op.execute("DROP TABLE IF EXISTS host_deposits")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS host_deposits")
