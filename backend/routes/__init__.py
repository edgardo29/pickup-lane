# Re-export routers here so the main FastAPI app can include feature routes
# from one place as the API grows.
from backend.routes.admin_action_routes import router as admin_actions_router
from backend.routes.auth_routes import router as auth_router
from backend.routes.booking_policy_acceptance_routes import (
    router as booking_policy_acceptances_router,
)
from backend.routes.booking_routes import router as bookings_router
from backend.routes.booking_status_history_routes import (
    router as booking_status_history_router,
)
from backend.routes.chat_message_routes import router as chat_messages_router
from backend.routes.game_chat_routes import router as game_chats_router
from backend.routes.game_image_routes import router as game_images_router
from backend.routes.game_routes import router as games_router
from backend.routes.game_participant_routes import router as game_participants_router
from backend.routes.game_status_history_routes import (
    router as game_status_history_router,
)
from backend.routes.host_deposit_event_routes import router as host_deposit_events_router
from backend.routes.host_deposit_routes import router as host_deposits_router
from backend.routes.notification_routes import router as notifications_router
from backend.routes.participant_status_history_routes import (
    router as participant_status_history_router,
)
from backend.routes.payment_event_routes import router as payment_events_router
from backend.routes.payment_routes import router as payments_router
from backend.routes.policy_acceptance_routes import router as policy_acceptances_router
from backend.routes.policy_document_routes import router as policy_documents_router
from backend.routes.refund_routes import router as refunds_router
from backend.routes.user_payment_method_routes import (
    router as user_payment_method_router,
)
from backend.routes.user_settings_routes import router as user_settings_router
from backend.routes.user_routes import router as users_router
from backend.routes.user_stats_routes import router as user_stats_router
from backend.routes.venue_approval_request_routes import (
    router as venue_approval_requests_router,
)
from backend.routes.venue_routes import router as venues_router
from backend.routes.waitlist_entry_routes import router as waitlist_entries_router

__all__ = [
    "admin_actions_router",
    "auth_router",
    "bookings_router",
    "booking_policy_acceptances_router",
    "booking_status_history_router",
    "chat_messages_router",
    "users_router",
    "user_settings_router",
    "user_stats_router",
    "user_payment_method_router",
    "venues_router",
    "venue_approval_requests_router",
    "game_chats_router",
    "game_images_router",
    "games_router",
    "game_participants_router",
    "game_status_history_router",
    "participant_status_history_router",
    "host_deposits_router",
    "host_deposit_events_router",
    "notifications_router",
    "waitlist_entries_router",
    "payments_router",
    "payment_events_router",
    "policy_documents_router",
    "policy_acceptances_router",
    "refunds_router",
]
