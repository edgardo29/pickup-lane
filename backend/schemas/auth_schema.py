from pydantic import BaseModel, ConfigDict

REQUEST_MODEL_CONFIG = ConfigDict(extra="forbid")


class AuthSyncUserRequest(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    auth_user_id: str
    email: str


class AuthDeleteAccountRequest(BaseModel):
    model_config = REQUEST_MODEL_CONFIG

    confirmation: str


class AuthEmailAvailabilityRead(BaseModel):
    email: str
    available: bool
