from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AdminActionCenterItemRead(BaseModel):
    item_id: str
    item_type: str
    section_key: str
    source: str
    severity: str
    status: str
    title: str
    summary: str
    entity_type: str
    entity_id: UUID
    entity_label: str
    related_entity_type: str | None = None
    related_entity_id: UUID | None = None
    related_entity_label: str | None = None
    detected_at: datetime
    due_at: datetime | None = None
    action_label: str
    action_path: str
    metadata: dict[str, str | int | bool | None] = Field(default_factory=dict)


class AdminActionCenterSectionRead(BaseModel):
    section_key: str
    label: str
    items: list[AdminActionCenterItemRead] = Field(default_factory=list)


class AdminActionCenterRead(BaseModel):
    generated_at: datetime
    total_count: int
    sections: list[AdminActionCenterSectionRead] = Field(default_factory=list)
