from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class SubPostRequestCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    sub_post_position_id: UUID


class SubPostRequestAction(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    reason: str | None = None


class SubPostRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sub_post_id: UUID
    sub_post_position_id: UUID
    requester_user_id: UUID
    request_status: str
    accepted_at: datetime | None
    confirmed_at: datetime | None
    declined_at: datetime | None
    sub_waitlisted_at: datetime | None
    canceled_at: datetime | None
    expired_at: datetime | None
    no_show_reported_at: datetime | None
    confirmation_due_at: datetime | None
    created_at: datetime
    updated_at: datetime
