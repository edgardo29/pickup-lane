# Re-export routers here so the main FastAPI app can include feature routes
# from one place as the API grows.
from backend.routes.booking_routes import router as bookings_router
from backend.routes.game_routes import router as games_router
from backend.routes.game_participant_routes import router as game_participants_router
from backend.routes.payment_routes import router as payments_router
from backend.routes.refund_routes import router as refunds_router
from backend.routes.user_payment_method_routes import (
    router as user_payment_method_router,
)
from backend.routes.user_settings_routes import router as user_settings_router
from backend.routes.user_routes import router as users_router
from backend.routes.venue_routes import router as venues_router
from backend.routes.waitlist_entry_routes import router as waitlist_entries_router

__all__ = [
    "bookings_router",
    "users_router",
    "user_settings_router",
    "user_payment_method_router",
    "venues_router",
    "games_router",
    "game_participants_router",
    "waitlist_entries_router",
    "payments_router",
    "refunds_router",
]
