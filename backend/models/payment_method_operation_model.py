import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database_metadata import Base


class PaymentMethodOperation(Base):
    __tablename__ = "payment_method_operations"
    __table_args__ = (
        CheckConstraint(
            "operation_kind IN ('setup_create', 'sync', 'set_default', 'detach', 'clear_default')",
            name="ck_payment_method_operations_kind",
        ),
        CheckConstraint(
            "status IN ('pending', 'provider_unknown', 'succeeded', 'failed')",
            name="ck_payment_method_operations_status",
        ),
        Index(
            "ix_payment_method_operations_user_created",
            "user_id",
            "created_at",
            "id",
        ),
        Index(
            "uq_payment_method_operations_fingerprint",
            "user_id",
            "operation_kind",
            "request_fingerprint",
            unique=True,
        ),
        Index(
            "uq_payment_method_operations_idempotency",
            "provider_idempotency_key",
            unique=True,
        ),
        Index(
            "uq_payment_method_operations_active_user",
            "user_id",
            unique=True,
            postgresql_where=text("status IN ('pending', 'provider_unknown')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    payment_method_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user_payment_methods.id", ondelete="SET NULL"),
        nullable=True,
    )
    operation_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'pending'")
    )
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_object_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
