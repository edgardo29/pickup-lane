from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AdminRejectedAttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    admin_user_id: UUID | None
    attempt_type: str
    rejection_mode: str
    response_status_code: int
    route_method: str
    route_path: str
    target_user_id: UUID | None
    target_game_credit_id: UUID | None
    metadata: dict[str, Any] | None = Field(
        validation_alias="metadata_",
        serialization_alias="metadata",
    )
    created_at: datetime
