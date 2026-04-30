# Re-export routers here so the main FastAPI app can include feature routes
# from one place as the API grows.
from backend.routes.user_payment_method_routes import (
    router as user_payment_method_router,
)
from backend.routes.user_settings_routes import router as user_settings_router
from backend.routes.user_routes import router as users_router
from backend.routes.venue_routes import router as venues_router

__all__ = [
    "users_router",
    "user_settings_router",
    "user_payment_method_router",
    "venues_router",
]
