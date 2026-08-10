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


class FirebaseIdentityUnavailableError(RuntimeError):
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
    firebase_app = initialize_firebase_admin()
    try:
        decoded_token = auth.verify_id_token(
            id_token,
            app=firebase_app,
            check_revoked=True,
            clock_skew_seconds=FIREBASE_TOKEN_CLOCK_SKEW_SECONDS,
        )
        auth_user_id = decoded_token.get("uid")
        if not isinstance(auth_user_id, str) or not auth_user_id:
            raise ValueError("Firebase token is missing a user id.")
        user_record = auth.get_user(auth_user_id, app=firebase_app)
        if getattr(user_record, "disabled", False):
            raise auth.UserDisabledError("Firebase user is disabled.")

        authoritative_token = dict(decoded_token)
        authoritative_token["uid"] = getattr(user_record, "uid", None) or auth_user_id
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


def firebase_email_exists(email: str) -> bool:
    firebase_app = initialize_firebase_admin()

    try:
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
    firebase_app = initialize_firebase_admin()

    try:
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
