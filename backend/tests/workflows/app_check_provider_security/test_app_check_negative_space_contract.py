from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.suite_type("ordinary")]

REPO_ROOT = Path(__file__).resolve().parents[4]
BACKEND_ROOT = REPO_ROOT / "backend"
FRONTEND_ROOT = REPO_ROOT / "frontend"
APP_CHECK_SERVICE = BACKEND_ROOT / "services/app_check_service.py"
APP_CHECK_MIDDLEWARE = BACKEND_ROOT / "services/app_check_middleware.py"
APP_CHECK_POLICY = BACKEND_ROOT / "services/app_check_policy.py"
FIREBASE_CLIENT = BACKEND_ROOT / "firebase_admin_client.py"
FRONTEND_APP_CHECK = FRONTEND_ROOT / "src/lib/appCheck.js"
FRONTEND_API_CLIENT = FRONTEND_ROOT / "src/lib/apiClient.js"
RECENT_AUTH_ROOT = BACKEND_ROOT / "tests/workflows/recent_auth_step_up"


def _source(path: Path) -> str:
    return path.read_text()


@pytest.mark.requirement("WS03-03B-R3", "WS03-03B-R6", "WS03-03B-R7")
def test_backend_verifier_does_not_accept_query_body_cookie_or_client_app_id_bypass() -> None:
    source = _source(APP_CHECK_SERVICE)

    assert 'APP_CHECK_HEADER_NAME = "X-Firebase-AppCheck"' in source
    for forbidden in (
        ".query_params",
        ".json(",
        ".form(",
        ".cookies",
        "X-Firebase-App-ID",
        "client_app_id",
        "app_check_valid",
        "valid_app_check",
    ):
        assert forbidden not in source


@pytest.mark.requirement("WS03-03B-R3", "WS03-03B-R7")
def test_backend_verifier_uses_central_provider_boundary_and_no_manual_jwt_decode() -> None:
    service_source = _source(APP_CHECK_SERVICE)
    firebase_client_source = _source(FIREBASE_CLIENT)
    combined_source = "\n".join([service_source, firebase_client_source])

    assert "from firebase_admin" not in service_source
    assert "app_check.verify_token" not in service_source
    assert "verify_firebase_app_check_token" in service_source
    assert "FirebaseAppCheckUnavailableError" in service_source
    assert "DependencyReadTimeoutError" in service_source
    assert "from firebase_admin import app_check" in firebase_client_source
    assert "app_check.verify_token(app_check_token, app=firebase_app)" in firebase_client_source
    assert "initialize_firebase_admin()" in firebase_client_source
    assert 'FIREBASE_APP_CHECK_VERIFY_OPERATION = "firebase.app_check.verify"' in (
        firebase_client_source
    )
    assert "jwt.decode" not in combined_source
    assert "get_unverified" not in combined_source
    assert "base64" not in combined_source
    assert "hmac" not in combined_source
    assert "rsa" not in combined_source.lower()


@pytest.mark.requirement("WS03-03B-R3", "WS03-03B-R6", "WS03-03B-R7")
def test_verified_app_id_comparison_is_required_and_not_used_as_identity_or_authz() -> None:
    service_source = _source(APP_CHECK_SERVICE)
    middleware_source = _source(APP_CHECK_MIDDLEWARE)

    assert 'verified_claims.get("app_id")' in service_source
    assert "verified_app_id != expected_app_id" in service_source
    assert "firebase_app_check_app_id" not in middleware_source
    for forbidden in ("user_id", "actor_id", "require_active", "require_recent"):
        assert forbidden not in service_source
        assert forbidden not in middleware_source


@pytest.mark.requirement("WS03-03B-R1", "WS03-03B-R7")
def test_local_defaults_do_not_leak_into_production_like_app_check_mode() -> None:
    source = _source(BACKEND_ROOT / "settings.py")

    assert 'if app_env.is_production_like:' in source
    assert '_fail("FIREBASE_APP_CHECK_MODE"' in source
    assert "FirebaseAppCheckMode.DISABLED" in source


@pytest.mark.requirement("WS03-03B-R2", "WS03-03B-R6", "WS03-03B-R7")
def test_frontend_source_has_no_app_check_bypass_flag_persistence_or_token_leakage() -> None:
    combined_source = "\n".join([_source(FRONTEND_APP_CHECK), _source(FRONTEND_API_CLIENT)])

    for forbidden in (
        "appCheck: false",
        "skipAppCheck",
        "disableAppCheck",
        "localStorage",
        "sessionStorage",
        "document.cookie",
        "console.",
        "URLSearchParams({ appCheck",
        "body: appCheckToken",
    ):
        assert forbidden not in combined_source


@pytest.mark.requirement("WS03-03B-R3", "WS03-03B-R7")
def test_app_check_observability_excludes_raw_provider_material_and_new_mode_label() -> None:
    middleware_source = _source(APP_CHECK_MIDDLEWARE)

    assert "EventEnvelope" in middleware_source
    assert "labels={\"route_template\": event.route_template}" in middleware_source
    assert "\"mode\"" not in middleware_source
    assert "'mode'" not in middleware_source
    for forbidden in (
        "decoded_claims",
        "verified_app_id",
        "expected_app_id",
        "provider exception",
        "stack",
        "raw_token",
    ):
        assert forbidden not in middleware_source


@pytest.mark.requirement("WS03-03B-R5", "WS03-03B-R7")
def test_route_policy_has_no_unknown_excluded_fallback_or_post_routing_dependency() -> None:
    policy_source = _source(APP_CHECK_POLICY)
    middleware_source = _source(APP_CHECK_MIDDLEWARE)

    assert "SUPPORTED_BROWSER_API_ROUTE_TAGS" in policy_source
    assert "Unclassified API route" in policy_source
    assert "scope[\"route\"]" not in middleware_source
    assert "scope.get(\"route\")" not in middleware_source
    assert "endpoint" not in middleware_source
    assert "unknown" not in policy_source.lower()


@pytest.mark.requirement("WS03-03B-R4", "WS03-03B-R6", "WS03-03B-R7")
def test_recorder_failure_path_cannot_turn_enforced_denial_into_allow_or_retry() -> None:
    source = _source(APP_CHECK_MIDDLEWARE)

    assert "_record_best_effort(" in source
    assert "except Exception" in source
    assert "return" in _function_source(source, "_record_best_effort", "_stable_error_code")
    assert "retry" not in source.lower()


@pytest.mark.requirement("WS03-03B-R6", "WS03-03B-R7")
def test_ws03_03a_recent_auth_evidence_still_has_deferred_provider_boundaries() -> None:
    declaration = (BACKEND_ROOT / "tests/support/requirements/ws03_03a.json").read_text()
    recent_auth_sources = "\n".join(path.read_text() for path in RECENT_AUTH_ROOT.glob("*.py"))

    assert '"id": "WS03-03A-R12"' in declaration
    assert '"id": "WS03-03A-R13"' in declaration
    assert '"id": "WS03-03A-R14"' in declaration
    assert '"state": "deferred"' in declaration
    assert "AUTH.RECENT_AUTH_REQUIRED" in recent_auth_sources


@pytest.mark.requirement("WS03-03B-R7")
def test_deferred_provider_governance_requirements_have_zero_pytest_mappings() -> None:
    mapped_requirements = _requirement_markers(BACKEND_ROOT / "tests")

    assert "WS03-03B-R8" not in mapped_requirements
    assert "WS03-03B-R9" not in mapped_requirements
    assert "WS03-03B-R10" not in mapped_requirements


def _requirement_markers(root: Path) -> set[str]:
    markers: set[str] = set()
    for path in root.rglob("*.py"):
        if "legacy" in path.relative_to(root).parts:
            continue
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if _call_name(node.func) != "pytest.mark.requirement":
                continue
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    markers.add(arg.value)
    return markers


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Call):
        return _call_name(node.func)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parts: list[str] = []
        current: ast.AST = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
    return ""


def _function_source(source: str, start_name: str, end_name: str) -> str:
    start = source.index(f"def {start_name}")
    end = source.index(f"def {end_name}", start + 1)
    return source[start:end]
