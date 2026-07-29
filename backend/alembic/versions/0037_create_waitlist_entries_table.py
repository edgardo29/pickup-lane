"""create waitlist_entries table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0037_waitlist_entries'
down_revision = '0036_sub_post_req_status_hist'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'waitlist_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('game_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('party_size', sa.Integer(), nullable=False, server_default=sa.text('1')),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('waitlist_status', sa.String(length=30), nullable=False, server_default=sa.text("'active'")),
        sa.Column('promoted_booking_id', postgresql.UUID(as_uuid=True)),
        sa.Column('promotion_expires_at', sa.DateTime(timezone=True)),
        sa.Column('auto_charge_consent_at', sa.DateTime(timezone=True)),
        sa.Column('auto_charge_consent_version', sa.String(length=50)),
        sa.Column('authorized_payment_method_id', postgresql.UUID(as_uuid=True)),
        sa.Column('authorized_stripe_payment_method_id', sa.String(length=255)),
        sa.Column('authorized_payment_method_brand', sa.String(length=50)),
        sa.Column('authorized_payment_method_last4', sa.String(length=4)),
        sa.Column('authorized_amount_cents', sa.Integer()),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('promoted_at', sa.DateTime(timezone=True)),
        sa.Column('cancelled_at', sa.DateTime(timezone=True)),
        sa.Column('expired_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint('(authorized_amount_cents IS NULL OR authorized_amount_cents >= 0)', name='ck_waitlist_entries_authorized_amount_non_negative'),
        sa.CheckConstraint("(waitlist_status <> 'cancelled' OR cancelled_at IS NOT NULL)", name='ck_waitlist_entries_cancelled_requires_cancelled_at'),
        sa.CheckConstraint("(waitlist_status <> 'expired' OR expired_at IS NOT NULL)", name='ck_waitlist_entries_expired_requires_expired_at'),
        sa.CheckConstraint('party_size > 0', name='ck_waitlist_entries_party_size'),
        sa.CheckConstraint('position > 0', name='ck_waitlist_entries_position'),
        sa.CheckConstraint("(waitlist_status <> 'promoted' OR promoted_at IS NOT NULL)", name='ck_waitlist_entries_promoted_requires_promoted_at'),
        sa.CheckConstraint("(waitlist_status <> 'promoted' OR promotion_expires_at IS NOT NULL)", name='ck_waitlist_entries_promoted_requires_promotion_expires_at'),
        sa.CheckConstraint("waitlist_status IN ('active', 'promoted', 'accepted', 'declined', 'expired', 'cancelled', 'removed', 'payment_processing', 'payment_failed')", name='ck_waitlist_entries_waitlist_status'),
        sa.ForeignKeyConstraint(['authorized_payment_method_id'], ['user_payment_methods.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['promoted_booking_id'], ['bookings.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_waitlist_entries_game_id', 'waitlist_entries', ['game_id'], unique=False)
    op.create_index('ix_waitlist_entries_game_id_waitlist_status_position', 'waitlist_entries', ['game_id', 'waitlist_status', 'position'], unique=False)
    op.create_index('ix_waitlist_entries_game_user_status', 'waitlist_entries', ['game_id', 'user_id', 'waitlist_status'], unique=False)
    op.create_index('ix_waitlist_entries_user_id', 'waitlist_entries', ['user_id'], unique=False)
    op.create_index('ix_waitlist_entries_user_id_waitlist_status', 'waitlist_entries', ['user_id', 'waitlist_status'], unique=False)
    op.create_index('ix_waitlist_entries_waitlist_status', 'waitlist_entries', ['waitlist_status'], unique=False)
    op.create_index('ux_waitlist_entries_active_position_per_game', 'waitlist_entries', ['game_id', 'position'], unique=True, postgresql_where=sa.text("waitlist_status = 'active'"))
    op.create_index('ux_waitlist_entries_active_user_per_game', 'waitlist_entries', ['game_id', 'user_id'], unique=True, postgresql_where=sa.text("waitlist_status IN ('active', 'payment_processing')"))


def downgrade() -> None:
    op.drop_table('waitlist_entries')
