from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

import backend.firebase_admin_client as firebase_client
from backend.observability.timeouts import (
    DependencyMutationTimeoutUnknownError,
    DependencyReadTimeoutError,
)

pytestmark = pytest.mark.no_db_cleanup


class _UserNotFoundError(Exception):
    pass


class _CertificateFetchError(Exception):
    pass


class _AuthModule:
    UserNotFoundError = _UserNotFoundError
    CertificateFetchError = _CertificateFetchError
    InvalidIdTokenError = ValueError
    ExpiredIdTokenError = ValueError
    RevokedIdTokenError = ValueError
    UserDisabledError = ValueError

    def __init__(self) -> None:
        self.verify_id_token_result = {"uid": "firebase-user"}
        self.verify_id_token_exception: BaseException | None = None
        self.get_user_exception: BaseException | None = None
        self.get_user_by_email_exception: BaseException | None = None
        self.delete_user_exception: BaseException | None = None

    def verify_id_token(self, *args, **kwargs):
        if self.verify_id_token_exception is not None:
            raise self.verify_id_token_exception
        return dict(self.verify_id_token_result)

    def get_user(self, *args, **kwargs):
        if self.get_user_exception is not None:
            raise self.get_user_exception
        return SimpleNamespace(
            uid="firebase-user",
            email="user@example.invalid",
            email_verified=True,
            disabled=False,
        )

    def get_user_by_email(self, *args, **kwargs):
        if self.get_user_by_email_exception is not None:
            raise self.get_user_by_email_exception
        return SimpleNamespace(uid="firebase-user")

    def delete_user(self, *args, **kwargs):
        if self.delete_user_exception is not None:
            raise self.delete_user_exception
        return None


def _install_firebase_boundary(
    monkeypatch: pytest.MonkeyPatch,
    auth_module: _AuthModule,
) -> list[dict[str, object]]:
    initialize_calls: list[dict[str, object]] = []

    monkeypatch.setattr(firebase_client, "auth", auth_module)
    monkeypatch.setattr(
        firebase_client,
        "_firebase_settings",
        lambda: SimpleNamespace(
            firebase_project_id="pickup-lane-synthetic",
            firebase_http_timeout_seconds=8,
            firebase_admin_credentials_json_value='{"type":"service_account"}',
            firebase_admin_credentials_value="",
        ),
    )
    monkeypatch.setattr(
        firebase_client.credentials,
        "Certificate",
        lambda value: {"credential": value},
    )
    monkeypatch.setattr(firebase_client.firebase_admin, "_apps", {})
    monkeypatch.setattr(
        firebase_client.firebase_admin,
        "initialize_app",
        lambda cred, options: initialize_calls.append({"cred": cred, "options": options})
        or SimpleNamespace(name="synthetic-firebase-app"),
    )
    return initialize_calls


@pytest.mark.requirement("WS02-04C1-R3")
def test_firebase_admin_initialization_uses_approved_http_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth_module = _AuthModule()
    initialize_calls = _install_firebase_boundary(monkeypatch, auth_module)

    app = firebase_client.initialize_firebase_admin()

    assert app.name == "synthetic-firebase-app"
    assert initialize_calls == [
        {
            "cred": {"credential": {"type": "service_account"}},
            "options": {
                "httpTimeout": 8,
                "projectId": "pickup-lane-synthetic",
            },
        }
    ]


@pytest.mark.requirement("WS02-04C1-R3")
def test_firebase_token_verification_timeout_maps_to_dependency_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth_module = _AuthModule()
    auth_module.verify_id_token_exception = TimeoutError("verify timed out")
    _install_firebase_boundary(monkeypatch, auth_module)

    with pytest.raises(DependencyReadTimeoutError) as exc_info:
        firebase_client.verify_firebase_token("synthetic-token")

    assert exc_info.value.provider_kind == "firebase"
    assert exc_info.value.operation == "firebase.token.verify"


@pytest.mark.requirement("WS02-04C1-R3")
def test_firebase_user_record_timeout_maps_to_dependency_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth_module = _AuthModule()
    auth_module.get_user_exception = TimeoutError("user lookup timed out")
    _install_firebase_boundary(monkeypatch, auth_module)

    with pytest.raises(DependencyReadTimeoutError) as exc_info:
        firebase_client.verify_firebase_token("synthetic-token")

    assert exc_info.value.provider_kind == "firebase"
    assert exc_info.value.operation == "firebase.token.verify"


@pytest.mark.requirement("WS02-04C1-R3")
def test_firebase_email_lookup_timeout_maps_to_dependency_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth_module = _AuthModule()
    auth_module.get_user_by_email_exception = TimeoutError("email lookup timed out")
    _install_firebase_boundary(monkeypatch, auth_module)

    with pytest.raises(DependencyReadTimeoutError) as exc_info:
        firebase_client.firebase_email_exists("user@example.invalid")

    assert exc_info.value.provider_kind == "firebase"
    assert exc_info.value.operation == "firebase.user.lookup"


@pytest.mark.requirement("WS02-04C1-R3")
def test_firebase_delete_timeout_maps_to_mutation_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth_module = _AuthModule()
    auth_module.delete_user_exception = TimeoutError("delete timed out")
    _install_firebase_boundary(monkeypatch, auth_module)

    with pytest.raises(DependencyMutationTimeoutUnknownError) as exc_info:
        firebase_client.delete_firebase_user("firebase-user")

    assert exc_info.value.provider_kind == "firebase"
    assert exc_info.value.operation == "firebase.user.delete"
    assert exc_info.value.contract.details["outcome"] == "unknown"


@pytest.mark.requirement("WS02-04C1-R3")
def test_firebase_user_not_found_remains_current_non_timeout_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth_module = _AuthModule()
    _install_firebase_boundary(monkeypatch, auth_module)

    auth_module.get_user_by_email_exception = _UserNotFoundError("missing email")
    assert firebase_client.firebase_email_exists("missing@example.invalid") is False

    auth_module.delete_user_exception = _UserNotFoundError("already deleted")
    assert firebase_client.delete_firebase_user("firebase-user") is None


@pytest.mark.requirement("WS02-04C1-R3")
def test_firebase_token_validation_failures_remain_auth_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth_module = _AuthModule()
    auth_module.verify_id_token_exception = ValueError("invalid token")
    _install_firebase_boundary(monkeypatch, auth_module)

    with pytest.raises(ValueError, match="invalid token"):
        firebase_client.verify_firebase_token("synthetic-token")

    auth_module = _AuthModule()
    auth_module.get_user_exception = _UserNotFoundError("missing token user")
    _install_firebase_boundary(monkeypatch, auth_module)

    with pytest.raises(_UserNotFoundError, match="missing token user"):
        firebase_client.verify_firebase_token("synthetic-token")


@pytest.mark.requirement("WS02-04C1-R3", "WS02-04C1-R7")
def test_firebase_non_timeout_and_cancellation_are_not_timeout_classified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth_module = _AuthModule()
    auth_module.delete_user_exception = RuntimeError("plain failure")
    _install_firebase_boundary(monkeypatch, auth_module)

    with pytest.raises(RuntimeError, match="plain failure"):
        firebase_client.delete_firebase_user("firebase-user")

    auth_module.delete_user_exception = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        firebase_client.delete_firebase_user("firebase-user")
