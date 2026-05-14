import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


# Host profiles store one reusable host setup/defaults row per user.
class HostProfile(Base):
    __tablename__ = "host_profiles"
    __table_args__ = (
        CheckConstraint(
            "jsonb_typeof(default_payment_methods) = 'array'",
            name="ck_host_profiles_default_payment_methods_array",
        ),
        CheckConstraint(
            (
                "default_payment_due_timing IS NULL OR "
                "default_payment_due_timing IN ("
                "'before_game', 'at_arrival', 'after_confirmation', 'custom'"
                ")"
            ),
            name="ck_host_profiles_default_payment_due_timing",
        ),
        CheckConstraint(
            "(phone_verified_at IS NULL OR phone_number_e164 IS NOT NULL)",
            name="ck_host_profiles_phone_verified_requires_phone",
        ),
        CheckConstraint(
            "(host_rules_accepted_at IS NULL OR host_rules_version IS NOT NULL)",
            name="ck_host_profiles_rules_acceptance_requires_version",
        ),
        CheckConstraint(
            (
                "host_setup_completed_at IS NULL OR ("
                "phone_verified_at IS NOT NULL "
                "AND host_rules_accepted_at IS NOT NULL "
                "AND host_age_confirmed_at IS NOT NULL)"
            ),
            name="ck_host_profiles_setup_completion_requirements",
        ),
        UniqueConstraint("user_id", name="uq_host_profiles_user_id"),
        UniqueConstraint(
            "phone_number_e164", name="uq_host_profiles_phone_number_e164"
        ),
        Index("ix_host_profiles_user_id", "user_id"),
        Index("ix_host_profiles_host_setup_completed_at", "host_setup_completed_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    phone_number_e164: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )
    phone_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    host_rules_accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    host_rules_version: Mapped[str | None] = mapped_column(String(30), nullable=True)
    host_setup_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    host_age_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    default_payment_methods: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    default_payment_instructions: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    default_payment_due_timing: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )
    default_refund_policy: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_game_rules: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_arrival_expectations: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    default_equipment_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_behavior_rules: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_no_show_policy: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_player_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_free_game_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
