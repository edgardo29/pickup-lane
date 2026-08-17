from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import backend.firebase_admin_client as firebase_client
from backend.settings import SettingsError, build_settings

pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.suite_type("ordinary")]

REPO_ROOT = Path(__file__).resolve().parents[4]
SYNTHETIC_PROJECT_ID = "pickup-lane-synthetic"
FIREBASE_ADMIN_JSON = '{"type":"service_account","project_id":"synthetic"}'
PRODUCTION_DATABASE_URL = (
    "postgresql+psycopg://db.example.invalid:5432/pickup_lane_prod"
)


def _settings_env(**overrides: str | None) -> dict[str, str]:
    env = {
        "APP_ENV": "production",
        "DATABASE_URL": PRODUCTION_DATABASE_URL,
        "ALLOWED_HOSTS": "api.example.invalid",
        "CORS_ALLOWED_ORIGINS": "https://app.example.invalid",
        "ENABLE_API_DOCS": "false",
        "ENABLE_DB_HEALTH": "false",
        "FIREBASE_ADMIN_CREDENTIALS_JSON": FIREBASE_ADMIN_JSON,
        "FIREBASE_PROJECT_ID": SYNTHETIC_PROJECT_ID,
        "FIREBASE_APP_CHECK_MODE": "disabled",
        "ENABLE_STRIPE_PAYMENTS": "false",
        "R2_ACCOUNT_ID": "synthetic-r2-account",
        "R2_ACCESS_KEY_ID": "synthetic-r2-access-key-id",
        "R2_SECRET_ACCESS_KEY": "synthetic-r2-secret-access-key",
        "R2_BUCKET_NAME": "pickup-lane-synthetic-bucket",
        "R2_ENDPOINT_URL": (
            "https://synthetic-r2-account.r2.cloudflarestorage.com"
        ),
        "INBOX_TOKEN_SECRET": "synthetic-independent-inbox-token-secret",
    }
    for name, value in overrides.items():
        if value is None:
            env.pop(name, None)
        else:
            env[name] = value
    return env


def _assert_rejected(
    env: dict[str, str],
    *,
    mentions: tuple[str, ...],
    does_not_echo: tuple[str, ...] = (),
) -> None:
    with pytest.raises(SettingsError) as exc_info:
        build_settings(env, load_dotenv_file=False, validate_full=True)

    message = str(exc_info.value)
    for fragment in mentions:
        assert fragment in message
    for secret_or_placeholder in does_not_echo:
        assert secret_or_placeholder not in message


@pytest.mark.requirement("WS03-01-R10")
@pytest.mark.parametrize(
    "missing_name",
    [
        "FIREBASE_ADMIN_CREDENTIALS_JSON",
        "FIREBASE_PROJECT_ID",
    ],
)
def test_production_like_settings_require_firebase_credentials_and_project_id(
    missing_name: str,
) -> None:
    _assert_rejected(_settings_env(**{missing_name: None}), mentions=(missing_name,))


@pytest.mark.requirement("WS03-01-R10")
def test_production_like_settings_reject_placeholder_project_id_without_echoing_it() -> None:
    placeholder = "replace-with-firebase-project-id"

    _assert_rejected(
        _settings_env(FIREBASE_PROJECT_ID=placeholder),
        mentions=("FIREBASE_PROJECT_ID",),
        does_not_echo=(placeholder,),
    )


@pytest.mark.requirement("WS03-01-R10")
@pytest.mark.parametrize(
    "project_id",
    [
        "Pickup_Lane",
        "-pickup-lane",
        "pickup-lane-",
        "pickup lane",
    ],
)
def test_firebase_project_id_must_use_valid_dns_label_syntax(project_id: str) -> None:
    _assert_rejected(
        _settings_env(FIREBASE_PROJECT_ID=project_id),
        mentions=("FIREBASE_PROJECT_ID", "valid Firebase project id"),
    )


class _FirebaseAdminFake:
    def __init__(self) -> None:
        self._apps: dict[str, object] = {}
        self.initialized_options: dict[str, object] | None = None

    def initialize_app(self, credential: object, options: dict[str, object]) -> object:
        del credential
        app = SimpleNamespace(name="[DEFAULT]")
        self._apps["[DEFAULT]"] = app
        self.initialized_options = options
        return app

    def get_app(self) -> object:
        return self._apps["[DEFAULT]"]


class _CredentialsFake:
    class Certificate:
        def __init__(self, value: object) -> None:
            self.value = value


@pytest.mark.requirement("WS03-01-R10")
def test_firebase_admin_initialization_passes_configured_project_id_without_provider_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin_fake = _FirebaseAdminFake()
    settings = SimpleNamespace(
        firebase_admin_credentials_json_value=FIREBASE_ADMIN_JSON,
        firebase_admin_credentials_value=None,
        firebase_http_timeout_seconds=8,
        firebase_project_id=SYNTHETIC_PROJECT_ID,
    )

    monkeypatch.setattr(firebase_client, "firebase_admin", admin_fake)
    monkeypatch.setattr(firebase_client, "credentials", _CredentialsFake)
    monkeypatch.setattr(firebase_client, "get_settings", lambda: settings)

    firebase_client.initialize_firebase_admin()

    assert admin_fake.initialized_options == {
        "httpTimeout": 8,
        "projectId": SYNTHETIC_PROJECT_ID,
    }


@pytest.mark.requirement("WS03-01-R10", "WS03-03B-R1", "WS03-03B-R6")
def test_example_configuration_keeps_firebase_values_as_placeholders() -> None:
    text = (REPO_ROOT / "backend/.env.example").read_text()

    assert "FIREBASE_ADMIN_CREDENTIALS_JSON=replace-with-firebase-admin-json" in text
    assert "FIREBASE_PROJECT_ID=replace-with-firebase-project-id" in text
    assert "FIREBASE_APP_CHECK_APP_ID=replace-with-firebase-app-check-app-id" in text
    assert "private_key" not in text
    assert "client_email" not in text
    assert SYNTHETIC_PROJECT_ID not in text
