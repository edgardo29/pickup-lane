import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


# This table stores per-user app preferences that extend the core users table
# without crowding the main user profile record.
class UserSettings(Base):
    __tablename__ = "user_settings"
    __table_args__ = (
        # Restrict location permission status to the supported values used by
        # the application so bad state cannot be stored accidentally.
        CheckConstraint(
            (
                "location_permission_status IN ("
                "'unknown', "
                "'allowed', "
                "'denied', "
                "'skipped'"
                ")"
            ),
            name="ck_user_settings_location_permission_status",
        ),
    )

    # user_id is both the primary key and foreign key because this is a strict
    # one-to-one extension of the users table.
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    push_notifications_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    email_notifications_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    sms_notifications_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    marketing_opt_in: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    location_permission_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'unknown'")
    )
    selected_city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    selected_state: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
