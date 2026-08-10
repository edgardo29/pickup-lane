from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")
VenueImageRole = Literal["card", "gallery"]
VenueImageStatus = Literal["pending_upload", "active", "hidden", "removed"]


class VenueImageUploadCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    file_name: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=120)
    size_bytes: int = Field(gt=0)
    image_role: VenueImageRole = "gallery"
    is_primary: bool = False
    sort_order: int = Field(default=0, ge=0, le=2)
    alt_text: str | None = Field(default=None, max_length=280)
    caption: str | None = Field(default=None, max_length=280)


class VenueImageCompleteUpload(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    etag: str | None = Field(default=None, max_length=255)


class VenueImageUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    image_role: VenueImageRole | None = None
    image_status: VenueImageStatus | None = None
    is_primary: bool | None = None
    sort_order: int | None = Field(default=None, ge=0, le=2)
    alt_text: str | None = Field(default=None, max_length=280)
    caption: str | None = Field(default=None, max_length=280)
    reason: str | None = Field(default=None, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def strip_reason(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class VenueImageRead(BaseModel):
    id: UUID
    venue_id: UUID
    uploaded_by_user_id: UUID | None
    image_url: str
    storage_provider: str
    storage_object_key: str
    storage_bucket: str
    storage_account_id: str
    content_type: str
    size_bytes: int
    etag: str | None
    image_role: str
    image_status: str
    is_primary: bool
    sort_order: int
    alt_text: str | None
    caption: str | None
    upload_requested_at: datetime
    upload_completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class VenueImagePublicRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    venue_id: UUID
    image_url: str
    image_role: str
    is_primary: bool
    sort_order: int
    alt_text: str | None
    caption: str | None


class VenueImageAdminRead(VenueImageRead):
    pass


class VenueImageUploadRead(BaseModel):
    image: VenueImageAdminRead
    upload_url: str
    upload_headers: dict[str, str]
    expires_at: datetime
