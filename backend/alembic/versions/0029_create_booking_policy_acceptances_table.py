"""create booking_policy_acceptances table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0029_booking_policy_acceptances'
down_revision = '0028_admin_target_notices'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'booking_policy_acceptances',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('booking_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('policy_document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['policy_document_id'], ['policy_documents.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('booking_id', 'policy_document_id', name='uq_booking_policy_acceptances_booking_id_policy_document_id')
    )
    op.create_index('ix_booking_policy_acceptances_accepted_at', 'booking_policy_acceptances', ['accepted_at'], unique=False)
    op.create_index('ix_booking_policy_acceptances_booking_id', 'booking_policy_acceptances', ['booking_id'], unique=False)
    op.create_index('ix_booking_policy_acceptances_policy_document_id', 'booking_policy_acceptances', ['policy_document_id'], unique=False)


def downgrade() -> None:
    op.drop_table('booking_policy_acceptances')
