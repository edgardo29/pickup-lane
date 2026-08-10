from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from inspect import signature
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, select

import backend.firebase_admin_client as firebase_admin_client
from backend.services import auth_account_service
from backend.database import SessionLocal, get_db
from backend.main import app as main_app
from backend.models import Game, User
from backend.services.auth_service import (
    require_active_admin,
    require_active_user,
    require_verified_user,
)
from backend.tests.helpers import create_venue, set_user_role
from backend.tests.support.factories import create_user


@dataclass(frozen=True)
class SyntheticFirebaseUser:
    uid: str
    email: str | None
    email_verified: bool
    disabled: bool = False


class SyntheticProviderInfrastructureError(Exception):
    pass


def _auth_headers(label: str) -> dict[str, str]:
    return {"Authorization": f"Bearer synthetic-{label}"}


def _token_label(headers: dict[str, str]) -> str:
    return headers["Authorization"].removeprefix("Bearer ")


def _build_dependency_probe_client() -> TestClient:
    app = FastAPI()

    @app.get("/active")
    def active_probe(current_user: User = Depends(require_active_user)):
        return {"id": str(current_user.id)}

    @app.post("/verified")
    def verified_probe(current_user: User = Depends(require_verified_user)):
        return {"id": str(current_user.id)}

    @app.post("/admin")
    def admin_probe(current_user: User = Depends(require_active_admin)):
        return {"id": str(current_user.id)}

    def override_db():
        with SessionLocal() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    return TestClient(app)


def _install_synthetic_firebase_provider(
    monkeypatch: pytest.MonkeyPatch,
    *,
    tokens: dict[str, dict],
    users: dict[str, SyntheticFirebaseUser],
    token_errors: dict[str, Exception] | None = None,
    user_errors: dict[str, Exception] | None = None,
) -> dict[str, list[dict[str, object]]]:
    calls: dict[str, list[dict[str, object]]] = {"verify": [], "get_user": []}
    synthetic_app = object()
    errors_by_token = token_errors or {}
    errors_by_user = user_errors or {}

    def initialize_firebase_admin():
        return synthetic_app

    def verify_id_token(
        id_token,
        *,
        app=None,
        check_revoked=False,
        clock_skew_seconds=0,
    ):
        calls["verify"].append(
            {
                "app": app,
                "check_revoked": check_revoked,
                "clock_skew_seconds": clock_skew_seconds,
            }
        )
        if id_token in errors_by_token:
            raise errors_by_token[id_token]
        if id_token not in tokens:
            raise ValueError("Synthetic credential is invalid.")
        return tokens[id_token]

    def get_user(uid, *, app=None):
        calls["get_user"].append({"uid": uid, "app": app})
        if uid in errors_by_user:
            raise errors_by_user[uid]
        user = users[uid]
        if user.disabled:
            raise firebase_admin_client.auth.UserDisabledError(
                "Synthetic provider user is disabled."
            )
        return user

    monkeypatch.setattr(
        firebase_admin_client,
        "initialize_firebase_admin",
        initialize_firebase_admin,
    )
    monkeypatch.setattr(firebase_admin_client.auth, "verify_id_token", verify_id_token)
    monkeypatch.setattr(firebase_admin_client.auth, "get_user", get_user)
    return calls


def _load_user(user_id: str) -> User:
    with SessionLocal() as db:
        db_user = db.get(User, UUID(user_id))
        assert db_user is not None
        db.expunge(db_user)
        return db_user


def _set_user_state(
    user_id: str,
    *,
    account_status: str = "active",
    role: str | None = None,
    email_verified_at: datetime | None = None,
) -> None:
    with SessionLocal() as db:
        db_user = db.get(User, UUID(user_id))
        assert db_user is not None
        db_user.account_status = account_status
        db_user.email_verified_at = email_verified_at
        if role is not None:
            db_user.role = role
        db.commit()


def _game_count() -> int:
    with SessionLocal() as db:
        return db.scalar(select(func.count()).select_from(Game)) or 0


def test_firebase_verification_uses_bound_app_revocation_and_user_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = create_user()
    token = _token_label(_auth_headers("valid"))
    calls = _install_synthetic_firebase_provider(
        monkeypatch,
        tokens={token: {"uid": user["auth_user_id"], "email": "stale@example.test"}},
        users={
            user["auth_user_id"]: SyntheticFirebaseUser(
                uid=user["auth_user_id"],
                email=user["email"],
                email_verified=True,
            )
        },
    )

    response = _build_dependency_probe_client().get(
        "/active",
        headers=_auth_headers("valid"),
    )

    assert response.status_code == status.HTTP_200_OK, response.text
    assert response.json() == {"id": user["id"]}
    assert calls["verify"] == [
        {
            "app": calls["get_user"][0]["app"],
            "check_revoked": True,
            "clock_skew_seconds": firebase_admin_client.FIREBASE_TOKEN_CLOCK_SKEW_SECONDS,
        }
    ]
    assert calls["get_user"] == [
        {
            "uid": user["auth_user_id"],
            "app": calls["verify"][0]["app"],
        }
    ]


@pytest.mark.parametrize(
    ("token_label", "token_error", "expected_status"),
    [
        ("malformed", ValueError("Synthetic credential is malformed."), 401),
        (
            "expired",
            firebase_admin_client.auth.ExpiredIdTokenError(
                "Synthetic credential is expired.",
                cause=None,
            ),
            401,
        ),
        (
            "wrong-project",
            firebase_admin_client.auth.InvalidIdTokenError(
                "Synthetic credential has the wrong audience."
            ),
            401,
        ),
        (
            "revoked",
            firebase_admin_client.auth.RevokedIdTokenError(
                "Synthetic credential is revoked."
            ),
            401,
        ),
        (
            "provider-unavailable",
            firebase_admin_client.auth.CertificateFetchError(
                "Synthetic provider certificates unavailable.",
                cause=None,
            ),
            503,
        ),
    ],
)
def test_firebase_authentication_failures_and_provider_unavailability_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    token_label: str,
    token_error: Exception,
    expected_status: int,
) -> None:
    token = _token_label(_auth_headers(token_label))
    _install_synthetic_firebase_provider(
        monkeypatch,
        tokens={},
        users={},
        token_errors={token: token_error},
    )

    response = _build_dependency_probe_client().get(
        "/active",
        headers=_auth_headers(token_label),
    )

    assert response.status_code == expected_status, response.text
    assert "synthetic-" not in response.text


def test_auth_account_provider_config_errors_are_generic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unavailable_email_lookup(_email):
        raise firebase_admin_client.FirebaseAdminConfigError(
            "Synthetic setup detail that must stay private."
        )

    def unavailable_user_delete(_auth_user_id):
        raise firebase_admin_client.FirebaseAdminConfigError(
            "Synthetic setup detail that must stay private."
        )

    monkeypatch.setattr(
        auth_account_service,
        "firebase_email_exists",
        unavailable_email_lookup,
    )
    monkeypatch.setattr(
        auth_account_service,
        "get_auth_user_id_from_token",
        lambda _authorization: "synthetic-auth-user",
    )
    monkeypatch.setattr(
        auth_account_service,
        "delete_firebase_user",
        unavailable_user_delete,
    )

    with SessionLocal() as db:
        with pytest.raises(HTTPException) as availability_error:
            auth_account_service.check_email_availability_workflow(
                "synthetic-email@example.test",
                db,
            )
        with pytest.raises(HTTPException) as cleanup_error:
            auth_account_service.cleanup_unfinished_account_workflow(
                "Bearer synthetic-token",
                db,
            )

    assert availability_error.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert cleanup_error.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert "Synthetic setup detail" not in str(availability_error.value.detail)
    assert "Synthetic setup detail" not in str(cleanup_error.value.detail)


@pytest.mark.parametrize(
    "provider_failure",
    [
        firebase_admin_client.auth.UserDisabledError(
            "Synthetic provider user is disabled."
        ),
        firebase_admin_client.auth.UserNotFoundError(
            "Synthetic provider user is missing."
        ),
    ],
)
def test_disabled_or_deleted_provider_user_is_not_accepted(
    monkeypatch: pytest.MonkeyPatch,
    provider_failure: Exception,
) -> None:
    user = create_user()
    token = _token_label(_auth_headers("provider-user-failure"))
    _install_synthetic_firebase_provider(
        monkeypatch,
        tokens={token: {"uid": user["auth_user_id"]}},
        users={},
        user_errors={user["auth_user_id"]: provider_failure},
    )

    response = _build_dependency_probe_client().get(
        "/active",
        headers=_auth_headers("provider-user-failure"),
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED, response.text
    assert "synthetic-" not in response.text


def test_unverified_provider_state_clears_stale_snapshot_and_blocks_verified_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = create_user()
    _set_user_state(
        user["id"],
        email_verified_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    token = _token_label(_auth_headers("verification-lost"))
    provider_users = {
        user["auth_user_id"]: SyntheticFirebaseUser(
            uid=user["auth_user_id"],
            email=user["email"],
            email_verified=False,
        )
    }
    _install_synthetic_firebase_provider(
        monkeypatch,
        tokens={token: {"uid": user["auth_user_id"]}},
        users=provider_users,
    )

    denied_response = _build_dependency_probe_client().post(
        "/verified",
        headers=_auth_headers("verification-lost"),
    )

    assert denied_response.status_code == status.HTTP_403_FORBIDDEN, denied_response.text
    assert _load_user(user["id"]).email_verified_at is None

    provider_users[user["auth_user_id"]] = SyntheticFirebaseUser(
        uid=user["auth_user_id"],
        email=user["email"],
        email_verified=True,
    )
    allowed_response = _build_dependency_probe_client().post(
        "/verified",
        headers=_auth_headers("verification-lost"),
    )

    assert allowed_response.status_code == status.HTTP_200_OK, allowed_response.text
    assert _load_user(user["id"]).email_verified_at is not None


def test_verified_admin_requires_current_provider_verification_and_local_admin_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = create_user()
    _set_user_state(admin["id"], role="admin")
    token = _token_label(_auth_headers("admin"))
    provider_users = {
        admin["auth_user_id"]: SyntheticFirebaseUser(
            uid=admin["auth_user_id"],
            email=admin["email"],
            email_verified=False,
        )
    }
    _install_synthetic_firebase_provider(
        monkeypatch,
        tokens={token: {"uid": admin["auth_user_id"]}},
        users=provider_users,
    )

    client = _build_dependency_probe_client()
    unverified_response = client.post("/admin", headers=_auth_headers("admin"))
    assert unverified_response.status_code == status.HTTP_403_FORBIDDEN

    provider_users[admin["auth_user_id"]] = SyntheticFirebaseUser(
        uid=admin["auth_user_id"],
        email=admin["email"],
        email_verified=True,
    )
    verified_response = client.post("/admin", headers=_auth_headers("admin"))
    assert verified_response.status_code == status.HTTP_200_OK, verified_response.text

    _set_user_state(admin["id"], role="player")
    demoted_response = client.post("/admin", headers=_auth_headers("admin"))
    assert demoted_response.status_code == status.HTTP_403_FORBIDDEN


def test_profile_update_cannot_mutate_firebase_owned_email_but_auth_sync_can(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    user = create_user()
    provider_email = f"provider-{user['id']}@example.com"
    token = _token_label(_auth_headers("profile"))
    _install_synthetic_firebase_provider(
        monkeypatch,
        tokens={token: {"uid": user["auth_user_id"]}},
        users={
            user["auth_user_id"]: SyntheticFirebaseUser(
                uid=user["auth_user_id"],
                email=provider_email,
                email_verified=True,
            )
        },
    )

    rejected_update = client.patch(
        "/users/me",
        headers=_auth_headers("profile"),
        json={"email": "ordinary-update@example.com"},
    )

    assert rejected_update.status_code == 422
    assert _load_user(user["id"]).email == user["email"]

    sync_response = client.get("/auth/me", headers=_auth_headers("profile"))

    assert sync_response.status_code == status.HTTP_200_OK, sync_response.text
    assert _load_user(user["id"]).email == provider_email


def test_token_transport_remains_header_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = create_user()
    token = _token_label(_auth_headers("transport"))
    _install_synthetic_firebase_provider(
        monkeypatch,
        tokens={token: {"uid": user["auth_user_id"]}},
        users={
            user["auth_user_id"]: SyntheticFirebaseUser(
                uid=user["auth_user_id"],
                email=user["email"],
                email_verified=True,
            )
        },
    )
    client = _build_dependency_probe_client()

    assert client.get("/active", params={"id_token": token}).status_code == 401
    assert client.request("GET", "/active", json={"id_token": token}).status_code == 401

    accepted_response = client.get("/active", headers=_auth_headers("transport"))
    assert accepted_response.status_code == status.HTTP_200_OK, accepted_response.text


def test_representative_sensitive_route_families_use_verified_dependencies() -> None:
    expected_verified_routes = {
        ("POST", "/games/{game_id}/join"),
        ("POST", "/games/{game_id}/booking-guests/add"),
        ("POST", "/checkout/games/{game_id}/payment-intent"),
        ("POST", "/community-games/publish"),
        ("PUT", "/community-game-details/games/{game_id}/host-edit"),
        ("POST", "/need-a-sub/posts"),
        ("POST", "/need-a-sub/posts/{sub_post_id}/requests"),
        ("POST", "/chat-messages"),
        ("POST", "/game-chats/for-game/{game_id}"),
        ("POST", "/need-a-sub/posts/{sub_post_id}/chat"),
        ("POST", "/need-a-sub/posts/{sub_post_id}/chat/messages"),
    }
    expected_read_routes = {
        ("GET", "/games/{game_id}"),
        ("GET", "/chat-messages"),
        ("GET", "/need-a-sub/posts/{sub_post_id}/chat/messages"),
    }

    for method, path in expected_verified_routes:
        dependency_calls = _direct_route_dependencies(method, path)
        assert require_verified_user in dependency_calls

    for method, path in expected_read_routes:
        dependency_calls = _direct_route_dependencies(method, path)
        assert require_verified_user not in dependency_calls

    admin_dependencies = _direct_route_dependencies("GET", "/users")
    assert require_active_admin in admin_dependencies
    assert (
        signature(require_active_admin).parameters["current_user"].default.dependency
        is require_verified_user
    )


def test_unverified_admin_game_create_is_denied_before_game_write(
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
) -> None:
    admin = create_user()
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    token = _token_label(_auth_headers("unverified-admin"))
    _install_synthetic_firebase_provider(
        monkeypatch,
        tokens={token: {"uid": admin["auth_user_id"]}},
        users={
            admin["auth_user_id"]: SyntheticFirebaseUser(
                uid=admin["auth_user_id"],
                email=admin["email"],
                email_verified=False,
            )
        },
    )
    before_count = _game_count()

    response = client.post(
        "/games",
        headers=_auth_headers("unverified-admin"),
        json={
            "game_type": "official",
            "title": "Synthetic WS03 Match",
            "venue_id": venue["id"],
            "starts_at": "2026-09-01T18:00:00+00:00",
            "ends_at": "2026-09-01T19:00:00+00:00",
            "timezone": "America/Chicago",
            "format_label": "5v5",
            "environment_type": "indoor",
            "total_spots": 10,
            "price_per_player_cents": 1200,
        },
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN, response.text
    assert _game_count() == before_count


def _direct_route_dependencies(method: str, path: str) -> list[object]:
    for route in main_app.routes:
        if getattr(route, "path", None) == path and method in getattr(route, "methods", set()):
            return [dependency.call for dependency in route.dependant.dependencies]
    raise AssertionError(f"Route {method} {path} was not found.")
