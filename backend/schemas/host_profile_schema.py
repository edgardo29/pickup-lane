from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class HostProfileCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    user_id: UUID
    phone_number_e164: str | None = None
    phone_verified_at: datetime | None = None
    host_rules_accepted_at: datetime | None = None
    host_rules_version: str | None = None
    host_setup_completed_at: datetime | None = None
    host_age_confirmed_at: datetime | None = None
    default_payment_methods: list[str] = Field(default_factory=list)
    default_payment_instructions: str | None = None
    default_payment_due_timing: str | None = None
    default_refund_policy: str | None = None
    default_game_rules: str | None = None
    default_arrival_expectations: str | None = None
    default_equipment_notes: str | None = None
    default_behavior_rules: str | None = None
    default_no_show_policy: str | None = None
    default_player_message: str | None = None
    first_free_game_used_at: datetime | None = None


class HostProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    phone_number_e164: str | None
    phone_verified_at: datetime | None
    host_rules_accepted_at: datetime | None
    host_rules_version: str | None
    host_setup_completed_at: datetime | None
    host_age_confirmed_at: datetime | None
    default_payment_methods: list[str]
    default_payment_instructions: str | None
    default_payment_due_timing: str | None
    default_refund_policy: str | None
    default_game_rules: str | None
    default_arrival_expectations: str | None
    default_equipment_notes: str | None
    default_behavior_rules: str | None
    default_no_show_policy: str | None
    default_player_message: str | None
    first_free_game_used_at: datetime | None
    created_at: datetime
    updated_at: datetime


class HostProfileUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    user_id: UUID | None = None
    phone_number_e164: str | None = None
    phone_verified_at: datetime | None = None
    host_rules_accepted_at: datetime | None = None
    host_rules_version: str | None = None
    host_setup_completed_at: datetime | None = None
    host_age_confirmed_at: datetime | None = None
    default_payment_methods: list[str] | None = None
    default_payment_instructions: str | None = None
    default_payment_due_timing: str | None = None
    default_refund_policy: str | None = None
    default_game_rules: str | None = None
    default_arrival_expectations: str | None = None
    default_equipment_notes: str | None = None
    default_behavior_rules: str | None = None
    default_no_show_policy: str | None = None
    default_player_message: str | None = None
    first_free_game_used_at: datetime | None = None
