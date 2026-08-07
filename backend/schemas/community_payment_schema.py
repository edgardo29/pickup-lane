from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")
CommunityPaymentMethodType = Literal[
    "venmo",
    "zelle",
    "cash_app",
    "paypal",
    "apple_cash",
    "cash",
    "other",
]


class CommunityPaymentMethodSnapshot(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    type: CommunityPaymentMethodType
    value: StrictStr = Field(min_length=1, max_length=255)

    @field_validator("value", mode="before")
    @classmethod
    def trim_value(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value
