from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AdminMeRead(BaseModel):
    user_id: UUID
    role: str
    account_status: str
    permissions: list[str]
    data_scopes: list[str]
    role_updated_at: datetime | None
