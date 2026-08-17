from __future__ import annotations

import ast
import inspect
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone

import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute
from sqlalchemy import func, select, text

pytestmark = pytest.mark.suite_type("ordinary")


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _create_user(
    *,
    auth_user_id: str,
    email: str,
    role: str = "player",
    account_status: str = "active",
) -> uuid.UUID:
    from backend.models import User

    unique = uuid.uuid4().hex
    user = User(
        id=uuid.uuid4(),
        auth_user_id=auth_user_id,
        role=role,
        email=email,
        email_verified_at=datetime.now(timezone.utc),
        phone=f"+1555{unique[:10]}",
        first_name="Admin",
        last_name="Lifecycle",
        date_of_birth=date(1990, 1, 1),
        account_status=account_status,
        hosting_status="eligible",
    )
    with _session() as db:
        db.add(user)
        db.commit()
        return user.id


def _install_provider_identity(
    monkeypatch: pytest.MonkeyPatch,
    *,
    uid: str,
    email: str,
) -> None:
    import backend.services.auth_service as auth_service

    payload = {
        "uid": uid,
        "email": email,
        "email_verified": True,
        "auth_time": 1_700_000_000,
    }

    def verify_token(token: str) -> dict[str, object]:
        if token != "valid-token":
            raise ValueError("invalid synthetic token")
        return dict(payload)

    monkeypatch.setattr(auth_service, "verify_firebase_token", verify_token)


def _user_snapshot(user_id: uuid.UUID) -> dict[str, object]:
    from backend.models import User

    with _session() as db:
        user = db.get(User, user_id)
        assert user is not None
        return {
            "auth_user_id": user.auth_user_id,
            "email": user.email,
            "account_status": user.account_status,
            "role": user.role,
            "deleted_at": user.deleted_at,
        }


def _active_admin_count() -> int:
    from backend.models import User

    with _session() as db:
        return int(
            db.scalar(
                select(func.count())
                .select_from(User)
                .where(
                    User.role == "admin",
                    User.account_status == "active",
                    User.deleted_at.is_(None),
                )
            )
            or 0
        )


def _role_payload(idempotency_key: str):
    from backend.schemas.admin_user_schema import AdminUserRoleChangeCreate

    return AdminUserRoleChangeCreate(
        role="player",
        reason="final admin guard proof",
        idempotency_key=idempotency_key,
    )


def _parse_function(function) -> ast.FunctionDef:
    module = ast.parse(inspect.getsource(function))
    function_node = module.body[0]
    assert isinstance(function_node, ast.FunctionDef)
    return function_node


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _call_names(function_node: ast.AST) -> list[str]:
    names: list[str] = []
    for node in ast.walk(function_node):
        if isinstance(node, ast.Call):
            name = _call_name(node.func)
            if name is not None:
                names.append(name)
    return names


def _assignment_targets(node: ast.AST) -> list[ast.AST]:
    if isinstance(node, ast.Assign):
        return list(node.targets)
    if isinstance(node, ast.AnnAssign):
        return [node.target]
    if isinstance(node, ast.AugAssign):
        return [node.target]
    return []


def _attribute_assignments(function_node: ast.AST, attr: str) -> list[ast.AST]:
    assignments: list[ast.AST] = []
    for node in ast.walk(function_node):
        for target in _assignment_targets(node):
            if isinstance(target, ast.Attribute) and target.attr == attr:
                assignments.append(node)
    return assignments


def _new_user_role_values(function_node: ast.AST) -> set[object]:
    values: set[object] = set()
    for node in ast.walk(function_node):
        if not isinstance(node, ast.Call) or _call_name(node.func) != "User":
            continue
        for keyword in node.keywords:
            if keyword.arg == "role" and isinstance(keyword.value, ast.Constant):
                values.add(keyword.value.value)
    return values


def _admin_bootstrap_route_candidates() -> list[tuple[str, str, str]]:
    import backend.main as backend_main

    terms = (
        "bootstrap",
        "break_glass",
        "break-glass",
        "default_admin",
        "grant_admin",
        "impersonat",
        "make_admin",
        "shared_admin",
    )
    candidates: list[tuple[str, str, str]] = []
    for route in backend_main.app.routes:
        if not isinstance(route, APIRoute):
            continue
        try:
            endpoint_source = inspect.getsource(route.endpoint)
        except (OSError, TypeError):
            endpoint_source = ""
        haystack = f"{route.path} {route.endpoint.__name__} {endpoint_source}".lower()
        if not any(term in haystack for term in terms):
            continue
        for method in sorted(route.methods or set()):
            if method in {"HEAD", "OPTIONS"}:
                continue
            candidates.append((method, route.path, route.endpoint.__name__))
    return candidates


@pytest.mark.requirement("WS03-02-R10")
def test_admin_bootstrap_source_requires_existing_linked_provider_identity_and_no_reachable_bootstrap_route() -> None:
    import backend.routes.admin_user_routes as admin_user_routes
    import backend.scripts.bootstrap_admin as bootstrap_admin
    import backend.services.auth_account_service as auth_account_service

    bootstrap_module = ast.parse(inspect.getsource(bootstrap_admin))
    assert not any(
        isinstance(node, ast.Call) and _call_name(node.func) == "User"
        for node in ast.walk(bootstrap_module)
    )

    lookup_node = _parse_function(bootstrap_admin.get_active_user_by_email)
    lookup_calls = _call_names(lookup_node)
    lookup_source = inspect.getsource(bootstrap_admin.get_active_user_by_email)
    assert "scalar" in lookup_calls
    assert "lower" in lookup_calls
    assert "User.email" in lookup_source
    assert 'User.account_status == "active"' in lookup_source
    assert "User.deleted_at.is_(None)" in lookup_source

    verify_node = _parse_function(bootstrap_admin.verify_firebase_user)
    verify_calls = _call_names(verify_node)
    verify_source = inspect.getsource(bootstrap_admin.verify_firebase_user)
    assert "initialize_firebase_admin" in verify_calls
    assert "get_user_by_email" in verify_calls
    assert "firebase_user.disabled" in verify_source
    assert "user.auth_user_id != firebase_user.uid" in verify_source

    bootstrap_node = _parse_function(bootstrap_admin.bootstrap_admin)
    bootstrap_calls = _call_names(bootstrap_node)
    assert "get_active_user_by_email" in bootstrap_calls
    assert "verify_firebase_user" in bootstrap_calls
    assert "add_missing_user_context_rows" in bootstrap_calls
    assert "No active app user exists for that email." in inspect.getsource(
        bootstrap_admin.bootstrap_admin
    )
    assert "That app user is not linked to a Firebase Auth account." in inspect.getsource(
        bootstrap_admin.bootstrap_admin
    )

    role_assignments = _attribute_assignments(bootstrap_node, "role")
    assert len(role_assignments) == 1
    role_assignment = role_assignments[0]
    role_value = getattr(role_assignment, "value", None)
    assert isinstance(role_value, ast.Constant)
    assert role_value.value == "admin"
    verify_lines = [
        node.lineno
        for node in ast.walk(bootstrap_node)
        if isinstance(node, ast.Call)
        and _call_name(node.func) == "verify_firebase_user"
    ]
    assert verify_lines
    assert max(verify_lines) < role_assignment.lineno

    sync_node = _parse_function(auth_account_service.sync_user_workflow)
    assert _new_user_role_values(sync_node) == set()

    role_route_source = inspect.getsource(admin_user_routes.change_admin_user_role_route)
    assert "require_recent_active_admin" in role_route_source
    assert "change_user_role(" in role_route_source
    assert _admin_bootstrap_route_candidates() == []


@pytest.mark.requirement("WS03-02-R9", "WS03-02-R10")
def test_final_active_admin_cannot_be_demoted_suspended_or_deleted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import backend.services.account_deletion_service as account_deletion_service
    import backend.services.admin_user_delete_service as admin_user_delete_service
    from backend.schemas.admin_user_schema import (
        AdminUserDeleteCreate,
        AdminUserSuspendCreate,
    )
    from backend.schemas.auth_schema import AuthDeleteAccountRequest
    from backend.services.account_deletion_service import delete_account_workflow
    from backend.services.admin_user_account_service import suspend_admin_user
    from backend.services.admin_user_delete_service import delete_admin_user
    from backend.services.admin_user_role_service import change_user_role

    uid = f"ws03-02-final-admin-{uuid.uuid4()}"
    email = f"ws03-02-final-admin-{uuid.uuid4()}@example.invalid"
    _install_provider_identity(monkeypatch, uid=uid, email=email)
    admin_id = _create_user(auth_user_id=uid, email=email, role="admin")
    provider_calls: list[str] = []

    def provider_delete(auth_user_id: str) -> None:
        provider_calls.append(auth_user_id)
        raise AssertionError("final-admin rejection must occur before provider delete")

    monkeypatch.setattr(account_deletion_service, "delete_firebase_user", provider_delete)
    monkeypatch.setattr(admin_user_delete_service, "delete_firebase_user", provider_delete)

    with _session() as db:
        admin_user = db.get(account_deletion_service.User, admin_id)
        assert admin_user is not None
        with pytest.raises(HTTPException) as exc_info:
            change_user_role(
                db,
                admin_user=admin_user,
                user_id=admin_id,
                payload=_role_payload(f"role-{uuid.uuid4()}"),
            )
        assert exc_info.value.status_code == 409
        assert exc_info.value.detail == "The last active admin cannot be demoted."

    with _session() as db:
        admin_user = db.get(account_deletion_service.User, admin_id)
        assert admin_user is not None
        with pytest.raises(HTTPException) as exc_info:
            suspend_admin_user(
                db,
                admin_user=admin_user,
                user_id=admin_id,
                payload=AdminUserSuspendCreate(
                    preview_token="a" * 64,
                    reason="final admin guard proof",
                    idempotency_key=f"suspend-{uuid.uuid4()}",
                ),
            )
        assert exc_info.value.status_code == 409
        assert exc_info.value.detail == "The last active admin cannot be suspended."

    with _session() as db:
        with pytest.raises(HTTPException) as exc_info:
            delete_account_workflow(
                AuthDeleteAccountRequest(confirmation="DELETE"),
                "Bearer valid-token",
                db,
            )
        assert exc_info.value.status_code == 409
        assert exc_info.value.detail == "The last active admin cannot be deleted."

    with _session() as db:
        admin_user = db.get(admin_user_delete_service.User, admin_id)
        assert admin_user is not None
        with pytest.raises(HTTPException) as exc_info:
            delete_admin_user(
                db,
                admin_user=admin_user,
                user_id=admin_id,
                payload=AdminUserDeleteCreate(
                    preview_token="b" * 64,
                    reason="final admin guard proof",
                    idempotency_key=f"delete-{uuid.uuid4()}",
                ),
            )
        assert exc_info.value.status_code == 409
        assert exc_info.value.detail == "The last active admin cannot be deleted."

    assert provider_calls == []
    assert _user_snapshot(admin_id) == {
        "auth_user_id": uid,
        "email": email,
        "account_status": "active",
        "role": "admin",
        "deleted_at": None,
    }


@pytest.mark.requirement("WS03-02-R9", "WS03-02-R10")
def test_non_final_admin_can_be_demoted_when_another_active_admin_remains() -> None:
    from backend.services.admin_user_role_service import change_user_role

    acting_id = _create_user(
        auth_user_id=f"ws03-02-admin-actor-{uuid.uuid4()}",
        email=f"ws03-02-admin-actor-{uuid.uuid4()}@example.invalid",
        role="admin",
    )
    target_id = _create_user(
        auth_user_id=f"ws03-02-admin-target-{uuid.uuid4()}",
        email=f"ws03-02-admin-target-{uuid.uuid4()}@example.invalid",
        role="admin",
    )

    with _session() as db:
        from backend.models import User

        acting_admin = db.get(User, acting_id)
        assert acting_admin is not None
        result = change_user_role(
            db,
            admin_user=acting_admin,
            user_id=target_id,
            payload=_role_payload(f"non-final-{uuid.uuid4()}"),
        )

    assert result.previous_role == "admin"
    assert result.role == "player"
    assert _user_snapshot(target_id)["role"] == "player"
    assert _active_admin_count() == 1


def _concurrent_demote(
    acting_user_id: uuid.UUID,
    target_user_id: uuid.UUID,
    barrier: threading.Barrier,
) -> tuple[object, ...]:
    from backend.models import User
    from backend.services.admin_user_role_service import change_user_role

    with _session() as db:
        backend_pid = int(db.scalar(text("select pg_backend_pid()")) or 0)
        admin_user = db.get(User, acting_user_id)
        assert admin_user is not None
        barrier.wait(timeout=10)
        try:
            result = change_user_role(
                db,
                admin_user=admin_user,
                user_id=target_user_id,
                payload=_role_payload(f"race-{acting_user_id}-{uuid.uuid4()}"),
            )
            return ("ok", str(result.user_id), result.previous_role, result.role, backend_pid)
        except HTTPException as exc:
            return ("http", exc.status_code, exc.detail, backend_pid)


@pytest.mark.requirement("WS03-02-R9", "WS03-02-R10")
def test_concurrent_admin_demotions_cannot_leave_zero_active_admins() -> None:
    admin_a_id = _create_user(
        auth_user_id=f"ws03-02-admin-race-a-{uuid.uuid4()}",
        email=f"ws03-02-admin-race-a-{uuid.uuid4()}@example.invalid",
        role="admin",
    )
    admin_b_id = _create_user(
        auth_user_id=f"ws03-02-admin-race-b-{uuid.uuid4()}",
        email=f"ws03-02-admin-race-b-{uuid.uuid4()}@example.invalid",
        role="admin",
    )
    barrier = threading.Barrier(2)

    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="admin-demote") as executor:
        results = [
            future.result()
            for future in (
                executor.submit(_concurrent_demote, admin_a_id, admin_b_id, barrier),
                executor.submit(_concurrent_demote, admin_b_id, admin_a_id, barrier),
            )
    ]

    assert len({result[-1] for result in results}) == 2
    assert len([result for result in results if result[0] == "ok"]) == 1
    http_results = [result for result in results if result[0] == "http"]
    assert len(http_results) == 1
    assert http_results[0][1:3] == (
        409,
        "The last active admin cannot be demoted.",
    )
    assert _active_admin_count() == 1
