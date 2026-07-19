import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


# Host publish entitlements are the ledger of free/credited community publishes.
class HostPublishEntitlement(Base):
    __tablename__ = "host_publish_entitlements"
    __table_args__ = (
        CheckConstraint(
            (
                "entitlement_type IN ("
                "'first_free', 'admin_grant', 'refund_replacement', 'courtesy'"
                ")"
            ),
            name="ck_host_publish_entitlements_type",
        ),
        CheckConstraint(
            "status IN ('available', 'reserved', 'used', 'revoked', 'expired')",
            name="ck_host_publish_entitlements_status",
        ),
        CheckConstraint(
            "source IN ('system', 'admin', 'financial_outcome')",
            name="ck_host_publish_entitlements_source",
        ),
        CheckConstraint(
            (
                "status <> 'reserved' OR "
                "(reserved_by_attempt_id IS NOT NULL AND used_at IS NULL)"
            ),
            name="ck_host_publish_entitlements_reserved_requirements",
        ),
        CheckConstraint(
            (
                "status <> 'used' OR ("
                "used_by_game_id IS NOT NULL "
                "AND used_by_host_publish_fee_id IS NOT NULL "
                "AND used_at IS NOT NULL)"
            ),
            name="ck_host_publish_entitlements_used_requirements",
        ),
        CheckConstraint(
            (
                "status <> 'revoked' OR ("
                "revoked_at IS NOT NULL "
                "AND NULLIF(BTRIM(revoke_reason), '') IS NOT NULL)"
            ),
            name="ck_host_publish_entitlements_revoked_requirements",
        ),
        Index("ix_host_publish_entitlements_host_user_id", "host_user_id"),
        Index("ix_host_publish_entitlements_status", "status"),
        Index(
            "ix_host_publish_entitlements_host_status",
            "host_user_id",
            "status",
        ),
        Index(
            "ix_host_publish_entitlements_reserved_by_attempt_id",
            "reserved_by_attempt_id",
        ),
        Index(
            "ix_host_publish_entitlements_used_by_game_id",
            "used_by_game_id",
        ),
        Index(
            "ix_host_publish_entitlements_used_by_fee_id",
            "used_by_host_publish_fee_id",
        ),
        Index(
            "ux_host_publish_entitlements_one_first_free_per_host",
            "host_user_id",
            unique=True,
            postgresql_where=text("entitlement_type = 'first_free'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    host_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    entitlement_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    source_admin_action_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admin_actions.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_financial_outcome_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    reserved_by_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("community_publish_attempts.id", ondelete="SET NULL"),
        nullable=True,
    )
    used_by_game_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("games.id", ondelete="SET NULL"),
        nullable=True,
    )
    used_by_host_publish_fee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("host_publish_fees.id", ondelete="SET NULL"),
        nullable=True,
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    revoke_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
