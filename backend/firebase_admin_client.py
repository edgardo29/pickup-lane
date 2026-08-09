import json
import os

import firebase_admin
from firebase_admin import auth, credentials

from backend.observability.timeouts import (
    DependencyMutationTimeoutUnknownError,
    DependencyReadTimeoutError,
    is_timeout_like_exception,
)
from backend.settings import SettingsError, get_settings

FIREBASE_TOKEN_CLOCK_SKEW_SECONDS = 10


class FirebaseAdminConfigError(RuntimeError):
    pass


def initialize_firebase_admin() -> None:
    if firebase_admin._apps:
        return

    settings = _firebase_settings()
    cred = _load_firebase_credentials(settings)
    firebase_admin.initialize_app(
        cred,
        {"httpTimeout": settings.firebase_http_timeout_seconds},
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
    initialize_firebase_admin()
    try:
        return auth.verify_id_token(
            id_token,
            clock_skew_seconds=FIREBASE_TOKEN_CLOCK_SKEW_SECONDS,
        )
    except Exception as exc:
        if is_timeout_like_exception(exc):
            raise DependencyReadTimeoutError(
                provider_kind="firebase",
                operation="firebase.token.verify",
            ) from exc
        raise


def firebase_email_exists(email: str) -> bool:
    initialize_firebase_admin()

    try:
        auth.get_user_by_email(email)
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
    initialize_firebase_admin()

    try:
        auth.delete_user(auth_user_id)
    except auth.UserNotFoundError:
        return
    except Exception as exc:
        if is_timeout_like_exception(exc):
            raise DependencyMutationTimeoutUnknownError(
                provider_kind="firebase",
                operation="firebase.user.delete",
            ) from exc
        raise
