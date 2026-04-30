# Re-export schemas here so route modules can import from one place as the API
# surface grows.
from backend.schemas.user_schema import UserCreate, UserRead, UserUpdate
from backend.schemas.user_settings_schema import (
    UserSettingsCreate,
    UserSettingsRead,
    UserSettingsUpdate,
)

__all__ = [
    "UserCreate",
    "UserRead",
    "UserUpdate",
    "UserSettingsCreate",
    "UserSettingsRead",
    "UserSettingsUpdate",
]
