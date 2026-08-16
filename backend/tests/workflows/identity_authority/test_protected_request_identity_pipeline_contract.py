from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.suite_type("ordinary")


def _provider_payload(
    *,
    uid: str = "firebase-user",
    email: str = "Current.Email@example.invalid",
    email_verified: bool = True,
    **extra: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "uid": uid,
        "email": email,
        "email_verified": email_verified,
        "auth_time": 1_700_000_000,
    }
    payload.update(extra)
    return payload


def _install_token_verifier(
    monkeypatch: pytest.MonkeyPatch,
    *,
    payload: dict[str, object] | None = None,
) -> list[str]:
    import backend.services.auth_service as auth_service

    calls: list[str] = []
    token_payload = payload or _provider_payload()

    def verify_token(token: str) -> dict[str, object]:
        calls.append(token)
        if token != "valid-token":
            raise ValueError("invalid synthetic token")
        return dict(token_payload)

    monkeypatch.setattr(auth_service, "verify_firebase_token", verify_token)
    return calls


def _create_user(
    *,
    auth_user_id: str = "firebase-user",
    email: str = "local-user@example.invalid",
    role: str = "player",
    account_status: str = "active",
    deleted_at: datetime | None = None,
    email_verified_at: datetime | None = None,
) -> uuid.UUID:
    from backend.database import SessionLocal
    from backend.models import User

    user = User(
        id=uuid.uuid4(),
        auth_user_id=auth_user_id,
        role=role,
        email=email,
        email_verified_at=email_verified_at,
        phone=f"+1555{uuid.uuid4().hex[:10]}",
        first_name="Identity",
        last_name="User",
        date_of_birth=date(1990, 1, 1),
        account_status=account_status,
        hosting_status="eligible",
        deleted_at=deleted_at,
    )
    with SessionLocal() as db:
        db.add(user)
        db.commit()
        return user.id


def _auth_headers(token: str = "valid-token") -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.requirement("WS03-01-R1", "WS03-01-R2")
@pytest.mark.parametrize(
    ("headers", "expected_detail"),
    [
        ({}, "Missing authorization header."),
        ({"Authorization": "Basic valid-token"}, "Invalid authorization header."),
        ({"Authorization": "Bearer"}, "Invalid authorization header."),
    ],
)
def test_protected_requests_reject_missing_or_malformed_bearer_credentials(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    headers: dict[str, str],
    expected_detail: str,
) -> None:
    calls = _install_token_verifier(monkeypatch)

    response = client.get("/users/me", headers=headers)

    assert response.status_code == 401
    assert response.json()["detail"] == expected_detail
    assert calls == []


@pytest.mark.requirement("WS03-01-R1")
def test_credentials_are_not_accepted_from_query_or_cookie_locations(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _install_token_verifier(monkeypatch)
    client.cookies.set("Authorization", "Bearer valid-token")

    response = client.get("/users/me?access_token=valid-token")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing authorization header."
    assert calls == []


@pytest.mark.requirement("WS03-01-R1", "WS03-01-R2", "WS03-01-R3")
def test_provider_identity_is_established_before_local_user_authority(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _install_token_verifier(
        monkeypatch,
        payload=_provider_payload(
            uid="provider-uid",
            email="provider-current@example.invalid",
            email_verified=True,
        ),
    )
    user_id = _create_user(
        auth_user_id="provider-uid",
        email="local-snapshot@example.invalid",
    )

    response = client.get("/users/me", headers=_auth_headers())

    assert response.status_code == 200
    assert response.json()["id"] == str(user_id)
    assert response.json()["email"] == "local-snapshot@example.invalid"
    assert calls == ["valid-token"]


@pytest.mark.requirement("WS03-01-R3")
def test_valid_provider_token_alone_cannot_grant_local_access(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_token_verifier(
        monkeypatch,
        payload=_provider_payload(uid="missing-local-user"),
    )

    response = client.get("/users/me", headers=_auth_headers())

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found."


@pytest.mark.requirement("WS03-01-R3")
@pytest.mark.parametrize(
    ("account_status", "deleted", "expected_status", "expected_detail"),
    [
        ("active", False, 200, None),
        ("suspended", False, 403, "Active account required."),
        ("pending_deletion", False, 404, "User not found."),
        ("deleted", True, 404, "User not found."),
    ],
)
def test_local_account_state_is_applied_after_provider_identity(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    account_status: str,
    deleted: bool,
    expected_status: int,
    expected_detail: str | None,
) -> None:
    _install_token_verifier(monkeypatch)
    _create_user(
        account_status=account_status,
        deleted_at=datetime.now(timezone.utc) if deleted else None,
    )

    response = client.get("/my-games", headers=_auth_headers())

    assert response.status_code == expected_status
    if expected_detail is None:
        assert response.json()["items"] == []
    else:
        assert response.json()["detail"] == expected_detail


@pytest.mark.requirement("WS03-01-R1", "WS03-01-R2", "WS03-01-R3")
def test_request_scoped_identity_is_sanitized_from_raw_provider_claims(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services.auth_service import (
        VerifiedFirebaseIdentity,
        get_decoded_firebase_token,
        get_verified_firebase_identity_from_authorization,
    )

    _install_token_verifier(
        monkeypatch,
        payload=_provider_payload(
            uid="firebase-user",
            email="MIXED.CASE@example.invalid",
            email_verified=True,
            admin=True,
            role="admin",
            permissions=["*"],
            raw_provider_claim="not-business-authority",
        ),
    )

    identity = get_verified_firebase_identity_from_authorization("Bearer valid-token")
    decoded = get_decoded_firebase_token("Bearer valid-token")

    assert identity == VerifiedFirebaseIdentity(
        auth_user_id="firebase-user",
        email="mixed.case@example.invalid",
        email_verified=True,
        authenticated_at=datetime.fromtimestamp(1_700_000_000, tz=timezone.utc),
        provider_account_active=True,
    )
    assert not hasattr(identity, "admin")
    assert set(decoded) == {"uid", "email", "email_verified"}
    assert decoded == {
        "uid": "firebase-user",
        "email": "mixed.case@example.invalid",
        "email_verified": True,
    }
