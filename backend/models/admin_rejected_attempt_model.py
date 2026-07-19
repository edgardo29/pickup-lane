import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class AdminRejectedAttempt(Base):
    __tablename__ = "admin_rejected_attempts"
    __table_args__ = (
        CheckConstraint(
            (
                "attempt_type IN ("
                "'issue_credit_rejected', "
                "'reverse_credit_rejected', "
                "'suspend_user_rejected', "
                "'delete_user_rejected'"
                ")"
            ),
            name="ck_admin_rejected_attempts_attempt_type",
        ),
        CheckConstraint(
            "rejection_mode IN ('domain_rejected_postload')",
            name="ck_admin_rejected_attempts_rejection_mode",
        ),
        CheckConstraint(
            "response_status_code BETWEEN 400 AND 599",
            name="ck_admin_rejected_attempts_response_status_code",
        ),
        Index("ix_admin_rejected_attempts_admin_user_id", "admin_user_id"),
        Index("ix_admin_rejected_attempts_attempt_type", "attempt_type"),
        Index("ix_admin_rejected_attempts_rejection_mode", "rejection_mode"),
        Index("ix_admin_rejected_attempts_created_at", "created_at"),
        Index("ix_admin_rejected_attempts_target_user_id", "target_user_id"),
        Index("ix_admin_rejected_attempts_target_game_credit_id", "target_game_credit_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    admin_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    attempt_type: Mapped[str] = mapped_column(String(80), nullable=False)
    rejection_mode: Mapped[str] = mapped_column(String(40), nullable=False)
    response_status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    route_method: Mapped[str] = mapped_column(String(10), nullable=False)
    route_path: Mapped[str] = mapped_column(String(240), nullable=False)
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_game_credit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("game_credits.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )
