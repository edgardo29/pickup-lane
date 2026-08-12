from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
import pytest

from backend.database import SessionLocal, get_db
from backend.models import User
from backend.services.auth_service import require_active_user
from backend.tests.support.factories import create_user


class ExpiredCredentialError(Exception):
    pass


class RevokedCredentialError(Exception):
    pass


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _build_active_user_probe_client() -> TestClient:
    app = FastAPI()

    @app.get("/active-user-probe")
    def active_user_probe(current_user: User = Depends(require_active_user)):
        return {"id": str(current_user.id)}

    def override_db():
        with SessionLocal() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    return TestClient(app)


def _stub_firebase_tokens(
    monkeypatch: pytest.MonkeyPatch,
    token_payloads: dict[str, dict],
    token_errors: dict[str, Exception] | None = None,
) -> None:
    errors = token_errors or {}

    def verify_firebase_token(id_token: str) -> dict:
        if id_token in errors:
            raise errors[id_token]
        payload = token_payloads.get(id_token)
        if payload is None:
            raise ValueError("Invalid token")
        return payload

    monkeypatch.setattr(
        "backend.services.auth_service.verify_firebase_token",
        verify_firebase_token,
    )


def _set_user_state(
    user_id: str,
    *,
    account_status: str,
    deleted_at: datetime | None = None,
) -> None:
    with SessionLocal() as db:
        db_user = db.get(User, UUID(user_id))
        assert db_user is not None
        db_user.account_status = account_status
        db_user.deleted_at = deleted_at
        db.commit()


def test_active_user_dependency_accepts_verified_active_app_user(
    monkeypatch: pytest.MonkeyPatch,
):
    user = create_user()
    _stub_firebase_tokens(
        monkeypatch,
        {
            "valid-token": {
                "uid": user["auth_user_id"],
                "email": user["email"],
            }
        },
    )

    response = _build_active_user_probe_client().get(
        "/active-user-probe",
        headers=_auth_headers("valid-token"),
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"id": user["id"]}


@pytest.mark.parametrize(
    "authorization",
    [
        "Token malformed-token",
        "Bearer",
    ],
)
def test_active_user_dependency_rejects_malformed_credentials(
    authorization: str,
):
    response = _build_active_user_probe_client().get(
        "/active-user-probe",
        headers={"Authorization": authorization},
    )

    assert response.status_code == 401, response.text
    assert response.json()["detail"] == "Invalid authorization header."


@pytest.mark.parametrize(
    ("token", "exception"),
    [
        ("invalid-token", ValueError("Invalid token")),
        ("expired-token", ExpiredCredentialError("Expired token")),
        ("revoked-token", RevokedCredentialError("Revoked token")),
    ],
)
def test_active_user_dependency_rejects_invalid_expired_and_revoked_credentials(
    monkeypatch: pytest.MonkeyPatch,
    token: str,
    exception: Exception,
):
    _stub_firebase_tokens(monkeypatch, {}, {token: exception})

    response = _build_active_user_probe_client().get(
        "/active-user-probe",
        headers=_auth_headers(token),
    )

    assert response.status_code == 401, response.text
    assert response.json()["detail"] == "Invalid or expired authentication token."


def test_active_user_dependency_rejects_verified_identity_without_app_user(
    monkeypatch: pytest.MonkeyPatch,
):
    _stub_firebase_tokens(
        monkeypatch,
        {
            "missing-user-token": {
                "uid": "firebase-missing-user",
                "email": "missing-user@example.com",
            }
        },
    )

    response = _build_active_user_probe_client().get(
        "/active-user-probe",
        headers=_auth_headers("missing-user-token"),
    )

    assert response.status_code == 404, response.text
    assert response.json()["detail"] == "User not found."


@pytest.mark.parametrize(
    ("account_status", "deleted_at", "expected_status", "expected_detail"),
    [
        ("suspended", None, 403, "Active account required."),
        ("deleted", None, 403, "Active account required."),
        ("pending_deletion", None, 404, "User not found."),
        (
            "active",
            datetime(2026, 1, 1, tzinfo=UTC),
            404,
            "User not found.",
        ),
    ],
)
def test_active_user_dependency_rejects_inactive_product_account_states(
    monkeypatch: pytest.MonkeyPatch,
    account_status: str,
    deleted_at: datetime | None,
    expected_status: int,
    expected_detail: str,
):
    user = create_user()
    _set_user_state(
        user["id"],
        account_status=account_status,
        deleted_at=deleted_at,
    )
    _stub_firebase_tokens(
        monkeypatch,
        {
            "state-token": {
                "uid": user["auth_user_id"],
                "email": user["email"],
            }
        },
    )

    response = _build_active_user_probe_client().get(
        "/active-user-probe",
        headers=_auth_headers("state-token"),
    )

    assert response.status_code == expected_status, response.text
    assert response.json()["detail"] == expected_detail
