from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class VenueImageUploadCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    file_name: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=120)
    size_bytes: int = Field(gt=0)
    image_role: str = "gallery"
    is_primary: bool = False
    sort_order: int = Field(default=0, ge=0)
    alt_text: str | None = Field(default=None, max_length=280)
    caption: str | None = Field(default=None, max_length=280)


class VenueImageCompleteUpload(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    etag: str | None = Field(default=None, max_length=255)


class VenueImageUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    image_role: str | None = None
    image_status: str | None = None
    is_primary: bool | None = None
    sort_order: int | None = Field(default=None, ge=0)
    alt_text: str | None = Field(default=None, max_length=280)
    caption: str | None = Field(default=None, max_length=280)


class VenueImageRead(BaseModel):
    id: UUID
    venue_id: UUID
    uploaded_by_user_id: UUID | None
    image_url: str
    blob_name: str
    container_name: str
    storage_account_name: str
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


class VenueImageUploadRead(BaseModel):
    image: VenueImageRead
    upload_url: str
    upload_headers: dict[str, str]
    expires_at: datetime
