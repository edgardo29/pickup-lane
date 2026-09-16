import json
import os
from contextlib import contextmanager

import firebase_admin
from firebase_admin import app_check, auth, credentials
from firebase_admin import exceptions as firebase_exceptions

from backend.observability.metrics import record_provider_outcome
from backend.observability.timeouts import (
    DependencyMutationTimeoutUnknownError,
    DependencyReadTimeoutError,
    is_timeout_like_exception,
)
from backend.settings import SettingsError, get_settings

try:  # pragma: no cover - import shape is owned by the installed Firebase SDK.
    from jwt.exceptions import PyJWKClientError
except ImportError:  # pragma: no cover
    PyJWKClientError = ()  # type: ignore[assignment]

FIREBASE_TOKEN_CLOCK_SKEW_SECONDS = 10
FIREBASE_APP_CHECK_VERIFY_OPERATION = "firebase.app_check.verify"

_APP_CHECK_PROVIDER_UNAVAILABLE_ERRORS = (
    firebase_exceptions.AbortedError,
    firebase_exceptions.CancelledError,
    firebase_exceptions.DataLossError,
    firebase_exceptions.DeadlineExceededError,
    firebase_exceptions.InternalError,
    firebase_exceptions.ResourceExhaustedError,
    firebase_exceptions.UnavailableError,
    firebase_exceptions.UnknownError,
)


class FirebaseAdminConfigError(RuntimeError):
    pass


class FirebaseIdentityUnavailableError(RuntimeError):
    pass


class FirebaseAppCheckUnavailableError(RuntimeError):
    pass


def initialize_firebase_admin() -> firebase_admin.App:
    if firebase_admin._apps:
        return firebase_admin.get_app()

    settings = _firebase_settings()
    if not settings.firebase_project_id:
        raise FirebaseAdminConfigError(
            "FIREBASE_PROJECT_ID is required before Firebase authentication is used."
        )
    cred = _load_firebase_credentials(settings)
    return firebase_admin.initialize_app(
        cred,
        {
            "httpTimeout": settings.firebase_http_timeout_seconds,
            "projectId": settings.firebase_project_id,
        },
    )


def _firebase_settings():
    try:
        return get_settings()
    except SettingsError as exc:
        raise FirebaseAdminConfigError(str(exc)) from exc


def _load_firebase_credentials(settings) -> credentials.Certificate:
    credentials_json = settings.firebase_admin_credentials_json_value
    if credentials_json:
        credentials_info = json.loads(credentials_json)
        return credentials.Certificate(credentials_info)

    credentials_path = settings.firebase_admin_credentials_value
    if not credentials_path:
        raise FirebaseAdminConfigError(
            "FIREBASE_ADMIN_CREDENTIALS_JSON or FIREBASE_ADMIN_CREDENTIALS is required."
        )

    if not os.path.exists(credentials_path):
        raise FirebaseAdminConfigError(
            "FIREBASE_ADMIN_CREDENTIALS does not point to a readable file."
        )

    return credentials.Certificate(credentials_path)


def verify_firebase_token(id_token: str) -> dict:
    firebase_app = _initialize_for_operation("firebase.token.verify")
    try:
        with _observe_firebase_operation("firebase.token.verify"):
            decoded_token = auth.verify_id_token(
                id_token,
                app=firebase_app,
                check_revoked=True,
                clock_skew_seconds=FIREBASE_TOKEN_CLOCK_SKEW_SECONDS,
            )
            auth_user_id = decoded_token.get("uid")
            if not isinstance(auth_user_id, str) or not auth_user_id:
                raise ValueError("Firebase token is missing a user id.")
        with _observe_firebase_operation("firebase.user.lookup"):
            user_record = auth.get_user(auth_user_id, app=firebase_app)
            if getattr(user_record, "disabled", False):
                raise auth.UserDisabledError("Firebase user is disabled.")

            authoritative_token = dict(decoded_token)
            authoritative_token["uid"] = (
                getattr(user_record, "uid", None) or auth_user_id
            )
            authoritative_token["email"] = getattr(user_record, "email", None)
            authoritative_token["email_verified"] = bool(
                getattr(user_record, "email_verified", False)
            )
        return authoritative_token
    except Exception as exc:
        if is_timeout_like_exception(exc):
            raise DependencyReadTimeoutError(
                provider_kind="firebase",
                operation="firebase.token.verify",
            ) from exc
        if isinstance(exc, auth.CertificateFetchError):
            raise FirebaseIdentityUnavailableError(
                "Firebase identity state is unavailable."
            ) from exc
        if isinstance(
            exc,
            (
                ValueError,
                auth.InvalidIdTokenError,
                auth.ExpiredIdTokenError,
                auth.RevokedIdTokenError,
                auth.UserDisabledError,
                auth.UserNotFoundError,
            ),
        ):
            raise
        raise FirebaseIdentityUnavailableError(
            "Firebase identity state is unavailable."
        ) from exc


def verify_firebase_app_check_token(app_check_token: str) -> dict:
    firebase_app = _initialize_for_operation(FIREBASE_APP_CHECK_VERIFY_OPERATION)
    try:
        with _observe_firebase_operation(FIREBASE_APP_CHECK_VERIFY_OPERATION):
            return dict(app_check.verify_token(app_check_token, app=firebase_app))
    except ValueError:
        raise
    except PyJWKClientError as exc:
        raise FirebaseAppCheckUnavailableError(
            "Firebase App Check verification is unavailable."
        ) from exc
    except _APP_CHECK_PROVIDER_UNAVAILABLE_ERRORS as exc:
        raise FirebaseAppCheckUnavailableError(
            "Firebase App Check verification is unavailable."
        ) from exc
    except Exception as exc:
        if is_timeout_like_exception(exc):
            raise DependencyReadTimeoutError(
                provider_kind="firebase",
                operation=FIREBASE_APP_CHECK_VERIFY_OPERATION,
            ) from exc
        raise FirebaseAppCheckUnavailableError(
            "Firebase App Check verification is unavailable."
        ) from exc


def firebase_email_exists(email: str) -> bool:
    firebase_app = _initialize_for_operation("firebase.user.lookup")

    try:
        with _observe_firebase_operation("firebase.user.lookup"):
            auth.get_user_by_email(email, app=firebase_app)
    except auth.UserNotFoundError:
        return False
    except Exception as exc:
        if is_timeout_like_exception(exc):
            raise DependencyReadTimeoutError(
                provider_kind="firebase",
                operation="firebase.user.lookup",
            ) from exc
        raise

    return True


def delete_firebase_user(auth_user_id: str) -> None:
    firebase_app = _initialize_for_operation("firebase.user.delete")

    try:
        with _observe_firebase_operation("firebase.user.delete"):
            auth.delete_user(auth_user_id, app=firebase_app)
    except auth.UserNotFoundError:
        return
    except Exception as exc:
        if is_timeout_like_exception(exc):
            raise DependencyMutationTimeoutUnknownError(
                provider_kind="firebase",
                operation="firebase.user.delete",
            ) from exc
        raise


def _initialize_for_operation(operation: str):
    try:
        return initialize_firebase_admin()
    except Exception:
        record_provider_outcome(operation, "configuration_error")
        raise


def _firebase_error_result(operation: str, exc: Exception) -> str:
    if isinstance(exc, auth.UserNotFoundError):
        if operation == "firebase.user.delete":
            return "succeeded"
        return "rejected" if operation == "firebase.token.verify" else "not_found"
    if operation == "firebase.token.verify" and isinstance(
        exc,
        (
            ValueError,
            auth.InvalidIdTokenError,
            auth.ExpiredIdTokenError,
            auth.RevokedIdTokenError,
            auth.UserDisabledError,
        ),
    ):
        return "rejected"
    if operation == "firebase.user.lookup" and isinstance(exc, auth.UserDisabledError):
        return "rejected"
    if operation == FIREBASE_APP_CHECK_VERIFY_OPERATION and isinstance(exc, ValueError):
        return "rejected"
    if isinstance(exc, firebase_exceptions.ResourceExhaustedError):
        return "rate_limited"
    if is_timeout_like_exception(exc):
        return "unknown_outcome" if operation == "firebase.user.delete" else "timed_out"
    if operation == FIREBASE_APP_CHECK_VERIFY_OPERATION and isinstance(
        exc, _APP_CHECK_PROVIDER_UNAVAILABLE_ERRORS
    ):
        return "failed"
    return "failed"


@contextmanager
def _observe_firebase_operation(operation: str):
    try:
        yield
    except Exception as exc:
        try:
            result = _firebase_error_result(operation, exc)
        except Exception:  # noqa: BLE001 - preserve the original provider failure.
            result = "failed"
        record_provider_outcome(operation, result)
        raise
    else:
        record_provider_outcome(operation, "succeeded")
