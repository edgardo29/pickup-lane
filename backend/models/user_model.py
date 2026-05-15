import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


# This table stores the app-level user profile that sits alongside Firebase
# authentication. auth_user_id links the Firebase identity to Pickup Lane's
# internal user record.
class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        # These checks enforce the allowed role and account state values at the
        # database level so invalid values cannot be inserted accidentally.
        CheckConstraint(
            "role IN ('player', 'admin', 'moderator')",
            name="ck_users_role",
        ),
        CheckConstraint(
            "account_status IN ('active', 'suspended', 'pending_deletion', 'deleted')",
            name="ck_users_account_status",
        ),
        CheckConstraint(
            (
                "hosting_status IN ("
                "'not_eligible', "
                "'pending_review', "
                "'eligible', "
                "'restricted', "
                "'suspended', "
                "'banned_from_hosting'"
                ")"
            ),
            name="ck_users_hosting_status",
        ),
        # Keep the important identity fields unique so each auth account,
        # contact method, and Stripe customer maps to at most one app user.
        UniqueConstraint("auth_user_id", name="uq_users_auth_user_id"),
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("phone", name="uq_users_phone"),
        UniqueConstraint(
            "stripe_customer_id",
            name="uq_users_stripe_customer_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    auth_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'player'")
    )
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    profile_photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    home_city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    home_state: Mapped[str | None] = mapped_column(String(120), nullable=True)
    account_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'active'")
    )
    hosting_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'not_eligible'")
    )
    hosting_suspended_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    # deleted_at keeps the internal user row available for historical records
    # while marking the account as removed.
    member_since: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
