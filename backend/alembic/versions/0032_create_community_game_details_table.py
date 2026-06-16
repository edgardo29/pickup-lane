"""create community game details table"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0032_community_game_details"
down_revision = "0031_sub_post_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "community_game_details",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "payment_methods_snapshot",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("payment_instructions_snapshot", sa.Text(), nullable=True),
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
            "jsonb_typeof(payment_methods_snapshot) = 'array'",
            name="ck_community_game_details_payment_methods_array",
        ),
        sa.ForeignKeyConstraint(
            ["game_id"],
            ["games.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("game_id", name="uq_community_game_details_game_id"),
    )
    op.create_index(
        "ix_community_game_details_game_id",
        "community_game_details",
        ["game_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_community_game_details_game_id",
        table_name="community_game_details",
    )
    op.drop_table("community_game_details")
