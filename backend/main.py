import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.database import check_database_connection
from backend.routes import (
    admin_actions_router,
    auth_router,
    booking_policy_acceptances_router,
    booking_status_history_router,
    bookings_router,
    chat_messages_router,
    community_game_details_router,
    game_chats_router,
    game_images_router,
    games_router,
    game_participants_router,
    game_status_history_router,
    host_profiles_router,
    host_publish_fees_router,
    notifications_router,
    participant_status_history_router,
    payment_events_router,
    payments_router,
    policy_acceptances_router,
    policy_documents_router,
    refunds_router,
    sub_post_positions_router,
    sub_post_request_status_history_router,
    sub_post_requests_router,
    sub_post_status_history_router,
    sub_posts_router,
    user_payment_method_router,
    user_settings_router,
    user_stats_router,
    users_router,
    venue_approval_requests_router,
    venues_router,
    waitlist_entries_router,
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DEFAULT_CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


def get_cors_origins() -> list[str]:
    configured_origins = os.getenv("CORS_ALLOWED_ORIGINS")
    if not configured_origins:
        return DEFAULT_CORS_ORIGINS

    return [
        origin.strip().rstrip("/")
        for origin in configured_origins.split(",")
        if origin.strip()
    ]

app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Backend is running"}


@app.get("/db-health")
def db_health():
    check_database_connection()
    return {"message": "Database connection is working"}


# Include feature-specific routers here so the main app stays small as the API
# surface grows.
app.include_router(users_router)
app.include_router(auth_router)
app.include_router(user_settings_router)
app.include_router(user_stats_router)
app.include_router(user_payment_method_router)
app.include_router(venues_router)
app.include_router(venue_approval_requests_router)
app.include_router(game_chats_router)
app.include_router(game_images_router)
app.include_router(chat_messages_router)
app.include_router(community_game_details_router)
app.include_router(games_router)
app.include_router(bookings_router)
app.include_router(booking_status_history_router)
app.include_router(booking_policy_acceptances_router)
app.include_router(game_participants_router)
app.include_router(game_status_history_router)
app.include_router(participant_status_history_router)
app.include_router(host_profiles_router)
app.include_router(host_publish_fees_router)
app.include_router(notifications_router)
app.include_router(admin_actions_router)
app.include_router(waitlist_entries_router)
app.include_router(payments_router)
app.include_router(payment_events_router)
app.include_router(policy_documents_router)
app.include_router(policy_acceptances_router)
app.include_router(refunds_router)
app.include_router(sub_posts_router)
app.include_router(sub_post_positions_router)
app.include_router(sub_post_requests_router)
app.include_router(sub_post_request_status_history_router)
app.include_router(sub_post_status_history_router)
