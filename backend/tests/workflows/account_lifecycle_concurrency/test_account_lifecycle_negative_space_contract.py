from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.no_db_cleanup,
    pytest.mark.suite_type("ordinary"),
]

_REPO_ROOT = Path(__file__).resolve().parents[4]
_BACKEND_SOURCE_ROOTS = ("backend/routes", "backend/services")
_ACCOUNT_ROUTE_PREFIXES = (
    "/auth",
    "/users",
    "/admin/users",
    "/user-settings",
    "/user-stats",
)

_ROUTE_CLASSIFICATIONS = {
    ("DELETE", "/auth/account"): "self-delete staged provider/local boundary",
    (
        "DELETE",
        "/auth/unfinished-account",
    ): "unfinished signup cleanup, not account recovery or relink",
    ("GET", "/admin/users"): "admin account read inventory",
    ("GET", "/admin/users/{user_id}"): "admin account detail read",
    (
        "GET",
        "/admin/users/{user_id}/game-activity",
    ): "admin account-adjacent activity read, no identity mutation",
    (
        "GET",
        "/admin/users/{user_id}/need-a-sub-activity",
    ): "admin account-adjacent activity read, no identity mutation",
    ("GET", "/auth/email-availability"): "signup preflight, not recovery authority",
    ("GET", "/auth/me"): "current local user read after provider authentication",
    ("GET", "/user-settings/me"): "current user's one-to-one settings read",
    ("GET", "/user-settings/{user_id}"): "admin settings read, no context create",
    ("GET", "/user-stats"): "admin stats read, no context create",
    ("GET", "/user-stats/me"): "current user's one-to-one stats read",
    ("GET", "/user-stats/{user_id}"): "admin stats read, no context create",
    ("GET", "/users"): "admin user list read",
    ("GET", "/users/me"): "current user's profile read",
    ("GET", "/users/{user_id}"): "admin user profile read",
    ("DELETE", "/users/{user_id}"): "disabled generic user deletion scaffold",
    (
        "PATCH",
        "/admin/users/{user_id}/role",
    ): "admin role mutation with final-admin guard",
    ("PATCH", "/user-settings/me"): "current user's settings update/repair",
    (
        "PATCH",
        "/user-settings/{user_id}",
    ): "retired generic settings mutation scaffold",
    ("PATCH", "/user-stats/{user_id}"): "retired generic stats mutation scaffold",
    ("PATCH", "/users/me"): "current user's non-identity profile update",
    ("PATCH", "/users/{user_id}"): "disabled generic user mutation scaffold",
    (
        "POST",
        "/admin/users/{user_id}/delete",
    ): "admin-delete staged provider/local boundary",
    (
        "POST",
        "/admin/users/{user_id}/delete-preview",
    ): "admin-delete current-state preview",
    (
        "POST",
        "/admin/users/{user_id}/hosting-restriction-preview",
    ): "admin hosting restriction preview, not identity linkage",
    (
        "POST",
        "/admin/users/{user_id}/restore-hosting",
    ): "admin hosting restriction workflow, not identity linkage",
    (
        "POST",
        "/admin/users/{user_id}/restrict-hosting",
    ): "admin hosting restriction workflow, not identity linkage",
    (
        "POST",
        "/admin/users/{user_id}/suspend",
    ): "admin account-status mutation with final-admin guard",
    (
        "POST",
        "/admin/users/{user_id}/suspension-preview",
    ): "admin suspension current-state preview",
    (
        "POST",
        "/admin/users/{user_id}/unsuspend",
    ): "admin account-status restoration workflow",
    ("POST", "/auth/sync-user"): "approved Firebase UID sync owner",
    ("POST", "/user-settings"): "retired generic settings creation scaffold",
    ("POST", "/user-stats"): "retired generic stats creation scaffold",
    ("POST", "/users"): "disabled generic user creation scaffold",
}

_SOURCE_CLASSIFICATIONS = {
    "backend/routes/admin_user_routes.py": (
        "registered admin account lifecycle routes; hosting endpoints are "
        "classified adjacent admin-user hosting policy, not identity linkage"
    ),
    "backend/routes/auth_routes.py": (
        "registered sync, current-user, signup preflight, and self-delete routes"
    ),
    "backend/routes/user_routes.py": (
        "profile reads/current profile update plus disabled generic user writes"
    ),
    "backend/routes/user_settings_routes.py": (
        "settings read/current-user update plus retired generic settings writes"
    ),
    "backend/routes/user_stats_routes.py": (
        "stats read routes plus retired generic stats writes"
    ),
    "backend/services/account_deletion_service.py": (
        "self-delete staging, provider boundary, partial-failure support state"
    ),
    "backend/services/account_eligibility_service.py": (
        "email-verification-derived eligibility helper, not identity linkage"
    ),
    "backend/services/admin_user_account_service.py": (
        "admin suspension/unsuspension lifecycle and final-admin guard"
    ),
    "backend/services/admin_user_delete_service.py": (
        "admin-delete staging, provider boundary, partial-failure support state"
    ),
    "backend/services/admin_user_hosting_service.py": (
        "admin hosting-status workflow, adjacent to user account state but not "
        "identity linkage"
    ),
    "backend/services/admin_user_role_service.py": (
        "admin role mutation lifecycle and final-admin guard"
    ),
    "backend/services/admin_user_service.py": (
        "admin user read/preview helpers, counts, and active-admin queries"
    ),
    "backend/services/auth_account_service.py": (
        "approved Firebase UID sync/provisioning/context-row repair owner"
    ),
    "backend/services/auth_service.py": (
        "provider identity verification and current local state dependencies"
    ),
    "backend/services/support_flag_policy.py": (
        "account-delete partial-failure support flag policy"
    ),
    "backend/services/support_flag_service.py": (
        "support flag staging used by deletion partial-failure recording"
    ),
    "backend/services/user_service.py": (
        "profile reads/current profile update and disabled generic user writes"
    ),
    "backend/services/user_settings_service.py": (
        "settings read/current-user repair; generic create path is route-retired"
    ),
    "backend/services/user_stats_service.py": (
        "stats read/update helpers; generic create path is route-retired"
    ),
}

_DISABLED_ROUTE_SENTINELS = {
    ("PATCH", "/user-settings/{user_id}"): "raise_retired_mutation_route",
    ("PATCH", "/user-stats/{user_id}"): "raise_retired_mutation_route",
    ("PATCH", "/users/{user_id}"): "reject_generic_user_mutation()",
    ("DELETE", "/users/{user_id}"): "reject_generic_user_mutation()",
    ("POST", "/user-settings"): "raise_retired_mutation_route",
    ("POST", "/user-stats"): "raise_retired_mutation_route",
    ("POST", "/users"): "reject_generic_user_mutation()",
}

_ALLOWED_USER_CONSTRUCTION_PATHS = {
    "backend/services/auth_account_service.py",
}
_ALLOWED_CONTEXT_CONSTRUCTION_PATHS = {
    "backend/services/auth_account_service.py",
    "backend/services/user_settings_service.py",
    "backend/services/user_stats_service.py",
}


def _read(relative_path: str) -> str:
    return (_REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _relative(path: Path) -> str:
    return path.relative_to(_REPO_ROOT).as_posix()


def _is_source_candidate(relative_path: str, source: str) -> bool:
    path = Path(relative_path)
    stem = path.stem

    if relative_path.startswith("backend/routes/"):
        return (
            stem
            in {
                "admin_user_routes",
                "auth_routes",
                "user_routes",
                "user_settings_routes",
                "user_stats_routes",
            }
            or any(term in stem for term in ("link", "merge", "reassign", "recovery"))
        )

    if not relative_path.startswith("backend/services/"):
        return False

    return (
        stem.startswith(("account", "admin_user", "auth", "user"))
        or any(term in stem for term in ("link", "merge", "reassign", "recovery"))
        or (
            stem.startswith("support_flag")
            and (
                "account_delete_partial_failure" in source
                or "stage_support_flag" in source
            )
        )
    )


def _discover_source_candidates() -> set[str]:
    discovered: set[str] = set()
    for root in _BACKEND_SOURCE_ROOTS:
        for path in sorted((_REPO_ROOT / root).glob("*.py")):
            if path.name == "__init__.py":
                continue
            relative_path = _relative(path)
            source = path.read_text(encoding="utf-8")
            if _is_source_candidate(relative_path, source):
                discovered.add(relative_path)
    return discovered


def _discover_routes():
    from fastapi.routing import APIRoute
    import backend.main as backend_main

    routes = {}
    for route in backend_main.app.routes:
        if not isinstance(route, APIRoute):
            continue
        if not route.path.startswith(_ACCOUNT_ROUTE_PREFIXES):
            continue
        for method in route.methods or set():
            if method in {"HEAD", "OPTIONS"}:
                continue
            routes[(method, route.path)] = route
    return routes


def _parse(relative_path: str) -> ast.AST:
    return ast.parse(_read(relative_path), filename=relative_path)


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _assignment_targets(node: ast.AST) -> list[ast.AST]:
    if isinstance(node, ast.Assign):
        return list(node.targets)
    if isinstance(node, ast.AnnAssign):
        return [node.target]
    if isinstance(node, ast.AugAssign):
        return [node.target]
    return []


def _is_none_literal(node: ast.AST | None) -> bool:
    return isinstance(node, ast.Constant) and node.value is None


@pytest.mark.requirement("WS03-02-R11")
def test_active_route_inventory_classifies_every_account_lifecycle_surface() -> None:
    routes = _discover_routes()
    discovered_keys = set(routes)
    classified_keys = set(_ROUTE_CLASSIFICATIONS)

    assert discovered_keys == classified_keys
    assert all(reason.strip() for reason in _ROUTE_CLASSIFICATIONS.values())

    disallowed_terms = ("merge", "relink", "recover", "reassign", "impersonate", "takeover")
    risky_routes = [
        (method, path)
        for method, path in discovered_keys
        if any(term in path.lower() for term in disallowed_terms)
    ]
    assert risky_routes == []

    for route_key, sentinel in _DISABLED_ROUTE_SENTINELS.items():
        endpoint_source = inspect.getsource(routes[route_key].endpoint)
        assert sentinel in endpoint_source


@pytest.mark.requirement("WS03-02-R11")
def test_active_backend_source_inventory_classifies_every_candidate_module() -> None:
    discovered_paths = _discover_source_candidates()
    classified_paths = set(_SOURCE_CLASSIFICATIONS)

    assert discovered_paths == classified_paths
    for relative_path, classification in _SOURCE_CLASSIFICATIONS.items():
        assert classification.strip()
        assert "out of scope" not in classification.lower()
        assert (_REPO_ROOT / relative_path).is_file()


@pytest.mark.requirement("WS03-02-R1", "WS03-02-R5", "WS03-02-R11")
def test_active_backend_source_has_no_unapproved_uid_reassignment_or_user_creation() -> None:
    risky_auth_reassignments: list[str] = []
    risky_user_constructors: list[str] = []

    for relative_path in sorted(_discover_source_candidates()):
        tree = _parse(relative_path)
        for node in ast.walk(tree):
            for target in _assignment_targets(node):
                if isinstance(target, ast.Attribute) and target.attr == "auth_user_id":
                    value = getattr(node, "value", None)
                    if not _is_none_literal(value):
                        risky_auth_reassignments.append(f"{relative_path}:{node.lineno}")

            if not isinstance(node, ast.Call) or _call_name(node.func) != "User":
                continue
            if relative_path not in _ALLOWED_USER_CONSTRUCTION_PATHS:
                risky_user_constructors.append(f"{relative_path}:{node.lineno}")

    assert risky_auth_reassignments == []
    assert risky_user_constructors == []

    combined = "\n".join(_read(path) for path in sorted(_discover_source_candidates()))
    forbidden_patterns = [
        r"email_owner\.auth_user_id\s*=(?!=)",
        r"\.auth_user_id\s*=\s*payload\.auth_user_id",
        r"\bmerge_.*user\b",
        r"\brelink_.*email\b",
        r"\breassign_.*email\b",
        r"\brecover_.*local.*account\b",
    ]
    for pattern in forbidden_patterns:
        assert re.search(pattern, combined, flags=re.IGNORECASE) is None

    assert "sync_user_workflow" in combined
    assert "A user with this email already exists." in combined
    assert "reject_generic_user_mutation()" in combined


@pytest.mark.requirement("WS03-02-R11")
def test_context_row_provisioning_candidates_are_classified_and_generic_routes_are_retired() -> None:
    risky_context_constructors: list[str] = []

    for relative_path in sorted(_discover_source_candidates()):
        tree = _parse(relative_path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            call_name = _call_name(node.func)
            if call_name not in {"UserSettings", "UserStats"}:
                continue
            if relative_path not in _ALLOWED_CONTEXT_CONSTRUCTION_PATHS:
                risky_context_constructors.append(f"{relative_path}:{node.lineno}")

    assert risky_context_constructors == []

    user_settings_routes = _read("backend/routes/user_settings_routes.py")
    user_stats_routes = _read("backend/routes/user_stats_routes.py")
    assert user_settings_routes.count("raise_retired_mutation_route(") == 2
    assert user_stats_routes.count("raise_retired_mutation_route(") == 2
    assert "create_user_settings_workflow(" not in user_settings_routes
    assert "create_user_stats_workflow(" not in user_stats_routes


@pytest.mark.requirement("WS03-02-R6", "WS03-02-R9", "WS03-02-R11")
def test_protected_dependency_source_uses_current_local_state_not_role_or_status_cache() -> None:
    auth_service = _read("backend/services/auth_service.py")

    assert "get_active_user_by_auth_id(identity.auth_user_id, db)" in auth_service
    assert "def require_active_user(" in auth_service
    assert 'user.account_status != "active"' in auth_service
    assert "def require_active_admin(" in auth_service
    assert "require_active_admin_user(current_user)" in auth_service
    assert "role == ADMIN_ROLE" in auth_service

    combined = "\n".join(_read(path) for path in sorted(_discover_source_candidates()))
    for forbidden in ("@lru_cache", "cached_user", "account_status_cache", "role_cache"):
        assert forbidden not in combined


@pytest.mark.requirement("WS03-02-R6", "WS03-02-R7", "WS03-02-R11")
def test_deletion_source_keeps_unknown_outcomes_manual_and_terminal_states_non_resurrecting() -> None:
    self_delete = _read("backend/services/account_deletion_service.py")
    admin_delete = _read("backend/services/admin_user_delete_service.py")

    for source in (self_delete, admin_delete):
        assert "DependencyMutationTimeoutUnknownError" in source
        assert "firebase_delete_outcome_unknown" in source
        assert "clear_auth_link=False" in source
        assert '"auth_identity_deleted": "unknown"' in source
        assert "delete_firebase_user(auth_user_id)" in source

    self_delete_workflow = self_delete[self_delete.find("def delete_account_workflow") :]
    admin_delete_workflow = admin_delete[admin_delete.find("def delete_admin_user") :]
    assert "while " not in self_delete_workflow
    assert "while " not in admin_delete_workflow

    assert "user.account_status = \"pending_deletion\"" in self_delete
    assert "user.auth_user_id = None" in self_delete
    assert "anonymize_user(user, now)" in self_delete
    assert "target_user.account_status = \"pending_deletion\"" in admin_delete
    assert "target_user.auth_user_id = None" in admin_delete
    assert "anonymize_user(target_user, now)" in admin_delete


@pytest.mark.requirement("WS03-02-R8", "WS03-02-R11")
def test_recovery_and_linking_inventory_has_no_local_password_reset_or_reassignment_api() -> None:
    frontend_sources = {
        "frontend/src/lib/authErrors.js": _read("frontend/src/lib/authErrors.js"),
        "frontend/src/pages/auth/ForgotPasswordPage.jsx": _read(
            "frontend/src/pages/auth/ForgotPasswordPage.jsx"
        ),
        "frontend/src/pages/auth/CheckEmailPage.jsx": _read(
            "frontend/src/pages/auth/CheckEmailPage.jsx"
        ),
        "frontend/src/pages/auth/usePasswordResetForm.js": _read(
            "frontend/src/pages/auth/usePasswordResetForm.js"
        ),
        "frontend/src/context/authProviderCredentialActions.js": _read(
            "frontend/src/context/authProviderCredentialActions.js"
        ),
    }
    backend_sources = {
        path: _read(path)
        for path in sorted(_discover_source_candidates())
        if path.startswith("backend/routes/") or "auth" in Path(path).stem
    }

    assert "sendPasswordResetEmail" in frontend_sources[
        "frontend/src/context/authProviderCredentialActions.js"
    ]
    assert "verifyPasswordResetCode" in frontend_sources[
        "frontend/src/context/authProviderCredentialActions.js"
    ]
    assert "confirmFirebasePasswordReset" in frontend_sources[
        "frontend/src/context/authProviderCredentialActions.js"
    ]
    assert "linkWithCredential(firebaseUser, credential)" in frontend_sources[
        "frontend/src/context/authProviderCredentialActions.js"
    ]
    assert "Email or password is incorrect." in frontend_sources[
        "frontend/src/lib/authErrors.js"
    ]
    assert "requestError?.code?.includes('auth/user-not-found')" in frontend_sources[
        "frontend/src/pages/auth/ForgotPasswordPage.jsx"
    ]
    assert "/email-availability" in backend_sources["backend/routes/auth_routes.py"]
    assert (
        "check_email_availability_workflow(email, db)"
        in backend_sources["backend/routes/auth_routes.py"]
    )

    combined = "\n".join(frontend_sources.values()) + "\n" + "\n".join(
        backend_sources.values()
    )
    for forbidden in (
        "/auth/reset-password",
        "/auth/recover-account",
        "/auth/link-account",
        "/auth/reassign-email",
        "localPasswordReset",
        "localAccountRecovery",
        "localEmailRelink",
        "localAccountMerge",
    ):
        assert forbidden not in combined


@pytest.mark.requirement("WS03-02-R10", "WS03-02-R11")
def test_final_admin_bypass_inventory_requires_locked_current_state_checks() -> None:
    role_service = _read("backend/services/admin_user_role_service.py")
    suspension_service = _read("backend/services/admin_user_account_service.py")
    self_delete = _read("backend/services/account_deletion_service.py")
    admin_delete = _read("backend/services/admin_user_delete_service.py")

    assert ".with_for_update()" in role_service
    assert "The last active admin cannot be demoted." in role_service
    assert "len(active_admin_users) <= 1" in role_service

    assert ".with_for_update()" in suspension_service
    assert "The last active admin cannot be suspended." in suspension_service
    assert "active_admin_count <= 1" in suspension_service

    assert ".with_for_update()" in self_delete
    assert "The last active admin cannot be deleted." in self_delete
    assert "active_admin_count <= 1" in self_delete

    assert "lock_user_and_active_admins_for_account_removal" in admin_delete
    assert "def lock_delete_users(" in admin_delete
    assert "The last active admin cannot be deleted." in admin_delete
    assert "active_admin_count <= 1" in admin_delete
