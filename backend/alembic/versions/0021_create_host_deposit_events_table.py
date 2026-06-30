"""retire host deposit events table"""


revision = "0021_host_deposit_events"
down_revision = "0020_payment_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Host deposit events were retired with host deposits before production
    # data. Keep this revision as a no-op to preserve the migration chain.
    pass


def downgrade() -> None:
    pass
