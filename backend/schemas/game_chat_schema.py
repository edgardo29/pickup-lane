from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


# GameChatCreate defines the fields allowed when creating the room-level chat
# record for one game.
class GameChatCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    game_id: UUID
    chat_status: str = "active"
    locked_at: datetime | None = None


# GameChatRead defines the game chat payload returned by the API.
class GameChatRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    game_id: UUID
    chat_status: str
    created_at: datetime
    updated_at: datetime
    locked_at: datetime | None


# GameChatUpdate supports partial chat updates, so every field is optional and
# only provided values should be applied by the route.
class GameChatUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    game_id: UUID | None = None
    chat_status: str | None = None
    locked_at: datetime | None = None
