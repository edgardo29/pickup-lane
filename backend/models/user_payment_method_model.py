import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


# This table stores the payment-method references associated with each user.
# It keeps only provider reference data and safe card metadata, not raw card
# details or sensitive payment secrets.
class UserPaymentMethod(Base):
    __tablename__ = "user_payment_methods"
    __table_args__ = (
        # Restrict provider and card metadata values to supported, valid ranges
        # so bad payment-method state cannot be stored accidentally.
        CheckConstraint(
            "provider IN ('stripe')",
            name="ck_user_payment_methods_provider",
        ),
        CheckConstraint(
            "(exp_month IS NULL OR exp_month BETWEEN 1 AND 12)",
            name="ck_user_payment_methods_exp_month",
        ),
        CheckConstraint(
            "(card_last4 IS NULL OR char_length(card_last4) = 4)",
            name="ck_user_payment_methods_card_last4",
        ),
        # Each user may have many payment methods, but only one active default
        # payment method at a time.
        Index(
            "ix_user_payment_methods_user_id",
            "user_id",
        ),
        Index(
            "ix_user_payment_methods_one_active_default_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("is_default = true AND is_active = true"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'stripe'")
    )
    provider_payment_method_id: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True
    )
    card_brand: Mapped[str | None] = mapped_column(String(50), nullable=True)
    card_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    exp_month: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    exp_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
