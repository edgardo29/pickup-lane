from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.suite_type("ordinary")]

REPO_ROOT = Path(__file__).resolve().parents[4]
FRONTEND_SRC = REPO_ROOT / "frontend/src"
JS_EXTENSIONS = {".js", ".jsx", ".ts", ".tsx"}


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text()


def _frontend_source_files() -> list[Path]:
    return sorted(
        path
        for path in FRONTEND_SRC.rglob("*")
        if path.is_file() and path.suffix in JS_EXTENSIONS
    )


def _relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


@pytest.mark.requirement("WS03-01-R9")
def test_firebase_auth_uses_explicit_browser_local_persistence() -> None:
    source = _read("frontend/src/lib/firebase.js")

    assert "browserLocalPersistence" in source
    assert re.search(
        r"setPersistence\(\s*auth\s*,\s*browserLocalPersistence\s*\)",
        source,
    )
    assert "export async function ensureAuthPersistence" in source
    assert "await authPersistenceReady" in source


@pytest.mark.requirement("WS03-01-R9")
def test_credential_sign_in_flows_await_persistence_setup_before_sign_in() -> None:
    credential_source = _read("frontend/src/context/authProviderCredentialActions.js")
    google_source = _read("frontend/src/context/authProviderGoogleActions.js")

    for sign_in_call in (
        "signInWithEmailAndPassword(auth, email, password)",
        "createUserWithEmailAndPassword(auth, email, password)",
    ):
        assert credential_source.index("await ensureAuthPersistence()") < (
            credential_source.index(sign_in_call)
        )

    assert google_source.index("await ensureAuthPersistence()") < (
        google_source.index("signInWithPopup(auth, googleProvider)")
    )


@pytest.mark.requirement("WS03-01-R9")
def test_firebase_id_tokens_are_sent_to_backend_as_authorization_bearer_headers() -> None:
    token_files = [
        path
        for path in _frontend_source_files()
        if "getIdToken" in path.read_text()
    ]
    transport_files: list[str] = []
    refresh_only_files: list[str] = []

    for path in token_files:
        source = path.read_text()
        rel = _relative(path)
        if "apiRequest(" not in source and "fetch(" not in source:
            refresh_only_files.append(rel)
            continue

        transport_files.append(rel)
        assert "Authorization" in source
        assert "Bearer" in source

    assert "frontend/src/lib/authApi.js" in transport_files
    assert "frontend/src/lib/reauthentication.js" in refresh_only_files


@pytest.mark.requirement("WS03-01-R9")
def test_bearer_tokens_are_not_manually_duplicated_into_app_storage_urls_or_forms() -> None:
    storage_terms = ("localStorage", "sessionStorage", "indexedDB")
    token_terms = ("idToken", "accessToken", "refreshToken", "Bearer", "Authorization")
    unsafe_storage_lines: list[str] = []
    unsafe_url_or_body_lines: list[str] = []

    for path in _frontend_source_files():
        source = path.read_text()
        rel = _relative(path)
        for line_number, line in enumerate(source.splitlines(), start=1):
            if any(term in line for term in storage_terms) and any(
                term in line for term in token_terms
            ):
                unsafe_storage_lines.append(f"{rel}:{line_number}:{line.strip()}")

        if "getIdToken" not in source:
            continue

        if re.search(r"[?&](?:id_token|access_token|token)=", source):
            unsafe_url_or_body_lines.append(f"{rel}: token query parameter")
        if re.search(
            r"body\s*:\s*JSON\.stringify\(\{[^}]*\b(?:idToken|token|accessToken)\b",
            source,
            re.DOTALL,
        ):
            unsafe_url_or_body_lines.append(f"{rel}: token JSON body")
        if re.search(
            r"new\s+FormData\(\)[\s\S]{0,500}\b(?:idToken|token|accessToken)\b",
            source,
        ):
            unsafe_url_or_body_lines.append(f"{rel}: token form payload")

    assert unsafe_storage_lines == []
    assert unsafe_url_or_body_lines == []


@pytest.mark.requirement("WS03-01-R9")
def test_auth_refresh_is_bounded_to_safe_read_specific_paths() -> None:
    auth_source = _read("frontend/src/lib/authApi.js")
    admin_source = _read("frontend/src/pages/admin/shared/adminApi.js")
    api_client_source = _read("frontend/src/lib/apiClient.js")

    assert "if (!forceRefresh && error?.status === 401)" in auth_source
    assert auth_source.count("firebaseUser.getIdToken(true)") == 1
    assert "apiRequest('/auth/me'" in auth_source
    auth_retry_block = auth_source[
        auth_source.index("export async function getAuthenticatedAppUser") :
        auth_source.index("export async function syncFirebaseUser")
    ]
    assert "method:" not in auth_retry_block

    assert "if (!forceRefresh && error?.status === 401)" in admin_source
    assert "fetchAdminMe({ firebaseUser, forceRefresh: true })" in admin_source
    admin_retry_block = admin_source[
        admin_source.index("export async function fetchAdminMe") :
        admin_source.index("export async function listAdminReviewCases")
    ]
    assert "apiRequest('/admin/me'" in admin_retry_block
    assert "method:" not in admin_retry_block

    assert "getIdToken" not in api_client_source
    assert "Authorization" not in api_client_source
    assert "forceRefresh" not in api_client_source


@pytest.mark.requirement("WS03-01-R9")
def test_no_generic_auth_retry_interceptor_blindly_replays_mutations() -> None:
    unsafe_retry_candidates: list[str] = []

    for path in _frontend_source_files():
        source = path.read_text()
        rel = _relative(path)
        if "error?.status === 401" not in source:
            continue
        if rel in {
            "frontend/src/lib/authApi.js",
            "frontend/src/pages/admin/shared/adminApi.js",
            "frontend/src/routes/RouteGuards.jsx",
            "frontend/src/pages/admin/sign-in/useAdminSignInForm.js",
        }:
            continue
        unsafe_retry_candidates.append(rel)

    assert unsafe_retry_candidates == []
