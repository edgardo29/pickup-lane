from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path

import pytest

from backend.tests.workflows.recent_auth_step_up.test_recent_auth_route_inventory_contract import (
    FROZEN_RECENT_AUTH_ROUTE_MATRIX,
    RECENT_AUTH_NOT_REQUIRED_ADMIN_MUTATIONS,
    RECENT_AUTH_REQUIRED_ADMIN_MUTATIONS,
    RETIRED_OR_NON_EXECUTING_ADMIN_MUTATIONS,
    _admin_access_mutation_routes,
    _dependency_call_names,
    _has_any_recent_auth_dependency,
    _has_dependency,
    _registered_routes,
)

pytestmark = [
    pytest.mark.no_db_cleanup,
    pytest.mark.suite_type("ordinary"),
]

REPO_ROOT = Path(__file__).resolve().parents[4]
BACKEND_ROOT = REPO_ROOT / "backend"
FRONTEND_SRC = REPO_ROOT / "frontend/src"
RECENT_AUTH_TEST_ROOT = REPO_ROOT / "backend/tests/workflows/recent_auth_step_up"

PRODUCTION_FRESHNESS_OWNER_PATHS = {
    "backend/services/auth_service.py",
    "backend/services/recent_auth_policy.py",
    "backend/settings.py",
}
ALLOWED_DECODED_TOKEN_PATHS = {
    "backend/firebase_admin_client.py",
    "backend/services/auth_service.py",
}


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _backend_source_files() -> list[Path]:
    roots = [
        BACKEND_ROOT / "alembic/versions",
        BACKEND_ROOT / "models",
        BACKEND_ROOT / "routes",
        BACKEND_ROOT / "schemas",
        BACKEND_ROOT / "services",
        BACKEND_ROOT / "settings.py",
        BACKEND_ROOT / "firebase_admin_client.py",
    ]
    files: list[Path] = []
    for root in roots:
        if root.is_file():
            files.append(root)
            continue
        for path in root.rglob("*.py"):
            if "__pycache__" not in path.parts:
                files.append(path)
    return sorted(files)


def _frontend_source_files() -> list[Path]:
    excluded_parts = {"node_modules", "dist", "playwright-report", "test-results"}
    return sorted(
        path
        for path in FRONTEND_SRC.rglob("*")
        if path.is_file()
        and path.suffix in {".js", ".jsx", ".ts", ".tsx"}
        and excluded_parts.isdisjoint(path.parts)
    )


def _trusted_support_files() -> list[Path]:
    support_root = REPO_ROOT / "backend/tests/support"
    return sorted(
        path
        for path in support_root.rglob("*")
        if path.is_file()
        and path.suffix in {".py", ".json"}
        and "__pycache__" not in path.parts
    )


def _requirement_markers(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=_relative(path))
    markers: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (
            isinstance(func, ast.Attribute)
            and func.attr == "requirement"
            and isinstance(func.value, ast.Attribute)
            and func.value.attr == "mark"
        ):
            continue
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                markers.add(arg.value)
    return markers


@pytest.mark.requirement("WS03-03A-R1", "WS03-03A-R10", "WS03-03A-R11")
def test_backend_source_has_no_alternate_recent_auth_freshness_authority() -> None:
    disallowed_freshness_terms: list[str] = []
    raw_decoded_token_users: list[str] = []
    disallowed_assignments: list[str] = []
    freshness_names = {
        "auth_time",
        "authenticated_at",
        "recent_auth_at",
        "recently_authenticated",
        "reauthenticated_at",
        "step_up_at",
        "step_up_token",
        "fresh_auth",
        "auth_fresh",
    }

    for path in _backend_source_files():
        relative_path = _relative(path)
        source = path.read_text(encoding="utf-8")
        lower_source = source.lower()
        if relative_path not in PRODUCTION_FRESHNESS_OWNER_PATHS:
            for term in freshness_names:
                if term in lower_source:
                    disallowed_freshness_terms.append(f"{relative_path}:{term}")
        if "decoded_token" in source and relative_path not in ALLOWED_DECODED_TOKEN_PATHS:
            raw_decoded_token_users.append(relative_path)

        tree = ast.parse(source, filename=relative_path)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = list(node.targets) if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    target_name = ""
                    if isinstance(target, ast.Name):
                        target_name = target.id
                    elif isinstance(target, ast.Attribute):
                        target_name = target.attr
                    if (
                        target_name.lower() in freshness_names
                        and relative_path not in PRODUCTION_FRESHNESS_OWNER_PATHS
                    ):
                        disallowed_assignments.append(f"{relative_path}:{target_name}")

    assert disallowed_freshness_terms == []
    assert raw_decoded_token_users == []
    assert disallowed_assignments == []


@pytest.mark.requirement("WS03-03A-R1", "WS03-03A-R10", "WS03-03A-R11")
def test_request_schema_and_storage_source_do_not_accept_client_freshness() -> None:
    schema_offenders: list[str] = []
    storage_offenders: list[str] = []
    cookie_or_cache_offenders: list[str] = []
    purpose_flag_offenders: list[str] = []
    freshness_terms = (
        "auth_time",
        "authenticated_at",
        "recentAuth",
        "recent_auth",
        "reauthenticated",
        "stepUp",
        "step_up",
    )
    request_terms = ("BaseModel", "Field(", "Query(", "Header(", "Body(")
    storage_terms = ("localStorage", "sessionStorage", "indexedDB")

    for path in _backend_source_files():
        relative_path = _relative(path)
        source = path.read_text(encoding="utf-8")
        if relative_path in PRODUCTION_FRESHNESS_OWNER_PATHS:
            continue
        if any(term in source for term in request_terms) and any(
            term in source for term in freshness_terms
        ):
            schema_offenders.append(relative_path)
        if re.search(r"purpose\s*[:=]", source, flags=re.IGNORECASE) and re.search(
            r"recent|reauth|step.?up|fresh", source, flags=re.IGNORECASE
        ):
            purpose_flag_offenders.append(relative_path)

    for path in _frontend_source_files():
        relative_path = _relative(path)
        source = path.read_text(encoding="utf-8")
        for line_number, line in enumerate(source.splitlines(), start=1):
            if any(storage in line for storage in storage_terms) and any(
                term in line for term in freshness_terms
            ):
                storage_offenders.append(f"{relative_path}:{line_number}")
            if ("document.cookie" in line or "Cache" in line) and any(
                term in line for term in freshness_terms
            ):
                cookie_or_cache_offenders.append(f"{relative_path}:{line_number}")

    assert schema_offenders == []
    assert purpose_flag_offenders == []
    assert storage_offenders == []
    assert cookie_or_cache_offenders == []


@pytest.mark.requirement("WS03-03A-R5", "WS03-03A-R6", "WS03-03A-R11")
def test_recent_auth_policy_window_and_partition_have_single_source_owners() -> None:
    policy_reexports: list[str] = []
    window_redefinitions: list[str] = []
    protected_action_redefinitions: list[str] = []

    for path in _backend_source_files():
        relative_path = _relative(path)
        source = path.read_text(encoding="utf-8")
        if (
            "RecentAuthProtectedAction" in source
            and relative_path != "backend/services/recent_auth_policy.py"
        ):
            policy_reexports.append(relative_path)
        if (
            "RECENT_AUTH_PROTECTED_ACTIONS" in source
            and relative_path != "backend/services/recent_auth_policy.py"
        ):
            protected_action_redefinitions.append(relative_path)
        if (
            "DEFAULT_RECENT_AUTHENTICATION_WINDOW_SECONDS" in source
            and relative_path != "backend/settings.py"
        ):
            window_redefinitions.append(relative_path)

    assert policy_reexports == []
    assert protected_action_redefinitions == []
    assert window_redefinitions == []


@pytest.mark.requirement("WS03-03A-R5", "WS03-03A-R6", "WS03-03A-R11")
def test_complete_admin_partition_fails_closed_for_drift_and_hidden_terminal_actions() -> None:
    from backend.services.recent_auth_policy import RECENT_AUTH_PROTECTED_ROUTE_KEYS

    registered_routes = _registered_routes()
    discovered_admin_mutations = _admin_access_mutation_routes(registered_routes)
    required = set(RECENT_AUTH_REQUIRED_ADMIN_MUTATIONS)
    not_required = set(RECENT_AUTH_NOT_REQUIRED_ADMIN_MUTATIONS)
    retired = set(RETIRED_OR_NON_EXECUTING_ADMIN_MUTATIONS)
    classified = required | not_required | retired

    assert len(required) == 22
    assert len(not_required) == 38
    assert len(retired) == 47
    assert len(classified) == 107
    assert required.isdisjoint(not_required)
    assert required.isdisjoint(retired)
    assert not_required.isdisjoint(retired)
    assert discovered_admin_mutations == classified
    assert RECENT_AUTH_PROTECTED_ROUTE_KEYS == set(FROZEN_RECENT_AUTH_ROUTE_MATRIX)

    for route_key in required:
        route = registered_routes[route_key]
        assert route_key in RECENT_AUTH_PROTECTED_ROUTE_KEYS
        assert _has_dependency(route, "require_recent_active_admin"), (
            f"{route_key} must not rely only on ordinary admin auth; dependencies "
            f"were {sorted(_dependency_call_names(route))}"
        )

    for route_key in not_required | retired:
        route = registered_routes[route_key]
        assert route_key not in RECENT_AUTH_PROTECTED_ROUTE_KEYS
        assert not _has_any_recent_auth_dependency(route), (
            f"{route_key} is not in the high-risk matrix but has recent-auth"
        )

    terminal_routes = {
        ("POST", "/admin/community-games/{game_id}/cancel"),
        ("POST", "/admin/need-a-sub/{post_id}/remove"),
        (
            "POST",
            "/admin/official-games/{game_id}/participants/{participant_id}/remove",
        ),
        ("DELETE", "/games/{game_id}"),
        ("DELETE", "/venues/{venue_id}"),
        ("PATCH", "/payment-events/{payment_event_id}"),
    }
    assert terminal_routes <= required
    assert terminal_routes.isdisjoint(not_required)
    assert terminal_routes.isdisjoint(retired)
    assert (
        "POST",
        "/admin/official-games/{game_id}/players",
    ) in not_required


@pytest.mark.requirement("WS03-03A-R6", "WS03-03A-R11")
def test_retired_or_non_executing_admin_mutations_remain_non_executing() -> None:
    registered_routes = _registered_routes()
    executing_retired_routes: list[tuple[str, str]] = []

    for route_key in sorted(RETIRED_OR_NON_EXECUTING_ADMIN_MUTATIONS):
        route = registered_routes.get(route_key)
        assert route is not None, f"Stale retired classification: {route_key}"
        endpoint_source = inspect.getsource(route.endpoint)
        if (
            "raise_retired_mutation_route" not in endpoint_source
            and "reject_generic_user_mutation()" not in endpoint_source
            and "_raise_admin_notification_scaffold_removed()" not in endpoint_source
        ):
            executing_retired_routes.append(route_key)

    assert executing_retired_routes == []


@pytest.mark.requirement("WS03-03A-R8", "WS03-03A-R11")
def test_frontend_source_has_no_blind_recent_auth_replay_or_credential_forwarding() -> None:
    generic_recent_auth_handlers: list[str] = []
    unsafe_token_refreshers: list[str] = []
    credential_forwarders: list[str] = []
    provider_result_forwarders: list[str] = []

    for path in _frontend_source_files():
        relative_path = _relative(path)
        source = path.read_text(encoding="utf-8")
        if (
            "AUTH.RECENT_AUTH_REQUIRED" in source
            and relative_path != "frontend/src/lib/stepUpAction.js"
        ):
            generic_recent_auth_handlers.append(relative_path)
        if (
            "getIdToken(true)" in source
            and relative_path
            not in {
                "frontend/src/lib/authApi.js",
                "frontend/src/lib/reauthentication.js",
            }
        ):
            unsafe_token_refreshers.append(relative_path)
        if "apiRequest(" in source and any(
            term in source for term in ("password", "credential", "providerCredential")
        ):
            if relative_path not in {
                "frontend/src/lib/authApi.js",
                "frontend/src/pages/auth/usePasswordResetForm.js",
            }:
                credential_forwarders.append(relative_path)
        if "reauthenticateWithPopup" in source and any(
            term in source for term in ("apiRequest(", "fetch(", "accessToken", "refreshToken")
        ):
            provider_result_forwarders.append(relative_path)

    api_client = _read("frontend/src/lib/apiClient.js")
    assert "getIdToken" not in api_client
    assert "forceRefresh" not in api_client
    assert "AUTH.RECENT_AUTH_REQUIRED" not in api_client
    assert generic_recent_auth_handlers == []
    assert unsafe_token_refreshers == []
    assert credential_forwarders == []
    assert provider_result_forwarders == []


@pytest.mark.requirement("WS03-03A-R9", "WS03-03A-R11")
def test_credential_linking_has_no_backend_relink_or_local_account_merge_path() -> None:
    backend_route_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in _backend_source_files()
        if _relative(path).startswith(("backend/routes", "backend/services"))
    )
    credential_actions = _read("frontend/src/context/authProviderCredentialActions.js")
    add_password = _read("frontend/src/pages/profile/useAddPasswordSettings.js")

    forbidden_backend_patterns = (
        "/auth/link-account",
        "/auth/relink",
        "/auth/reassign-email",
        "localAccountMerge",
        "localEmailRelink",
        "merge_user_by_email",
        "reassign_auth_user_id",
    )
    for pattern in forbidden_backend_patterns:
        assert pattern not in backend_route_text

    assert "linkWithCredential(firebaseUser, credential)" in credential_actions
    assert "await confirmStepUp({ actionLabel: 'add password sign-in' })" in add_password
    assert add_password.index(
        "await confirmStepUp({ actionLabel: 'add password sign-in' })"
    ) < add_password.index("await addPasswordToCurrentAccount(newPassword)")


@pytest.mark.requirement("WS03-03A-R8", "WS03-03A-R11")
def test_no_current_frontend_caller_exists_for_unowned_backend_only_routes() -> None:
    destructive_callers: list[str] = []
    payment_event_callers: list[str] = []

    for path in _frontend_source_files():
        relative_path = _relative(path)
        source = path.read_text(encoding="utf-8")
        if "/payment-events/" in source:
            payment_event_callers.append(relative_path)
        if "method: 'DELETE'" in source and (
            "/games/${" in source or "/venues/${" in source
        ):
            destructive_callers.append(relative_path)

    assert payment_event_callers == []
    assert destructive_callers == []


@pytest.mark.requirement("WS03-03A-R10", "WS03-03A-R11")
def test_current_trusted_support_does_not_offer_request_owned_freshness_bypass() -> None:
    support_bypass_candidates: list[str] = []
    unsafe_override_candidates: list[str] = []

    for path in _trusted_support_files():
        relative_path = _relative(path)
        source = path.read_text(encoding="utf-8")
        if "auth_time" in source or "authenticated_at" in source:
            if relative_path != "backend/tests/support/requirements/ws03_03a.json":
                support_bypass_candidates.append(relative_path)
        if "require_recent_authentication" in source or "require_recent_active" in source:
            unsafe_override_candidates.append(relative_path)

    assert support_bypass_candidates == []
    assert unsafe_override_candidates == []


@pytest.mark.requirement("WS03-03A-R11")
def test_deferred_provider_governance_requirements_have_no_pytest_mappings() -> None:
    forbidden_requirements = {
        "WS03-03A-" + suffix
        for suffix in ("R12", "R13", "R14")
    }
    mapped_requirements: dict[str, set[str]] = {}

    for path in sorted(RECENT_AUTH_TEST_ROOT.glob("test_*.py")):
        markers = _requirement_markers(path)
        if markers & forbidden_requirements:
            mapped_requirements[_relative(path)] = markers & forbidden_requirements

    assert mapped_requirements == {}
