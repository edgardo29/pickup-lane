from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Response, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.database import check_database_connection, dispose_database_engine
from backend.routes import (
    admin_actions_router,
    admin_rejected_attempts_router,
    admin_review_cases_router,
    admin_community_games_router,
    admin_game_credits_router,
    admin_game_images_router,
    admin_lookups_router,
    admin_money_router,
    admin_need_a_sub_router,
    admin_notifications_router,
    admin_official_games_router,
    admin_router,
    admin_users_router,
    admin_venue_images_router,
    auth_router,
    booking_policy_acceptances_router,
    booking_status_history_router,
    bookings_router,
    chat_messages_router,
    checkout_router,
    community_game_details_router,
    community_games_router,
    game_chats_router,
    game_credits_router,
    game_images_router,
    games_router,
    game_participants_router,
    game_status_history_router,
    host_publish_fees_router,
    inbox_router,
    my_games_router,
    notifications_router,
    participant_status_history_router,
    payment_events_router,
    payments_router,
    policy_acceptances_router,
    policy_documents_router,
    platform_notices_router,
    refunds_router,
    stripe_webhook_router,
    sub_post_positions_router,
    sub_post_request_status_history_router,
    sub_post_requests_router,
    sub_post_status_history_router,
    sub_posts_router,
    support_flags_router,
    user_payment_method_router,
    user_settings_router,
    user_stats_router,
    users_router,
    venue_approval_requests_router,
    venue_images_router,
    venues_router,
    waitlist_entries_router,
)
from backend.settings import BackendSettings, get_settings

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
NO_STORE_CACHE_CONTROL = "no-store"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.lifecycle_started = True
    try:
        yield
    finally:
        app.state.lifecycle_started = False
        dispose_database_engine()


def create_app(settings: BackendSettings | None = None) -> FastAPI:
    backend_settings = settings or get_settings()
    api_docs_enabled = backend_settings.enable_api_docs

    app = FastAPI(
        docs_url="/docs" if api_docs_enabled else None,
        redoc_url="/redoc" if api_docs_enabled else None,
        openapi_url="/openapi.json" if api_docs_enabled else None,
        lifespan=lifespan,
    )
    app.state.lifecycle_started = False
    app.state.release_identity = backend_settings.release_identity
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(backend_settings.cors_allowed_origins),
        allow_credentials=backend_settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    def read_root():
        return {"message": "Backend is running"}

    @app.get("/live")
    def live():
        if not _lifecycle_started(app):
            return _health_response(
                app,
                "not_live",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return _health_response(app, "live")

    @app.get("/ready")
    def ready():
        if not _lifecycle_started(app):
            return _health_response(
                app,
                "not_ready",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if not _database_ready():
            return _health_response(
                app,
                "not_ready",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return _health_response(app, "ready")

    if backend_settings.enable_db_health:

        @app.get("/db-health")
        def db_health(response: Response):
            response.headers["Cache-Control"] = NO_STORE_CACHE_CONTROL
            if not _database_ready():
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    headers={"Cache-Control": NO_STORE_CACHE_CONTROL},
                    content={"message": "Database connection is unavailable"},
                )
            return {"message": "Database connection is working"}

    _include_routers(app)
    return app


def _lifecycle_started(app: FastAPI) -> bool:
    return bool(getattr(app.state, "lifecycle_started", False))


def _database_ready() -> bool:
    try:
        check_database_connection()
    except Exception:  # noqa: BLE001 - health probes must not expose diagnostics.
        return False
    return True


def _health_response(
    app: FastAPI,
    health_status: str,
    *,
    status_code: int = status.HTTP_200_OK,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        headers={"Cache-Control": NO_STORE_CACHE_CONTROL},
        content={
            "status": health_status,
            "release": getattr(app.state, "release_identity", "source-unavailable"),
        },
    )


def _include_routers(app: FastAPI) -> None:
    # Include feature-specific routers here so the main app stays small as the API
    # surface grows.
    app.include_router(users_router)
    app.include_router(auth_router)
    app.include_router(user_settings_router)
    app.include_router(user_stats_router)
    app.include_router(user_payment_method_router)
    app.include_router(venues_router)
    app.include_router(venue_approval_requests_router)
    app.include_router(venue_images_router)
    app.include_router(game_chats_router)
    app.include_router(game_credits_router)
    app.include_router(admin_router)
    app.include_router(admin_users_router)
    app.include_router(admin_community_games_router)
    app.include_router(admin_rejected_attempts_router)
    app.include_router(admin_review_cases_router)
    app.include_router(admin_game_credits_router)
    app.include_router(admin_game_images_router)
    app.include_router(admin_lookups_router)
    app.include_router(admin_money_router)
    app.include_router(admin_need_a_sub_router)
    app.include_router(admin_notifications_router)
    app.include_router(admin_official_games_router)
    app.include_router(admin_venue_images_router)
    app.include_router(game_images_router)
    app.include_router(chat_messages_router)
    app.include_router(checkout_router)
    app.include_router(community_game_details_router)
    app.include_router(community_games_router)
    app.include_router(games_router)
    app.include_router(bookings_router)
    app.include_router(booking_status_history_router)
    app.include_router(booking_policy_acceptances_router)
    app.include_router(game_participants_router)
    app.include_router(game_status_history_router)
    app.include_router(participant_status_history_router)
    app.include_router(host_publish_fees_router)
    app.include_router(inbox_router)
    app.include_router(my_games_router)
    app.include_router(notifications_router)
    app.include_router(admin_actions_router)
    app.include_router(waitlist_entries_router)
    app.include_router(payments_router)
    app.include_router(payment_events_router)
    app.include_router(policy_documents_router)
    app.include_router(policy_acceptances_router)
    app.include_router(platform_notices_router)
    app.include_router(refunds_router)
    app.include_router(stripe_webhook_router)
    app.include_router(sub_posts_router)
    app.include_router(sub_post_positions_router)
    app.include_router(sub_post_requests_router)
    app.include_router(sub_post_request_status_history_router)
    app.include_router(sub_post_status_history_router)
    app.include_router(support_flags_router)


app = create_app()
