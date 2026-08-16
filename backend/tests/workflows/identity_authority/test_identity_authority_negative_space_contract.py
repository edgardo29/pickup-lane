from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.routing import APIRoute

from backend.schemas.user_schema import UserUpdate

pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.suite_type("ordinary")]

REPO_ROOT = Path(__file__).resolve().parents[4]
BACKEND_ROOT = REPO_ROOT / "backend"
FRONTEND_SRC = REPO_ROOT / "frontend/src"

RELEVANT_ROUTE_PREFIXES = (
    "/admin",
    "/auth",
    "/chat-messages",
    "/checkout",
    "/community-game-details",
    "/community-games",
    "/game-chats",
    "/games",
    "/my-games",
    "/need-a-sub",
    "/user-payment-methods",
    "/users",
)
MUTATION_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
ACTIVE_USER_STATUS_MUTATIONS = {
    ("POST", "/game-chats/{game_chat_id}/read"),
    ("POST", "/need-a-sub/posts/{sub_post_id}/chat/read"),
}
APPROVED_PROFILE_FIELDS = {
    "phone",
    "first_name",
    "last_name",
    "date_of_birth",
    "home_city",
    "home_state",
}
IDENTITY_OWNED_FIELDS = {
    "auth_user_id",
    "email",
    "email_verified",
    "email_verified_at",
    "role",
    "account_status",
    "deleted_at",
    "created_at",
    "updated_at",
    "auth_time",
    "last_login_at",
    "profile_photo_url",
    "permissions",
    "owner_user_id",
    "admin",
    "is_admin",
    "provider_id",
}


def _active_routes() -> list[APIRoute]:
    import backend.main as main

    return [
        route
        for route in main.app.routes
        if isinstance(route, APIRoute)
        and route.path_format.startswith(RELEVANT_ROUTE_PREFIXES)
    ]


def _dependency_call_names(route: APIRoute) -> set[str]:
    names: set[str] = set()

    def walk(dependant) -> None:
        for dependency in dependant.dependencies:
            call = dependency.call
            if call is not None:
                call_name = getattr(call, "__name__", repr(call))
                call_module = getattr(call, "__module__", "")
                names.add(call_name)
                names.add(f"{call_module}.{call_name}")
            walk(dependency)

    walk(route.dependant)
    return names


def _has_dependency(route: APIRoute, dependency_name: str) -> bool:
    return dependency_name in _dependency_call_names(route)


def _route_has_any_auth_dependency(route: APIRoute) -> bool:
    dependency_names = _dependency_call_names(route)
    return any(
        name in dependency_names
        for name in {
            "get_current_app_user",
            "get_optional_current_app_user",
            "get_synced_current_app_user",
            "require_active_user",
            "require_recent_active_user",
            "require_recent_app_user",
            "require_active_admin",
            "require_recent_active_admin",
            "require_verified_user",
        }
    )


def _classify_route(route: APIRoute, method: str) -> str:
    path = route.path_format

    if path.startswith("/admin"):
        assert _has_dependency(route, "require_active_admin") or _has_dependency(
            route, "require_recent_active_admin"
        ), f"{method} {path} bypasses active admin identity dependency"
        return "admin route: current verified active admin dependency"

    if path.startswith("/auth"):
        return "auth bootstrap/account lifecycle route with provider identity boundary"

    if path == "/users/me":
        return "ordinary self profile setup/read route"

    if path == "/users" or path.startswith("/users/{user_id}"):
        assert _has_dependency(route, "require_active_admin"), (
            f"{method} {path} generic/admin user route bypasses active admin"
        )
        return "admin-only user route or disabled generic mutation"

    if path.startswith("/user-payment-methods"):
        return "payment-method/recent-auth later-owner surface"

    if route.status_code == 410:
        return "retired 410 tombstone"

    if (method, path) in ACTIVE_USER_STATUS_MUTATIONS:
        assert _has_dependency(route, "require_active_user"), (
            f"{method} {path} read-state mutation lacks active-user identity"
        )
        return "active-user read-state/status mutation"

    if method == "GET":
        if _has_dependency(route, "require_active_admin"):
            return "active-admin read"
        if _has_dependency(route, "require_active_user"):
            return "active-user read/status/history"
        if _has_dependency(route, "get_optional_current_app_user"):
            return "public or optional-auth read"
        if not _route_has_any_auth_dependency(route):
            return "public read"
        return "authenticated read with explicit dependency"

    if method in MUTATION_METHODS:
        if _has_dependency(route, "require_active_admin") or _has_dependency(
            route, "require_recent_active_admin"
        ):
            return "admin or later-owner privileged mutation"
        if _has_dependency(route, "require_verified_user"):
            return "verified-email-required mutation"

    raise AssertionError(f"Unclassified WS03-01 route candidate: {method} {path}")


@pytest.mark.requirement(
    "WS03-01-R1",
    "WS03-01-R3",
    "WS03-01-R4",
    "WS03-01-R7",
    "WS03-01-R8",
)
def test_ws03_route_inventory_classifies_identity_relevant_routes_and_dependencies() -> None:
    classifications: dict[tuple[str, str], str] = {}

    for route in _active_routes():
        for method in sorted(route.methods or []):
            if method in {"HEAD", "OPTIONS"}:
                continue
            classifications[(method, route.path_format)] = _classify_route(route, method)

    assert classifications
    assert classifications[("POST", "/games/{game_id}/join")] == (
        "verified-email-required mutation"
    )
    assert classifications[
        ("POST", "/checkout/games/{game_id}/payment-intent")
    ] == "verified-email-required mutation"
    assert classifications[("POST", "/community-games/publish")] == (
        "verified-email-required mutation"
    )
    assert classifications[
        ("POST", "/need-a-sub/posts/{sub_post_id}/requests")
    ] == "verified-email-required mutation"
    assert classifications[("POST", "/chat-messages")] == (
        "verified-email-required mutation"
    )
    assert classifications[("GET", "/games/browse")] == "public read"
    assert classifications[("GET", "/my-games")] == "active-user read/status/history"
    assert classifications[("GET", "/admin/me")] == (
        "admin route: current verified active admin dependency"
    )


def _backend_source_files() -> list[Path]:
    excluded_parts = {".venv", "__pycache__"}
    return sorted(
        path
        for path in BACKEND_ROOT.rglob("*.py")
        if "tests" not in path.parts and excluded_parts.isdisjoint(path.parts)
    )


def _frontend_source_files() -> list[Path]:
    return sorted(
        path
        for path in FRONTEND_SRC.rglob("*")
        if path.is_file() and path.suffix in {".js", ".jsx", ".ts", ".tsx"}
    )


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


@pytest.mark.requirement("WS03-01-R1", "WS03-01-R3", "WS03-01-R7", "WS03-01-R8")
def test_backend_source_has_no_direct_token_or_custom_claim_authority_bypasses() -> None:
    direct_verify_offenders: list[str] = []
    decoded_token_offenders: list[str] = []
    custom_claim_offenders: list[str] = []
    allowed_decoded_paths = {
        "backend/firebase_admin_client.py",
        "backend/services/auth_service.py",
    }

    for path in _backend_source_files():
        rel = _relative(path)
        source = path.read_text()
        if "verify_id_token(" in source and rel != "backend/firebase_admin_client.py":
            direct_verify_offenders.append(rel)
        if "decoded_token" in source and rel not in allowed_decoded_paths:
            decoded_token_offenders.append(rel)
        if any(
            term in source
            for term in (
                "custom_claim",
                "customClaims",
                "firebase_claim",
                "claims.get(\"admin\"",
                "claims.get('admin'",
            )
        ):
            custom_claim_offenders.append(rel)

    assert direct_verify_offenders == []
    assert decoded_token_offenders == []
    assert custom_claim_offenders == []


@pytest.mark.requirement("WS03-01-R4", "WS03-01-R5", "WS03-01-R8")
def test_verified_email_authorization_depends_on_provider_identity_not_local_snapshot() -> None:
    source = (BACKEND_ROOT / "services/auth_service.py").read_text()
    require_verified_segment = source[
        source.index("def require_verified_user") :
        source.index("def user_is_active_admin")
    ]

    assert "identity.email_verified" in require_verified_segment
    assert "email_verified_at" not in require_verified_segment


@pytest.mark.requirement("WS03-01-R6", "WS03-01-R8")
def test_ordinary_profile_schema_exposes_no_identity_owned_fields() -> None:
    model_fields = set(UserUpdate.model_fields)

    assert model_fields == APPROVED_PROFILE_FIELDS
    assert model_fields.isdisjoint(IDENTITY_OWNED_FIELDS)


@pytest.mark.requirement("WS03-01-R9")
def test_frontend_source_has_no_manual_bearer_storage_or_generic_replay_bypass() -> None:
    unsafe_storage_lines: list[str] = []
    unsafe_token_placement: list[str] = []
    generic_retry_paths: list[str] = []

    for path in _frontend_source_files():
        rel = _relative(path)
        source = path.read_text()
        for line_number, line in enumerate(source.splitlines(), start=1):
            if any(
                storage_term in line
                for storage_term in ("localStorage", "sessionStorage", "indexedDB")
            ) and any(
                token_term in line
                for token_term in ("idToken", "accessToken", "refreshToken", "Bearer")
            ):
                unsafe_storage_lines.append(f"{rel}:{line_number}")

        if "getIdToken" in source:
            if any(term in source for term in ("id_token=", "access_token=", "?token=")):
                unsafe_token_placement.append(f"{rel}: query token")
            if "FormData" in source and "getIdToken" in source:
                unsafe_token_placement.append(f"{rel}: form token candidate")

        if "error?.status === 401" in source and rel not in {
            "frontend/src/lib/authApi.js",
            "frontend/src/pages/admin/shared/adminApi.js",
            "frontend/src/routes/RouteGuards.jsx",
            "frontend/src/pages/admin/sign-in/useAdminSignInForm.js",
        }:
            generic_retry_paths.append(rel)

    api_client_source = (FRONTEND_SRC / "lib/apiClient.js").read_text()
    assert "getIdToken" not in api_client_source
    assert "forceRefresh" not in api_client_source
    assert unsafe_storage_lines == []
    assert unsafe_token_placement == []
    assert generic_retry_paths == []
