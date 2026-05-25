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


# This table stores Stripe payment-method references associated with each user.
# It keeps only Stripe IDs and safe card metadata, never raw card numbers, CVC,
# client secrets, or other sensitive payment details.
class UserPaymentMethod(Base):
    __tablename__ = "user_payment_methods"
    __table_args__ = (
        CheckConstraint(
            "method_status IN ('active', 'detached', 'expired')",
            name="ck_user_payment_methods_method_status",
        ),
        CheckConstraint(
            "exp_month BETWEEN 1 AND 12",
            name="ck_user_payment_methods_exp_month",
        ),
        CheckConstraint(
            "char_length(card_last4) = 4",
            name="ck_user_payment_methods_card_last4",
        ),
        CheckConstraint(
            "(is_default = false OR method_status = 'active')",
            name="ck_user_payment_methods_default_requires_active",
        ),
        CheckConstraint(
            "(method_status = 'detached' OR detached_at IS NULL)",
            name="ck_user_payment_methods_detached_at_status",
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
            postgresql_where=text(
                "is_default = true AND method_status = 'active'"
            ),
        ),
        Index(
            "ix_user_payment_methods_user_status",
            "user_id",
            "method_status",
        ),
        Index(
            "ix_user_payment_methods_user_card_fingerprint",
            "user_id",
            "card_fingerprint",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    stripe_customer_id: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    stripe_payment_method_id: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True
    )
    card_fingerprint: Mapped[str] = mapped_column(String(255), nullable=False)
    card_brand: Mapped[str] = mapped_column(String(50), nullable=False)
    card_last4: Mapped[str] = mapped_column(String(4), nullable=False)
    exp_month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    exp_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    method_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'active'")
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    detached_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
