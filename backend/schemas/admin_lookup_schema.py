from uuid import UUID

from pydantic import BaseModel


class AdminLookupUserRead(BaseModel):
    id: UUID
    display_name: str
    email: str | None = None
    eligible: bool = False


class AdminLookupUserListRead(BaseModel):
    results: list[AdminLookupUserRead]
