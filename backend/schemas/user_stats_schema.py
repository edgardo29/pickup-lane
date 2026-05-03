from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


# UserStatsCreate defines the fields allowed when creating cached user profile
# stats for one user.
class UserStatsCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    user_id: UUID
    games_played_count: int = 0
    games_hosted_completed_count: int = 0
    no_show_count: int = 0
    late_cancel_count: int = 0
    host_cancel_count: int = 0
    last_calculated_at: datetime | None = None


# UserStatsRead defines the cached user stats payload returned by the API.
class UserStatsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    games_played_count: int
    games_hosted_completed_count: int
    no_show_count: int
    late_cancel_count: int
    host_cancel_count: int
    last_calculated_at: datetime


# UserStatsUpdate supports partial cached-stat updates, so every field is
# optional and only provided values should be applied by the route.
class UserStatsUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    games_played_count: int | None = None
    games_hosted_completed_count: int | None = None
    no_show_count: int | None = None
    late_cancel_count: int | None = None
    host_cancel_count: int | None = None
    last_calculated_at: datetime | None = None