# Re-export routers here so the main FastAPI app can include feature routes
# from one place as the API grows.
from backend.routes.admin_action_routes import router as admin_actions_router
from backend.routes.admin_action_center_routes import (
    router as admin_action_center_router,
)
from backend.routes.admin_rejected_attempt_routes import (
    router as admin_rejected_attempts_router,
)
from backend.routes.admin_lookup_routes import router as admin_lookups_router
from backend.routes.admin_official_game_routes import (
    router as admin_official_games_router,
)
from backend.routes.admin_routes import router as admin_router
from backend.routes.auth_routes import router as auth_router
from backend.routes.booking_policy_acceptance_routes import (
    router as booking_policy_acceptances_router,
)
from backend.routes.booking_routes import router as bookings_router
from backend.routes.booking_status_history_routes import (
    router as booking_status_history_router,
)
from backend.routes.chat_message_routes import router as chat_messages_router
from backend.routes.checkout_routes import router as checkout_router
from backend.routes.community_game_detail_routes import (
    router as community_game_details_router,
)
from backend.routes.community_game_publish_routes import router as community_games_router
from backend.routes.game_chat_routes import router as game_chats_router
from backend.routes.game_credit_routes import admin_router as admin_game_credits_router
from backend.routes.game_credit_routes import router as game_credits_router
from backend.routes.game_image_routes import admin_router as admin_game_images_router
from backend.routes.game_image_routes import router as game_images_router
from backend.routes.game_routes import router as games_router
from backend.routes.game_participant_routes import router as game_participants_router
from backend.routes.game_status_history_routes import (
    router as game_status_history_router,
)
from backend.routes.host_publish_fee_routes import router as host_publish_fees_router
from backend.routes.notification_routes import router as notifications_router
from backend.routes.participant_status_history_routes import (
    router as participant_status_history_router,
)
from backend.routes.payment_event_routes import router as payment_events_router
from backend.routes.payment_routes import router as payments_router
from backend.routes.policy_acceptance_routes import router as policy_acceptances_router
from backend.routes.policy_document_routes import router as policy_documents_router
from backend.routes.refund_routes import router as refunds_router
from backend.routes.stripe_webhook_routes import router as stripe_webhook_router
from backend.routes.sub_post_position_routes import router as sub_post_positions_router
from backend.routes.sub_post_request_routes import router as sub_post_requests_router
from backend.routes.sub_post_request_status_history_routes import (
    router as sub_post_request_status_history_router,
)
from backend.routes.sub_post_routes import router as sub_posts_router
from backend.routes.sub_post_status_history_routes import (
    router as sub_post_status_history_router,
)
from backend.routes.support_flag_routes import router as support_flags_router
from backend.routes.user_payment_method_routes import (
    router as user_payment_method_router,
)
from backend.routes.user_settings_routes import router as user_settings_router
from backend.routes.user_routes import router as users_router
from backend.routes.user_stats_routes import router as user_stats_router
from backend.routes.venue_approval_request_routes import (
    router as venue_approval_requests_router,
)
from backend.routes.venue_image_routes import admin_router as admin_venue_images_router
from backend.routes.venue_image_routes import public_router as venue_images_router
from backend.routes.venue_routes import router as venues_router
from backend.routes.waitlist_entry_routes import router as waitlist_entries_router

__all__ = [
    "admin_actions_router",
    "admin_action_center_router",
    "admin_rejected_attempts_router",
    "admin_game_credits_router",
    "admin_game_images_router",
    "admin_lookups_router",
    "admin_official_games_router",
    "admin_router",
    "admin_venue_images_router",
    "auth_router",
    "bookings_router",
    "booking_policy_acceptances_router",
    "booking_status_history_router",
    "chat_messages_router",
    "checkout_router",
    "community_game_details_router",
    "community_games_router",
    "users_router",
    "user_settings_router",
    "user_stats_router",
    "user_payment_method_router",
    "venues_router",
    "venue_approval_requests_router",
    "venue_images_router",
    "game_chats_router",
    "game_credits_router",
    "game_images_router",
    "games_router",
    "game_participants_router",
    "game_status_history_router",
    "participant_status_history_router",
    "host_publish_fees_router",
    "notifications_router",
    "waitlist_entries_router",
    "payments_router",
    "payment_events_router",
    "policy_documents_router",
    "policy_acceptances_router",
    "refunds_router",
    "stripe_webhook_router",
    "sub_posts_router",
    "sub_post_positions_router",
    "sub_post_requests_router",
    "sub_post_request_status_history_router",
    "sub_post_status_history_router",
    "support_flags_router",
]
