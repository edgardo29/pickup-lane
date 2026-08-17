from __future__ import annotations

import inspect
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import Depends as RouteDepends
from fastapi.params import Depends
from fastapi.testclient import TestClient

pytestmark = [
    pytest.mark.no_db_cleanup,
    pytest.mark.suite_type("ordinary"),
]


def _install_provider_identity(
    monkeypatch: pytest.MonkeyPatch,
    *,
    uid: str,
    email: str,
    auth_time: int | None,
) -> None:
    import backend.services.auth_service as auth_service

    payload: dict[str, object] = {
        "uid": uid,
        "email": email,
        "email_verified": True,
    }
    if auth_time is not None:
        payload["auth_time"] = auth_time

    def verify_token(token: str) -> dict[str, object]:
        if token != "valid-token":
            raise ValueError("invalid synthetic token")
        return dict(payload)

    monkeypatch.setattr(auth_service, "verify_firebase_token", verify_token)


def _auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer valid-token"}


def _active_admin_user(*, uid: str, email: str):
    from backend.models import User

    return User(
        id=uuid.uuid4(),
        auth_user_id=uid,
        role="admin",
        email=email,
        email_verified_at=datetime.now(timezone.utc),
        account_status="active",
    )


def _community_cancel_payload() -> dict[str, str]:
    return {
        "reason": "recent auth route boundary",
        "idempotency_key": "recent-auth-community-cancel",
    }


def _need_a_sub_remove_payload() -> dict[str, str]:
    return {
        "reason": "recent auth Need-a-Sub boundary",
        "idempotency_key": "recent-auth-need-a-sub-remove",
    }


def _assert_recent_auth_required_response(response) -> None:
    assert response.status_code == 403, response.text
    body = response.json()
    assert body["code"] == "AUTH.RECENT_AUTH_REQUIRED"
    assert body["message"] == "Confirm your identity to continue."
    assert body["detail"] == {
        "code": "AUTH.RECENT_AUTH_REQUIRED",
        "message": "Confirm your identity to continue.",
    }

    serialized_body = str(body)
    for fragment in (
        "valid-token",
        "auth_time",
        "password",
        "popup",
        "oauth",
        "credential",
        "provider exception",
        "Traceback",
        "verify_firebase_token",
    ):
        assert fragment not in serialized_body


def _dependency_default(function, parameter_name: str) -> Depends:
    default = inspect.signature(function).parameters[parameter_name].default
    assert isinstance(default, Depends)
    return default


def _install_admin_and_community_cancel_sentinel(
    app,
    monkeypatch: pytest.MonkeyPatch,
    *,
    admin_uid: str,
    admin_email: str,
) -> list[dict[str, object]]:
    import backend.routes.admin_community_routes as admin_community_routes
    import backend.services.auth_service as auth_service
    from backend.schemas import (
        AdminCommunityGameEnforcementActionResultRead,
        AdminCommunityGameEnforcementStateRead,
    )

    calls: list[dict[str, object]] = []
    active_admin = _active_admin_user(uid=admin_uid, email=admin_email)
    app.dependency_overrides[auth_service.require_active_admin] = lambda: active_admin
    app.dependency_overrides[admin_community_routes.get_db] = lambda: object()

    def cancel_sentinel(db, *, game_id, admin_user, payload):
        calls.append(
            {
                "game_id": game_id,
                "admin_user": admin_user,
                "payload": payload,
            }
        )
        return AdminCommunityGameEnforcementActionResultRead(
            game_id=game_id,
            enforcement_state=AdminCommunityGameEnforcementStateRead(
                public_visibility_status="visible",
                join_enforcement_status="open",
                game_status="cancelled",
                cancellation_source="admin",
            ),
            audit_action_id=uuid.uuid4(),
            notice_ids=[],
            idempotent_replay=False,
        )

    monkeypatch.setattr(
        admin_community_routes,
        "admin_cancel_community_game",
        cancel_sentinel,
    )
    return calls


def _install_admin_and_need_a_sub_remove_sentinel(
    app,
    monkeypatch: pytest.MonkeyPatch,
    *,
    admin_uid: str,
    admin_email: str,
) -> list[dict[str, object]]:
    import backend.routes.admin_need_a_sub_routes as admin_need_a_sub_routes
    import backend.services.auth_service as auth_service
    from backend.schemas import AdminNeedASubEnforcementActionResultRead

    calls: list[dict[str, object]] = []
    active_admin = _active_admin_user(uid=admin_uid, email=admin_email)
    app.dependency_overrides[auth_service.require_active_admin] = lambda: active_admin
    app.dependency_overrides[admin_need_a_sub_routes.get_db] = lambda: object()

    def remove_sentinel(db, *, post_id, admin_user, payload):
        calls.append(
            {
                "post_id": post_id,
                "admin_user": admin_user,
                "payload": payload,
            }
        )
        return AdminNeedASubEnforcementActionResultRead(
            post_id=post_id,
            post_status="removed",
            public_visibility_status="hidden",
            audit_action_id=uuid.uuid4(),
            notice_ids=[],
            closed_request_ids=[],
            idempotent_replay=False,
        )

    monkeypatch.setattr(
        admin_need_a_sub_routes,
        "remove_need_a_sub_post_by_admin",
        remove_sentinel,
    )
    return calls


@pytest.mark.no_db_cleanup
@pytest.mark.requirement("WS03-03A-R4")
def test_recent_auth_dependencies_layer_on_existing_identity_account_and_admin_guards() -> None:
    import backend.services.auth_service as auth_service

    recent_identity = _dependency_default(
        auth_service.require_recent_authentication,
        "identity",
    )
    recent_app_user_base = _dependency_default(
        auth_service.require_recent_app_user,
        "current_user",
    )
    recent_app_user_step_up = _dependency_default(
        auth_service.require_recent_app_user,
        "_identity",
    )
    recent_active_user_base = _dependency_default(
        auth_service.require_recent_active_user,
        "current_user",
    )
    recent_active_user_step_up = _dependency_default(
        auth_service.require_recent_active_user,
        "_identity",
    )
    recent_admin_base = _dependency_default(
        auth_service.require_recent_active_admin,
        "current_user",
    )
    recent_admin_step_up = _dependency_default(
        auth_service.require_recent_active_admin,
        "_identity",
    )

    assert recent_identity.dependency is auth_service.get_verified_firebase_identity
    assert recent_app_user_base.dependency is auth_service.get_current_app_user
    assert recent_app_user_step_up.dependency is auth_service.require_recent_authentication
    assert recent_active_user_base.dependency is auth_service.require_active_user
    assert (
        recent_active_user_step_up.dependency
        is auth_service.require_recent_authentication
    )
    assert recent_admin_base.dependency is auth_service.require_active_admin
    assert recent_admin_step_up.dependency is auth_service.require_recent_authentication

    assert (
        _dependency_default(auth_service.require_active_admin, "current_user").dependency
        is auth_service.require_verified_user
    )
    assert (
        _dependency_default(auth_service.require_verified_user, "current_user").dependency
        is auth_service.require_active_user
    )
    assert (
        _dependency_default(auth_service.require_active_user, "current_user").dependency
        is auth_service.get_current_app_user
    )


@pytest.mark.no_db_cleanup
@pytest.mark.requirement("WS03-03A-R4", "WS03-03A-R5")
def test_recent_auth_wrappers_do_not_replace_existing_workflow_safeguards() -> None:
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[4]
    sources = {
        "account": (repo_root / "backend/services/account_deletion_service.py").read_text(
            encoding="utf-8"
        ),
        "admin_delete": (
            repo_root / "backend/services/admin_user_delete_service.py"
        ).read_text(encoding="utf-8"),
        "admin_role": (repo_root / "backend/services/admin_user_role_service.py").read_text(
            encoding="utf-8"
        ),
        "admin_account": (
            repo_root / "backend/services/admin_user_account_service.py"
        ).read_text(encoding="utf-8"),
        "money_issue": (
            repo_root / "backend/services/admin_money_issue_service.py"
        ).read_text(encoding="utf-8"),
        "money_refund": (
            repo_root / "backend/services/admin_money_refund_service.py"
        ).read_text(encoding="utf-8"),
        "platform_notice": (
            repo_root / "backend/services/platform_notice_service.py"
        ).read_text(encoding="utf-8"),
        "official_cancel": (
            repo_root / "backend/services/game_cancellation_service.py"
        ).read_text(encoding="utf-8"),
    }

    assert "The last active admin cannot be deleted." in sources["account"]
    assert "The last active admin cannot be deleted." in sources["admin_delete"]
    assert "The last active admin cannot be demoted." in sources["admin_role"]
    assert "The last active admin cannot be suspended." in sources["admin_account"]
    assert "idempotency_key" in sources["admin_delete"]
    assert "idempotency_key" in sources["admin_role"]
    assert "idempotency_key" in sources["admin_account"]
    assert "idempotency_key" in sources["money_issue"]
    assert "idempotency_key" in sources["money_refund"]
    assert "idempotency_key" in sources["platform_notice"]
    assert "preview_token" in sources["official_cancel"]
    assert "record_admin_action" in sources["official_cancel"]


@pytest.mark.requirement("WS03-03A-R3", "WS03-03A-R5")
@pytest.mark.parametrize("claim_mode", ["missing", "stale"])
def test_recent_auth_denial_returns_safe_public_403_before_self_delete_side_effect(
    monkeypatch: pytest.MonkeyPatch,
    claim_mode: str,
) -> None:
    from backend.main import create_app
    from backend.services.auth_service import require_recent_authentication

    side_effects: list[str] = []
    stale_auth_time = int(
        (datetime.now(timezone.utc) - timedelta(minutes=6)).timestamp()
    )
    _install_provider_identity(
        monkeypatch,
        uid="recent-auth-denial",
        email="recent-auth-denial@example.invalid",
        auth_time=None if claim_mode == "missing" else stale_auth_time,
    )

    app = create_app()

    @app.get("/__recent-auth-probe")
    def recent_auth_probe(
        _identity=RouteDepends(require_recent_authentication),
    ) -> dict[str, bool]:
        side_effects.append("endpoint-called")
        return {"ok": True}

    with TestClient(app) as client:
        response = client.get("/__recent-auth-probe", headers=_auth_headers())

    assert response.status_code == 403, response.text
    body = response.json()
    assert body["code"] == "AUTH.RECENT_AUTH_REQUIRED"
    assert body["message"] == "Confirm your identity to continue."
    assert body["detail"] == {
        "code": "AUTH.RECENT_AUTH_REQUIRED",
        "message": "Confirm your identity to continue.",
    }

    serialized_body = str(body)
    forbidden_public_fragments = (
        "valid-token",
        "auth_time",
        "password",
        "popup",
        "oauth",
        "credential",
        "provider exception",
        "Traceback",
        "verify_firebase_token",
        str(stale_auth_time),
    )
    for fragment in forbidden_public_fragments:
        assert fragment not in serialized_body

    assert side_effects == []


@pytest.mark.requirement("WS03-03A-R3", "WS03-03A-R5")
@pytest.mark.parametrize("claim_mode", ["missing", "stale"])
def test_admin_community_cancel_rejects_missing_or_stale_recent_auth_before_service_execution(
    monkeypatch: pytest.MonkeyPatch,
    claim_mode: str,
) -> None:
    from backend.main import create_app

    admin_uid = "community-cancel-admin"
    admin_email = "community-cancel-admin@example.invalid"
    stale_auth_time = int(
        (datetime.now(timezone.utc) - timedelta(minutes=6)).timestamp()
    )
    _install_provider_identity(
        monkeypatch,
        uid=admin_uid,
        email=admin_email,
        auth_time=None if claim_mode == "missing" else stale_auth_time,
    )
    app = create_app()
    service_calls = _install_admin_and_community_cancel_sentinel(
        app,
        monkeypatch,
        admin_uid=admin_uid,
        admin_email=admin_email,
    )
    game_id = uuid.uuid4()

    try:
        with TestClient(app) as client:
            response = client.post(
                f"/admin/community-games/{game_id}/cancel",
                headers=_auth_headers(),
                json=_community_cancel_payload(),
            )
    finally:
        app.dependency_overrides.clear()

    _assert_recent_auth_required_response(response)
    assert str(stale_auth_time) not in str(response.json())
    assert service_calls == []


@pytest.mark.requirement("WS03-03A-R5")
def test_admin_community_cancel_with_fresh_recent_auth_reaches_route_workflow_sentinel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.main import create_app

    admin_uid = "fresh-community-cancel-admin"
    admin_email = "fresh-community-cancel-admin@example.invalid"
    _install_provider_identity(
        monkeypatch,
        uid=admin_uid,
        email=admin_email,
        auth_time=int(datetime.now(timezone.utc).timestamp()),
    )
    app = create_app()
    service_calls = _install_admin_and_community_cancel_sentinel(
        app,
        monkeypatch,
        admin_uid=admin_uid,
        admin_email=admin_email,
    )
    game_id = uuid.uuid4()

    try:
        with TestClient(app) as client:
            response = client.post(
                f"/admin/community-games/{game_id}/cancel",
                headers=_auth_headers(),
                json=_community_cancel_payload(),
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["game_id"] == str(game_id)
    assert body["enforcement_state"]["game_status"] == "cancelled"
    assert body["enforcement_state"]["cancellation_source"] == "admin"
    assert body["idempotent_replay"] is False

    assert len(service_calls) == 1
    call = service_calls[0]
    assert call["game_id"] == game_id
    assert call["admin_user"].auth_user_id == admin_uid
    assert call["payload"].reason == _community_cancel_payload()["reason"]
    assert call["payload"].idempotency_key == _community_cancel_payload()["idempotency_key"]


@pytest.mark.requirement("WS03-03A-R3", "WS03-03A-R5")
@pytest.mark.parametrize("claim_mode", ["missing", "stale"])
def test_admin_need_a_sub_remove_rejects_missing_or_stale_recent_auth_before_service_execution(
    monkeypatch: pytest.MonkeyPatch,
    claim_mode: str,
) -> None:
    from backend.main import create_app

    admin_uid = "need-a-sub-remove-admin"
    admin_email = "need-a-sub-remove-admin@example.invalid"
    stale_auth_time = int(
        (datetime.now(timezone.utc) - timedelta(minutes=6)).timestamp()
    )
    _install_provider_identity(
        monkeypatch,
        uid=admin_uid,
        email=admin_email,
        auth_time=None if claim_mode == "missing" else stale_auth_time,
    )
    app = create_app()
    service_calls = _install_admin_and_need_a_sub_remove_sentinel(
        app,
        monkeypatch,
        admin_uid=admin_uid,
        admin_email=admin_email,
    )
    post_id = uuid.uuid4()

    try:
        with TestClient(app) as client:
            response = client.post(
                f"/admin/need-a-sub/{post_id}/remove",
                headers=_auth_headers(),
                json=_need_a_sub_remove_payload(),
            )
    finally:
        app.dependency_overrides.clear()

    _assert_recent_auth_required_response(response)
    assert str(stale_auth_time) not in str(response.json())
    assert service_calls == []


@pytest.mark.requirement("WS03-03A-R5")
def test_admin_need_a_sub_remove_with_fresh_recent_auth_reaches_route_workflow_sentinel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.main import create_app

    admin_uid = "fresh-need-a-sub-remove-admin"
    admin_email = "fresh-need-a-sub-remove-admin@example.invalid"
    _install_provider_identity(
        monkeypatch,
        uid=admin_uid,
        email=admin_email,
        auth_time=int(datetime.now(timezone.utc).timestamp()),
    )
    app = create_app()
    service_calls = _install_admin_and_need_a_sub_remove_sentinel(
        app,
        monkeypatch,
        admin_uid=admin_uid,
        admin_email=admin_email,
    )
    post_id = uuid.uuid4()

    try:
        with TestClient(app) as client:
            response = client.post(
                f"/admin/need-a-sub/{post_id}/remove",
                headers=_auth_headers(),
                json=_need_a_sub_remove_payload(),
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["post_id"] == str(post_id)
    assert body["post_status"] == "removed"
    assert body["public_visibility_status"] == "hidden"
    assert body["idempotent_replay"] is False

    assert len(service_calls) == 1
    call = service_calls[0]
    assert call["post_id"] == post_id
    assert call["admin_user"].auth_user_id == admin_uid
    assert call["payload"].reason == _need_a_sub_remove_payload()["reason"]
    assert call["payload"].idempotency_key == _need_a_sub_remove_payload()["idempotency_key"]
