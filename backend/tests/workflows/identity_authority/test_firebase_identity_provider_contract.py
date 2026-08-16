from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import backend.firebase_admin_client as firebase_client
from backend.firebase_admin_client import (
    FIREBASE_TOKEN_CLOCK_SKEW_SECONDS,
    FirebaseAdminConfigError,
    FirebaseIdentityUnavailableError,
)

pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.suite_type("ordinary")]

SYNTHETIC_PROJECT_ID = "pickup-lane-synthetic"
SYNTHETIC_CREDENTIAL_JSON = '{"type":"service_account","project_id":"synthetic"}'


class _AuthFake:
    class CertificateFetchError(Exception):
        pass

    class ExpiredIdTokenError(Exception):
        pass

    class InvalidIdTokenError(Exception):
        pass

    class RevokedIdTokenError(Exception):
        pass

    class UserDisabledError(Exception):
        pass

    class UserNotFoundError(Exception):
        pass

    def __init__(
        self,
        *,
        decoded_token: dict | None = None,
        user_record: SimpleNamespace | None = None,
        verify_exc: Exception | None = None,
        get_user_exc: Exception | None = None,
    ) -> None:
        self.decoded_token = decoded_token or {
            "uid": "firebase-uid",
            "email": "token-email@example.invalid",
            "email_verified": False,
        }
        self.user_record = user_record or SimpleNamespace(
            uid="firebase-uid",
            email="provider-email@example.invalid",
            email_verified=True,
            disabled=False,
        )
        self.verify_exc = verify_exc
        self.get_user_exc = get_user_exc
        self.verify_calls: list[dict[str, object]] = []
        self.get_user_calls: list[dict[str, object]] = []

    def verify_id_token(self, id_token: str, **kwargs: object) -> dict:
        self.verify_calls.append({"id_token": id_token, **kwargs})
        if self.verify_exc is not None:
            raise self.verify_exc
        return dict(self.decoded_token)

    def get_user(self, uid: str, **kwargs: object) -> SimpleNamespace:
        self.get_user_calls.append({"uid": uid, **kwargs})
        if self.get_user_exc is not None:
            raise self.get_user_exc
        return self.user_record


class _FirebaseAdminFake:
    def __init__(self) -> None:
        self._apps: dict[str, object] = {}
        self.initialized_options: dict[str, object] | None = None
        self.initialized_credential: object | None = None

    def initialize_app(self, credential: object, options: dict[str, object]) -> object:
        app = SimpleNamespace(name="[DEFAULT]", options=options)
        self._apps["[DEFAULT]"] = app
        self.initialized_credential = credential
        self.initialized_options = options
        return app

    def get_app(self) -> object:
        return self._apps["[DEFAULT]"]


class _CredentialsFake:
    class Certificate:
        def __init__(self, value: object) -> None:
            self.value = value


def _install_firebase_fakes(
    monkeypatch: pytest.MonkeyPatch,
    *,
    decoded_token: dict | None = None,
    user_record: SimpleNamespace | None = None,
    verify_exc: Exception | None = None,
    get_user_exc: Exception | None = None,
    project_id: str | None = SYNTHETIC_PROJECT_ID,
) -> tuple[_FirebaseAdminFake, _AuthFake]:
    admin_fake = _FirebaseAdminFake()
    auth_fake = _AuthFake(
        decoded_token=decoded_token,
        user_record=user_record,
        verify_exc=verify_exc,
        get_user_exc=get_user_exc,
    )
    settings = SimpleNamespace(
        firebase_admin_credentials_json_value=SYNTHETIC_CREDENTIAL_JSON,
        firebase_admin_credentials_value=None,
        firebase_http_timeout_seconds=8.5,
        firebase_project_id=project_id,
    )

    monkeypatch.setattr(firebase_client, "firebase_admin", admin_fake)
    monkeypatch.setattr(firebase_client, "auth", auth_fake)
    monkeypatch.setattr(firebase_client, "credentials", _CredentialsFake)
    monkeypatch.setattr(firebase_client, "get_settings", lambda: settings)

    return admin_fake, auth_fake


@pytest.mark.requirement("WS03-01-R1", "WS03-01-R2", "WS03-01-R10")
def test_firebase_admin_verification_is_project_bound_and_provider_authoritative(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    decoded_token = {
        "uid": "decoded-uid",
        "email": "stale-token-email@example.invalid",
        "email_verified": False,
        "auth_time": 1_700_000_000,
    }
    provider_user = SimpleNamespace(
        uid="provider-uid",
        email="current-provider-email@example.invalid",
        email_verified=True,
        disabled=False,
    )
    admin_fake, auth_fake = _install_firebase_fakes(
        monkeypatch,
        decoded_token=decoded_token,
        user_record=provider_user,
    )

    authoritative_token = firebase_client.verify_firebase_token("synthetic-id-token")

    assert admin_fake.initialized_options == {
        "httpTimeout": 8.5,
        "projectId": SYNTHETIC_PROJECT_ID,
    }
    assert auth_fake.verify_calls == [
        {
            "id_token": "synthetic-id-token",
            "app": admin_fake.get_app(),
            "check_revoked": True,
            "clock_skew_seconds": FIREBASE_TOKEN_CLOCK_SKEW_SECONDS,
        }
    ]
    assert auth_fake.get_user_calls == [
        {"uid": "decoded-uid", "app": admin_fake.get_app()}
    ]
    assert authoritative_token["uid"] == "provider-uid"
    assert authoritative_token["email"] == "current-provider-email@example.invalid"
    assert authoritative_token["email_verified"] is True
    assert authoritative_token["auth_time"] == 1_700_000_000


@pytest.mark.requirement("WS03-01-R1")
@pytest.mark.parametrize("uid", ["", None])
def test_firebase_token_requires_valid_uid(
    monkeypatch: pytest.MonkeyPatch,
    uid: object,
) -> None:
    _admin_fake, auth_fake = _install_firebase_fakes(
        monkeypatch,
        decoded_token={"uid": uid, "email": "user@example.invalid"},
    )

    with pytest.raises(ValueError, match="missing a user id"):
        firebase_client.verify_firebase_token("synthetic-id-token")

    assert auth_fake.get_user_calls == []


@pytest.mark.requirement("WS03-01-R2")
def test_disabled_provider_account_is_denied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_firebase_fakes(
        monkeypatch,
        user_record=SimpleNamespace(
            uid="firebase-uid",
            email="disabled@example.invalid",
            email_verified=True,
            disabled=True,
        ),
    )

    with pytest.raises(_AuthFake.UserDisabledError):
        firebase_client.verify_firebase_token("synthetic-id-token")


@pytest.mark.requirement("WS03-01-R2")
def test_deleted_or_missing_provider_account_is_denied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_firebase_fakes(
        monkeypatch,
        get_user_exc=_AuthFake.UserNotFoundError("provider user missing"),
    )

    with pytest.raises(_AuthFake.UserNotFoundError):
        firebase_client.verify_firebase_token("synthetic-id-token")


@pytest.mark.requirement("WS03-01-R1", "WS03-01-R2")
@pytest.mark.parametrize(
    "verify_exc",
    [
        _AuthFake.InvalidIdTokenError("invalid token"),
        _AuthFake.ExpiredIdTokenError("expired token"),
        _AuthFake.RevokedIdTokenError("revoked token"),
        ValueError("wrong project or audience"),
    ],
)
def test_invalid_expired_revoked_or_wrong_project_style_credentials_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    verify_exc: Exception,
) -> None:
    _install_firebase_fakes(monkeypatch, verify_exc=verify_exc)

    with pytest.raises(type(verify_exc)):
        firebase_client.verify_firebase_token("synthetic-id-token")


@pytest.mark.requirement("WS03-01-R2")
@pytest.mark.parametrize(
    "verify_exc",
    [
        _AuthFake.CertificateFetchError("certificate endpoint unavailable"),
        RuntimeError("raw provider stack detail"),
    ],
)
def test_provider_unavailable_errors_are_classified_without_raw_provider_detail(
    monkeypatch: pytest.MonkeyPatch,
    verify_exc: Exception,
) -> None:
    _install_firebase_fakes(monkeypatch, verify_exc=verify_exc)

    with pytest.raises(FirebaseIdentityUnavailableError) as exc_info:
        firebase_client.verify_firebase_token("synthetic-id-token")

    assert str(exc_info.value) == "Firebase identity state is unavailable."
    assert "raw provider stack detail" not in str(exc_info.value)


@pytest.mark.requirement("WS03-01-R10")
def test_missing_project_configuration_fails_before_provider_verification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _admin_fake, auth_fake = _install_firebase_fakes(monkeypatch, project_id=None)

    with pytest.raises(FirebaseAdminConfigError, match="FIREBASE_PROJECT_ID"):
        firebase_client.verify_firebase_token("synthetic-id-token")

    assert auth_fake.verify_calls == []


@pytest.mark.requirement("WS03-01-R2")
@pytest.mark.parametrize(
    ("provider_exc", "expected_status", "expected_detail"),
    [
        (
            FirebaseAdminConfigError("secret credential path should not leak"),
            503,
            "Authentication provider is not configured.",
        ),
        (
            FirebaseIdentityUnavailableError("raw provider outage should not leak"),
            503,
            "Authentication provider is unavailable.",
        ),
        (
            _AuthFake.InvalidIdTokenError("raw invalid token detail should not leak"),
            401,
            "Invalid or expired authentication token.",
        ),
    ],
)
def test_public_auth_errors_do_not_leak_provider_exception_details(
    monkeypatch: pytest.MonkeyPatch,
    provider_exc: Exception,
    expected_status: int,
    expected_detail: str,
) -> None:
    import backend.services.auth_service as auth_service

    def fail_verification(_token: str) -> dict:
        raise provider_exc

    monkeypatch.setattr(auth_service, "verify_firebase_token", fail_verification)

    with pytest.raises(HTTPException) as exc_info:
        auth_service.get_verified_firebase_identity_from_authorization(
            "Bearer synthetic-id-token"
        )

    assert exc_info.value.status_code == expected_status
    assert exc_info.value.detail == expected_detail
    assert "secret credential path" not in str(exc_info.value.detail)
    assert "raw provider" not in str(exc_info.value.detail)
