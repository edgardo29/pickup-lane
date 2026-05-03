from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


# GameStatusHistoryCreate defines the fields allowed when recording a game
# publish/status lifecycle audit row.
class GameStatusHistoryCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    game_id: UUID
    old_publish_status: str | None = None
    new_publish_status: str
    old_game_status: str | None = None
    new_game_status: str
    changed_by_user_id: UUID | None = None
    change_source: str = "user"
    change_reason: str | None = None


# GameStatusHistoryRead defines the game status history payload returned by
# the API.
class GameStatusHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    game_id: UUID
    old_publish_status: str | None
    new_publish_status: str
    old_game_status: str | None
    new_game_status: str
    changed_by_user_id: UUID | None
    change_source: str
    change_reason: str | None
    created_at: datetime


# GameStatusHistoryUpdate supports partial audit-row updates, so every field is
# optional and only provided values should be applied by the route.
class GameStatusHistoryUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    game_id: UUID | None = None
    old_publish_status: str | None = None
    new_publish_status: str | None = None
    old_game_status: str | None = None
    new_game_status: str | None = None
    changed_by_user_id: UUID | None = None
    change_source: str | None = None
    change_reason: str | None = None
