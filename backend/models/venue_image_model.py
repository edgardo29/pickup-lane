import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.database_metadata import Base


# Venue images store reusable official venue media in Cloudflare R2.
class VenueImage(Base):
    __tablename__ = "venue_images"
    __table_args__ = (
        CheckConstraint(
            "image_role IN ('card', 'gallery')",
            name="ck_venue_images_image_role",
        ),
        CheckConstraint(
            "image_status IN ('pending_upload', 'active', 'hidden', 'removed')",
            name="ck_venue_images_image_status",
        ),
        CheckConstraint(
            (
                "image_status <> 'pending_upload' OR "
                "(upload_expires_at IS NOT NULL AND upload_completed_at IS NULL)"
            ),
            name="ck_venue_images_pending_upload_intent",
        ),
        CheckConstraint(
            "char_length(btrim(storage_provider)) > 0",
            name="ck_venue_images_storage_provider_not_empty",
        ),
        CheckConstraint(
            "char_length(btrim(storage_object_key)) > 0",
            name="ck_venue_images_storage_object_key_not_empty",
        ),
        CheckConstraint(
            "char_length(btrim(storage_bucket)) > 0",
            name="ck_venue_images_storage_bucket_not_empty",
        ),
        CheckConstraint(
            "char_length(btrim(storage_account_id)) > 0",
            name="ck_venue_images_storage_account_id_not_empty",
        ),
        CheckConstraint(
            "char_length(btrim(content_type)) > 0",
            name="ck_venue_images_content_type_not_empty",
        ),
        CheckConstraint(
            "size_bytes > 0",
            name="ck_venue_images_size_bytes_positive",
        ),
        CheckConstraint(
            "((publication_object_key IS NULL AND publication_content_type IS NULL "
            "AND publication_size_bytes IS NULL AND publication_etag IS NULL "
            "AND upload_completed_at IS NULL) OR "
            "(publication_object_key IS NOT NULL AND publication_content_type IS NOT NULL "
            "AND publication_size_bytes IS NOT NULL AND publication_etag IS NOT NULL "
            "AND upload_completed_at IS NOT NULL))",
            name="ck_venue_images_publication_tuple_complete",
        ),
        CheckConstraint(
            "((image_status = 'pending_upload' AND publication_object_key IS NULL) OR "
            "(image_status IN ('active', 'hidden') AND publication_object_key IS NOT NULL) OR "
            "image_status = 'removed')",
            name="ck_venue_images_publication_status",
        ),
        CheckConstraint(
            "publication_content_type IS NULL OR publication_content_type IN "
            "('image/jpeg', 'image/png', 'image/webp')",
            name="ck_venue_images_publication_content_type",
        ),
        CheckConstraint(
            "publication_size_bytes IS NULL OR "
            "publication_size_bytes BETWEEN 1 AND 8388608",
            name="ck_venue_images_publication_size_bytes",
        ),
        CheckConstraint(
            "publication_object_key IS NULL OR "
            "char_length(btrim(publication_object_key)) > 0",
            name="ck_venue_images_publication_object_key_not_empty",
        ),
        CheckConstraint(
            "publication_etag IS NULL OR char_length(btrim(publication_etag)) > 0",
            name="ck_venue_images_publication_etag_not_empty",
        ),
        CheckConstraint(
            "sort_order >= 0",
            name="ck_venue_images_sort_order_non_negative",
        ),
        Index("ix_venue_images_venue_id", "venue_id"),
        Index("ix_venue_images_uploaded_by_user_id", "uploaded_by_user_id"),
        Index("ix_venue_images_image_status", "image_status"),
        Index("ix_venue_images_sort_order", "sort_order"),
        Index(
            "ix_venue_images_venue_id_image_status_sort_order",
            "venue_id",
            "image_status",
            "sort_order",
        ),
        Index(
            "uq_venue_images_storage_object_key",
            "storage_object_key",
            unique=True,
        ),
        Index(
            "uq_venue_images_publication_object_key",
            "publication_object_key",
            unique=True,
            postgresql_where=text("publication_object_key IS NOT NULL"),
        ),
        Index(
            "uq_venue_images_one_active_primary_per_venue",
            "venue_id",
            unique=True,
            postgresql_where=text(
                "is_primary = true AND image_status = 'active' AND deleted_at IS NULL"
            ),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)

    venue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("venues.id", ondelete="CASCADE"),
        nullable=False,
    )

    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    storage_provider: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'r2'")
    )
    storage_object_key: Mapped[str] = mapped_column(Text, nullable=False)
    storage_bucket: Mapped[str] = mapped_column(String(120), nullable=False)
    storage_account_id: Mapped[str] = mapped_column(String(120), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    etag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    publication_object_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    publication_content_type: Mapped[str | None] = mapped_column(
        String(120), nullable=True
    )
    publication_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    publication_etag: Mapped[str | None] = mapped_column(String(255), nullable=True)

    image_role: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'gallery'")
    )
    image_status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'pending_upload'")
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )

    alt_text: Mapped[str | None] = mapped_column(String(280), nullable=True)
    caption: Mapped[str | None] = mapped_column(String(280), nullable=True)

    upload_requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    upload_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    upload_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
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
