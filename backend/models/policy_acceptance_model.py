import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


# Policy acceptances track which versioned policy document a user accepted.
class PolicyAcceptance(Base):
    __tablename__ = "policy_acceptances"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "policy_document_id",
            name="uq_policy_acceptances_user_id_policy_document_id",
        ),
        Index("ix_policy_acceptances_user_id", "user_id"),
        Index("ix_policy_acceptances_policy_document_id", "policy_document_id"),
        Index("ix_policy_acceptances_accepted_at", "accepted_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    policy_document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("policy_documents.id", ondelete="RESTRICT"),
        nullable=False,
    )

    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )