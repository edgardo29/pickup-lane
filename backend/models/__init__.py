# Re-export models here so Alembic and the rest of the backend can import from
# one place as the models package grows.
from backend.models.user_settings_model import UserSettings
from backend.models.user_model import User

__all__ = ["User", "UserSettings"]
