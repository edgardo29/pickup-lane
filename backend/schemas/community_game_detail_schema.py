from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.schemas.community_payment_schema import CommunityPaymentMethodSnapshot

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class CommunityGameDetailCreate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    game_id: UUID
    payment_methods_snapshot: list[CommunityPaymentMethodSnapshot] = Field(
        default_factory=list,
        max_length=2,
    )
    payment_instructions_snapshot: None = None

    @model_validator(mode="after")
    def reject_duplicate_payment_methods(self) -> "CommunityGameDetailCreate":
        method_types = [method.type for method in self.payment_methods_snapshot]
        if len(method_types) != len(set(method_types)):
            raise ValueError("payment_methods_snapshot must not contain duplicate types.")
        return self


class CommunityGameDetailPublicRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    game_id: UUID
    payment_methods_snapshot: list[dict]
    payment_instructions_snapshot: str | None
    payment_text_moderation_status: str
    created_at: datetime
    updated_at: datetime


class CommunityGameDetailHostRead(CommunityGameDetailPublicRead):
    pass


class CommunityGameDetailStaffRead(CommunityGameDetailHostRead):
    payment_text_hidden_at: datetime | None
    payment_text_hidden_by_user_id: UUID | None
    payment_text_hidden_reason: str | None


class CommunityGameDetailUpdate(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    game_id: UUID | None = None
    payment_methods_snapshot: list[CommunityPaymentMethodSnapshot] | None = Field(
        default=None,
        max_length=2,
    )
    payment_instructions_snapshot: None = None

    @model_validator(mode="after")
    def reject_duplicate_payment_methods(self) -> "CommunityGameDetailUpdate":
        if self.payment_methods_snapshot is None:
            return self
        method_types = [method.type for method in self.payment_methods_snapshot]
        if len(method_types) != len(set(method_types)):
            raise ValueError("payment_methods_snapshot must not contain duplicate types.")
        return self


class CommunityGameDetailHostUpsert(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    payment_methods_snapshot: list[CommunityPaymentMethodSnapshot] = Field(
        default_factory=list,
        max_length=2,
    )
    payment_instructions_snapshot: None = None

    @model_validator(mode="after")
    def reject_duplicate_payment_methods(self) -> "CommunityGameDetailHostUpsert":
        method_types = [method.type for method in self.payment_methods_snapshot]
        if len(method_types) != len(set(method_types)):
            raise ValueError("payment_methods_snapshot must not contain duplicate types.")
        return self
