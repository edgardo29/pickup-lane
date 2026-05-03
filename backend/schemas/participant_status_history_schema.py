from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


# ParticipantStatusHistoryCreate defines the fields allowed when recording
# participant or attendance lifecycle audit rows.
class ParticipantStatusHistoryCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    participant_id: UUID
    old_participant_status: str | None = None
    new_participant_status: str
    old_attendance_status: str | None = None
    new_attendance_status: str | None = None
    changed_by_user_id: UUID | None = None
    change_source: str = "system"
    change_reason: str | None = None


# ParticipantStatusHistoryRead defines the participant status history payload
# returned by the API.
class ParticipantStatusHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    participant_id: UUID
    old_participant_status: str | None
    new_participant_status: str
    old_attendance_status: str | None
    new_attendance_status: str | None
    changed_by_user_id: UUID | None
    change_source: str
    change_reason: str | None
    created_at: datetime


# ParticipantStatusHistoryUpdate supports partial audit-row updates, so every
# field is optional and only provided values should be applied by the route.
class ParticipantStatusHistoryUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    participant_id: UUID | None = None
    old_participant_status: str | None = None
    new_participant_status: str | None = None
    old_attendance_status: str | None = None
    new_attendance_status: str | None = None
    changed_by_user_id: UUID | None = None
    change_source: str | None = None
    change_reason: str | None = None