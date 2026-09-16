from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

import backend.firebase_admin_client as firebase_client
from backend.observability.metrics import MetricsRecorder, metrics_context
from backend.observability.timeouts import (
    DependencyMutationTimeoutUnknownError,
    DependencyReadTimeoutError,
)

pytestmark = pytest.mark.no_db_cleanup


@pytest.mark.parametrize("owner", ["verify", "lookup", "email", "app_check", "delete"])
@pytest.mark.parametrize(
    "outcome", ["succeeded", "timeout", "rate_limited", "failed", "configuration_error"]
)
def test_complete_firebase_metric_boundary_matrix(monkeypatch, owner, outcome):
    from firebase_admin.exceptions import ResourceExhaustedError

    auth_module = _AuthModule()
    app_check_module = _AppCheckModule()
    _install_firebase_boundary(monkeypatch, auth_module, app_check_module)
    operation = {
        "verify": "firebase.token.verify",
        "lookup": "firebase.user.lookup",
        "email": "firebase.user.lookup",
        "app_check": "firebase.app_check.verify",
        "delete": "firebase.user.delete",
    }[owner]
    expected = (
        "unknown_outcome"
        if owner == "delete" and outcome == "timeout"
        else "timed_out"
        if outcome == "timeout"
        else outcome
    )
    error = {
        "timeout": TimeoutError("private-canary"),
        "rate_limited": ResourceExhaustedError("private-canary"),
        "failed": RuntimeError("private-canary"),
    }.get(outcome)
    if outcome == "configuration_error":

        def fail_initialize():
            raise firebase_client.FirebaseAdminConfigError("private-canary")

        monkeypatch.setattr(
            firebase_client, "initialize_firebase_admin", fail_initialize
        )
        # Initialization is owned by verify, before lookup is possible.
        if owner == "lookup":
            operation = "firebase.token.verify"
    elif owner == "app_check":
        app_check_module.verify_token_exception = error
    else:
        attribute = {
            "verify": "verify_id_token_exception",
            "lookup": "get_user_exception",
            "email": "get_user_by_email_exception",
            "delete": "delete_user_exception",
        }[owner]
        setattr(auth_module, attribute, error)
    call = {
        "verify": lambda: firebase_client.verify_firebase_token("private-token"),
        "lookup": lambda: firebase_client.verify_firebase_token("private-token"),
        "email": lambda: firebase_client.firebase_email_exists(
            "private@example.invalid"
        ),
        "app_check": lambda: firebase_client.verify_firebase_app_check_token(
            "private-token"
        ),
        "delete": lambda: firebase_client.delete_firebase_user("private-user"),
    }[owner]
    recorder = MetricsRecorder("api", "test", "firebase-test")
    with metrics_context(recorder):
        if outcome == "succeeded":
            call()
        else:
            try:
                call()
            except Exception as exc:  # noqa: BLE001 - matrix asserts preserved owner-specific types separately.
                assert exc is not None
            else:
                pytest.fail("The configured provider failure must propagate")
    observations = {
        tuple(item.dimensions): item.value for item in recorder.snapshot().series
    }
    target = tuple(
        sorted(
            {
                "provider_kind": "firebase",
                "operation": operation,
                "result": expected,
            }.items()
        )
    )
    assert observations[target] == 1
    assert len(observations) == (
        2
        if owner in {"verify", "lookup"}
        and outcome == "succeeded"
        or owner == "lookup"
        and outcome != "configuration_error"
        else 1
    )
    assert "private" not in repr(recorder.snapshot())


@pytest.mark.parametrize(
    ("owner", "result"),
    [
        ("verify", "rejected"),
        ("lookup", "not_found"),
        ("email", "not_found"),
        ("delete", "succeeded"),
    ],
)
def test_firebase_absence_meaning_and_no_unattempted_lookup(monkeypatch, owner, result):
    auth_module = _AuthModule()
    _install_firebase_boundary(monkeypatch, auth_module)
    attribute = {
        "verify": "verify_id_token_exception",
        "lookup": "get_user_exception",
        "email": "get_user_by_email_exception",
        "delete": "delete_user_exception",
    }[owner]
    setattr(auth_module, attribute, _UserNotFoundError("private-user"))
    if owner == "verify":
        monkeypatch.setattr(
            auth_module, "get_user", lambda *a, **k: pytest.fail("Lookup not reached")
        )
    recorder = MetricsRecorder("api", "test", "firebase-test")
    with metrics_context(recorder):
        if owner in {"verify", "lookup"}:
            with pytest.raises(_UserNotFoundError):
                firebase_client.verify_firebase_token("private-token")
        elif owner == "email":
            assert (
                firebase_client.firebase_email_exists("private@example.invalid")
                is False
            )
        else:
            assert firebase_client.delete_firebase_user("private-user") is None
    series = recorder.snapshot().series
    target = next(item for item in series if dict(item.dimensions)["result"] == result)
    assert target.value == 1
    assert len(series) == (2 if owner == "lookup" else 1)


@pytest.mark.parametrize("owner", ["verify", "lookup", "app_check"])
def test_firebase_expected_rejection_is_not_failure(monkeypatch, owner):
    auth_module = _AuthModule()
    app_check_module = _AppCheckModule()
    _install_firebase_boundary(monkeypatch, auth_module, app_check_module)
    if owner == "verify":
        auth_module.verify_id_token_exception = ValueError("private-token")
    elif owner == "lookup":
        auth_module.get_user_exception = ValueError("private-disabled-user")
    else:
        app_check_module.verify_token_exception = ValueError("private-token")
    recorder = MetricsRecorder("api", "test", "firebase-test")
    with metrics_context(recorder), pytest.raises(ValueError):
        (
            firebase_client.verify_firebase_app_check_token
            if owner == "app_check"
            else firebase_client.verify_firebase_token
        )("private-token")
    assert dict(recorder.snapshot().series[-1].dimensions)[
        "result"
    ] == "rejected" or any(
        dict(item.dimensions)["operation"] == "firebase.user.lookup"
        and dict(item.dimensions)["result"] == "rejected"
        for item in recorder.snapshot().series
    )


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


class _AppCheckModule:
    def __init__(self) -> None:
        self.verify_token_result = {"app_id": "1:123456789:web:supported"}
        self.verify_token_exception: BaseException | None = None
        self.verify_token_calls: list[dict[str, object]] = []

    def verify_token(self, token, *, app=None):
        self.verify_token_calls.append(
            {"token": token, "app_name": getattr(app, "name", None)}
        )
        if self.verify_token_exception is not None:
            raise self.verify_token_exception
        return dict(self.verify_token_result)


def _install_firebase_boundary(
    monkeypatch: pytest.MonkeyPatch,
    auth_module: _AuthModule,
    app_check_module: _AppCheckModule | None = None,
) -> list[dict[str, object]]:
    initialize_calls: list[dict[str, object]] = []

    monkeypatch.setattr(firebase_client, "auth", auth_module)
    monkeypatch.setattr(
        firebase_client,
        "app_check",
        app_check_module or _AppCheckModule(),
    )
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
        lambda cred, options: (
            initialize_calls.append({"cred": cred, "options": options})
            or SimpleNamespace(name="synthetic-firebase-app")
        ),
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


@pytest.mark.requirement("WS02-04C1-R3")
def test_firebase_app_check_verification_uses_existing_initialized_app(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth_module = _AuthModule()
    app_check_module = _AppCheckModule()
    _install_firebase_boundary(monkeypatch, auth_module, app_check_module)

    result = firebase_client.verify_firebase_app_check_token(
        "synthetic-app-check-token"
    )

    assert result == {"app_id": "1:123456789:web:supported"}
    assert app_check_module.verify_token_calls == [
        {
            "token": "synthetic-app-check-token",
            "app_name": "synthetic-firebase-app",
        }
    ]


@pytest.mark.requirement("WS02-04C1-R3")
def test_firebase_app_check_timeout_maps_to_dependency_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth_module = _AuthModule()
    app_check_module = _AppCheckModule()
    app_check_module.verify_token_exception = TimeoutError("app check timed out")
    _install_firebase_boundary(monkeypatch, auth_module, app_check_module)

    with pytest.raises(DependencyReadTimeoutError) as exc_info:
        firebase_client.verify_firebase_app_check_token("synthetic-app-check-token")

    assert exc_info.value.provider_kind == "firebase"
    assert exc_info.value.operation == "firebase.app_check.verify"


@pytest.mark.requirement("WS02-04C1-R3")
def test_firebase_app_check_invalid_token_remains_validation_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth_module = _AuthModule()
    app_check_module = _AppCheckModule()
    app_check_module.verify_token_exception = ValueError("invalid app check token")
    _install_firebase_boundary(monkeypatch, auth_module, app_check_module)

    with pytest.raises(ValueError, match="invalid app check token"):
        firebase_client.verify_firebase_app_check_token("synthetic-app-check-token")


@pytest.mark.requirement("WS02-04C1-R3")
def test_firebase_app_check_provider_unavailable_is_not_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth_module = _AuthModule()
    app_check_module = _AppCheckModule()
    app_check_module.verify_token_exception = firebase_client.PyJWKClientError(
        "jwks unavailable"
    )
    _install_firebase_boundary(monkeypatch, auth_module, app_check_module)

    with pytest.raises(firebase_client.FirebaseAppCheckUnavailableError):
        firebase_client.verify_firebase_app_check_token("synthetic-app-check-token")


def test_firebase_app_check_deadline_preserves_translation_and_records_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth_module = _AuthModule()
    app_check_module = _AppCheckModule()
    app_check_module.verify_token_exception = (
        firebase_client.firebase_exceptions.DeadlineExceededError(
            "private-deadline-canary"
        )
    )
    _install_firebase_boundary(monkeypatch, auth_module, app_check_module)
    recorder = MetricsRecorder("api", "test", "firebase-test")

    with (
        metrics_context(recorder),
        pytest.raises(firebase_client.FirebaseAppCheckUnavailableError),
    ):
        firebase_client.verify_firebase_app_check_token("synthetic-app-check-token")

    (observation,) = recorder.snapshot().series
    assert observation.value == 1
    assert dict(observation.dimensions) == {
        "provider_kind": "firebase",
        "operation": "firebase.app_check.verify",
        "result": "timed_out",
    }
    assert "private-deadline-canary" not in repr(recorder.snapshot())


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


@pytest.mark.requirement("WS02-04C1-R3", "WS02-04C1-R7")
def test_firebase_app_check_cancellation_is_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth_module = _AuthModule()
    app_check_module = _AppCheckModule()
    app_check_module.verify_token_exception = asyncio.CancelledError()
    _install_firebase_boundary(monkeypatch, auth_module, app_check_module)

    with pytest.raises(asyncio.CancelledError):
        firebase_client.verify_firebase_app_check_token("synthetic-app-check-token")
