from pydantic import BaseModel, ConfigDict, Field, field_validator

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class AuthSyncUserRequest(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    auth_user_id: str
    email: str
    email_verified: bool = False


class AuthDeleteAccountRequest(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    confirmation: str = Field(min_length=1)

    @field_validator("confirmation")
    @classmethod
    def require_delete_confirmation(cls, value: str) -> str:
        stripped = value.strip()
        if stripped.upper() != "DELETE":
            raise ValueError("confirmation must be DELETE.")
        return stripped


class AuthEmailAvailabilityRead(BaseModel):
    email: str
    available: bool
