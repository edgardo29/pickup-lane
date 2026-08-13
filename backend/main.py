from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Response, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import MutableHeaders
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from backend.database import check_database_connection, dispose_database_engine
from backend.observability.http_contracts import RouteMatch, private_route_matches
from backend.observability.http_errors import (
    CorrelationIdMiddleware,
    register_exception_handlers,
)
from backend.observability.openapi_contracts import (
    install_openapi_contracts,
    mark_tombstone_routes_deprecated,
)
from backend.observability.request_body_limits import (
    PLATFORM_NOTICE_CREATE_PATH,
    RequestBodyLimitMiddleware,
    RequestBodyLimitRoute,
)
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
PRIVATE_NO_STORE_CACHE_CONTROL = "private, no-store"
API_REFERRER_POLICY = "no-referrer"
CONTENT_TYPE_OPTIONS = "nosniff"
DOCUMENTATION_FRAME_ANCESTORS = "frame-ancestors 'none'"
DOCUMENTATION_FRAME_OPTIONS = "DENY"
DOCUMENTATION_PERMISSIONS_POLICY = (
    "accelerometer=(), ambient-light-sensor=(), autoplay=(), camera=(), "
    "display-capture=(), encrypted-media=(), fullscreen=(), geolocation=(), "
    "gyroscope=(), magnetometer=(), microphone=(), midi=(), payment=(), "
    "usb=(), xr-spatial-tracking=()"
)
DOCUMENTATION_PATHS = ("/docs", "/redoc")
OPENAPI_SCHEMA_PATH = "/openapi.json"
HEALTH_PATHS = frozenset({"/live", "/ready", "/db-health"})
BODYLESS_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
SPECIAL_BODY_ROUTE_KEYS = frozenset({("POST", PLATFORM_NOTICE_CREATE_PATH)})
APPLICATION_CORS_ALLOWED_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")
APPLICATION_CORS_ALLOWED_HEADERS = (
    "Accept",
    "Authorization",
    "Content-Type",
    "X-Request-ID",
)


class ResponseSecurityHeadersMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        private_routes: tuple[RouteMatch, ...] = (),
    ) -> None:
        self.app = app
        self._private_routes = private_routes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = str(scope.get("path") or "")
        method = str(scope.get("method") or "").upper()

        async def send_with_security_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                _apply_response_security_headers(
                    headers,
                    method=method,
                    path=path,
                    private_routes=self._private_routes,
                    status_code=int(message["status"]),
                )
            await send(message)

        await self.app(scope, receive, send_with_security_headers)


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

    register_exception_handlers(app)

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
    mark_tombstone_routes_deprecated(app.routes)
    install_openapi_contracts(app)
    _add_application_middleware(app, backend_settings)
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


def _add_application_middleware(app: FastAPI, backend_settings: BackendSettings) -> None:
    app.add_middleware(
        RequestBodyLimitMiddleware,
        ordinary_json_request_body_limit_bytes=(
            backend_settings.ordinary_json_request_body_limit_bytes
        ),
        ordinary_json_body_routes=_ordinary_json_body_routes(app),
        platform_notice_request_body_limit_bytes=(
            backend_settings.platform_notice_request_body_limit_bytes
        ),
        stripe_webhook_request_body_limit_bytes=(
            backend_settings.stripe_webhook_request_body_limit_bytes
        ),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(backend_settings.cors_allowed_origins),
        allow_credentials=backend_settings.cors_allow_credentials,
        allow_methods=list(APPLICATION_CORS_ALLOWED_METHODS),
        allow_headers=list(APPLICATION_CORS_ALLOWED_HEADERS),
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=list(backend_settings.allowed_hosts),
        www_redirect=False,
    )
    app.add_middleware(
        ResponseSecurityHeadersMiddleware,
        private_routes=private_route_matches(app.routes),
    )
    app.add_middleware(CorrelationIdMiddleware)


def _ordinary_json_body_routes(app: FastAPI) -> tuple[RequestBodyLimitRoute, ...]:
    routes: list[RequestBodyLimitRoute] = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if not route.dependant.body_params:
            continue

        methods = frozenset(
            method
            for method in route.methods
            if method.upper() not in BODYLESS_METHODS
        )
        if not methods or _is_special_body_route(route.path, methods):
            continue

        routes.append(
            RequestBodyLimitRoute(
                path=route.path,
                methods=frozenset(method.upper() for method in methods),
                path_regex=route.path_regex,
            )
        )
    return tuple(routes)


def _is_special_body_route(path: str, methods: frozenset[str]) -> bool:
    return any((method, path) in SPECIAL_BODY_ROUTE_KEYS for method in methods)


def _apply_response_security_headers(
    headers: MutableHeaders,
    *,
    method: str,
    path: str,
    private_routes: tuple[RouteMatch, ...],
    status_code: int,
) -> None:
    if _is_redirect_response(status_code) or _is_static_path(path):
        return

    content_type = headers.get("content-type", "")
    if _is_documentation_html_response(path, content_type):
        _apply_documentation_security_headers(headers)
        return

    cache_control = (
        PRIVATE_NO_STORE_CACHE_CONTROL
        if _matches_private_route(method=method, path=path, private_routes=private_routes)
        else NO_STORE_CACHE_CONTROL
    )
    if _is_fastapi_owned_api_response(
        path=path,
        status_code=status_code,
        content_type=content_type,
    ):
        _apply_api_security_headers(headers, cache_control=cache_control)


def _apply_api_security_headers(
    headers: MutableHeaders,
    *,
    cache_control: str = NO_STORE_CACHE_CONTROL,
) -> None:
    headers.setdefault("X-Content-Type-Options", CONTENT_TYPE_OPTIONS)
    headers.setdefault("Referrer-Policy", API_REFERRER_POLICY)
    headers.setdefault("Cache-Control", cache_control)


def _apply_documentation_security_headers(headers: MutableHeaders) -> None:
    _apply_api_security_headers(headers, cache_control=NO_STORE_CACHE_CONTROL)
    headers.setdefault("Content-Security-Policy", DOCUMENTATION_FRAME_ANCESTORS)
    headers.setdefault("X-Frame-Options", DOCUMENTATION_FRAME_OPTIONS)
    headers.setdefault("Permissions-Policy", DOCUMENTATION_PERMISSIONS_POLICY)


def _is_redirect_response(status_code: int) -> bool:
    return 300 <= status_code < 400


def _is_static_path(path: str) -> bool:
    return path == "/static" or path.startswith("/static/")


def _is_documentation_html_response(path: str, content_type: str) -> bool:
    return (
        any(
            path == docs_path or path.startswith(f"{docs_path}/")
            for docs_path in DOCUMENTATION_PATHS
        )
        and _is_html_response(content_type)
    )


def _is_fastapi_owned_api_response(
    *,
    path: str,
    status_code: int,
    content_type: str,
) -> bool:
    return (
        path in HEALTH_PATHS
        or path == OPENAPI_SCHEMA_PATH
        or status_code == status.HTTP_204_NO_CONTENT
        or status_code >= status.HTTP_400_BAD_REQUEST
        or _is_json_response(content_type)
    )


def _is_json_response(content_type: str) -> bool:
    return content_type.lower().split(";", maxsplit=1)[0].strip() == "application/json"


def _is_html_response(content_type: str) -> bool:
    return content_type.lower().split(";", maxsplit=1)[0].strip() == "text/html"


def _matches_private_route(
    *,
    method: str,
    path: str,
    private_routes: tuple[RouteMatch, ...],
) -> bool:
    return any(route.matches(method=method, path=path) for route in private_routes)


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
