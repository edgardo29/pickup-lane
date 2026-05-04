from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


# GameImageCreate defines the fields allowed when attaching an image to a game.
class GameImageCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    game_id: UUID
    uploaded_by_user_id: UUID | None = None
    image_url: str
    image_role: str = "gallery"
    image_status: str = "active"
    is_primary: bool = False
    sort_order: int = 0


# GameImageRead defines the game image payload returned by the API.
class GameImageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    game_id: UUID
    uploaded_by_user_id: UUID | None
    image_url: str
    image_role: str
    image_status: str
    is_primary: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


# GameImageUpdate supports partial image metadata updates.
class GameImageUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    uploaded_by_user_id: UUID | None = None
    image_url: str | None = None
    image_role: str | None = None
    image_status: str | None = None
    is_primary: bool | None = None
    sort_order: int | None = None
    deleted_at: datetime | None = None