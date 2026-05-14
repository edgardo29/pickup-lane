from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class CommunityGameDetailCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    game_id: UUID
    payment_methods_snapshot: list[str] = Field(default_factory=list)
    payment_instructions_snapshot: str | None = None
    payment_due_timing_snapshot: str | None = None
    price_note_snapshot: str | None = None
    refund_policy_snapshot: str | None = None
    cancellation_policy_snapshot: str | None = None
    no_show_policy_snapshot: str | None = None
    arrival_expectations_snapshot: str | None = None
    equipment_notes_snapshot: str | None = None
    behavior_rules_snapshot: str | None = None
    player_message_snapshot: str | None = None


class CommunityGameDetailRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    game_id: UUID
    payment_methods_snapshot: list[str]
    payment_instructions_snapshot: str | None
    payment_due_timing_snapshot: str | None
    price_note_snapshot: str | None
    refund_policy_snapshot: str | None
    cancellation_policy_snapshot: str | None
    no_show_policy_snapshot: str | None
    arrival_expectations_snapshot: str | None
    equipment_notes_snapshot: str | None
    behavior_rules_snapshot: str | None
    player_message_snapshot: str | None
    created_at: datetime
    updated_at: datetime


class CommunityGameDetailUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    game_id: UUID | None = None
    payment_methods_snapshot: list[str] | None = None
    payment_instructions_snapshot: str | None = None
    payment_due_timing_snapshot: str | None = None
    price_note_snapshot: str | None = None
    refund_policy_snapshot: str | None = None
    cancellation_policy_snapshot: str | None = None
    no_show_policy_snapshot: str | None = None
    arrival_expectations_snapshot: str | None = None
    equipment_notes_snapshot: str | None = None
    behavior_rules_snapshot: str | None = None
    player_message_snapshot: str | None = None
