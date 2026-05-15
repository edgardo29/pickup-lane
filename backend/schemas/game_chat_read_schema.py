from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class GameChatReadStateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chat_id: UUID
    user_id: UUID
    last_read_at: datetime | None
    last_read_message_id: UUID | None
    unread_count: int

