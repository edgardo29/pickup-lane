from __future__ import annotations

from types import SimpleNamespace

import pytest

import backend.firebase_admin_client as firebase_admin_client
import backend.services.r2_storage_service as r2_storage_service
import backend.services.stripe_service as stripe_service
from backend.observability.timeouts import (
    DATABASE_TIMEOUT_CODE,
    DEPENDENCY_MUTATION_TIMEOUT_UNKNOWN_CODE,
    DEPENDENCY_READ_TIMEOUT_CODE,
    DependencyMutationTimeoutUnknownError,
    DependencyReadTimeoutError,
)
from backend.services.r2_storage_service import R2StorageConfig, R2StorageError
from backend.settings import (
    BACKEND_ENVIRONMENT_VARIABLES,
    DEFAULT_DB_LOCK_TIMEOUT_MILLISECONDS,
    DEFAULT_DB_POOL_WAIT_TIMEOUT_SECONDS,
    DEFAULT_DB_STATEMENT_TIMEOUT_MILLISECONDS,
    DEFAULT_FIREBASE_HTTP_TIMEOUT_SECONDS,
    DEFAULT_R2_METADATA_CONNECT_TIMEOUT_SECONDS,
    DEFAULT_R2_METADATA_READ_TIMEOUT_SECONDS,
    DEFAULT_STRIPE_MUTATION_TIMEOUT_SECONDS,
    DEFAULT_STRIPE_READ_TIMEOUT_SECONDS,
    SettingsError,
    build_settings,
)
from backend.tests.shared.settings.test_settings import backend_test_env


pytestmark = pytest.mark.no_db_cleanup


def test_timeout_setting_defaults_are_approved_values():
    settings = build_settings(backend_test_env())

    assert settings.stripe_read_timeout_seconds == DEFAULT_STRIPE_READ_TIMEOUT_SECONDS
    assert (
        settings.stripe_mutation_timeout_seconds
        == DEFAULT_STRIPE_MUTATION_TIMEOUT_SECONDS
    )
    assert settings.firebase_http_timeout_seconds == DEFAULT_FIREBASE_HTTP_TIMEOUT_SECONDS
    assert (
        settings.r2_metadata_connect_timeout_seconds
        == DEFAULT_R2_METADATA_CONNECT_TIMEOUT_SECONDS
    )
    assert (
        settings.r2_metadata_read_timeout_seconds
        == DEFAULT_R2_METADATA_READ_TIMEOUT_SECONDS
    )
    assert settings.db_pool_wait_timeout_seconds == DEFAULT_DB_POOL_WAIT_TIMEOUT_SECONDS
    assert (
        settings.db_statement_timeout_milliseconds
        == DEFAULT_DB_STATEMENT_TIMEOUT_MILLISECONDS
    )
    assert settings.db_lock_timeout_milliseconds == DEFAULT_DB_LOCK_TIMEOUT_MILLISECONDS


def test_timeout_setting_overrides_are_positive_and_provider_independent():
    settings = build_settings(
        backend_test_env(
            STRIPE_READ_TIMEOUT_SECONDS="7",
            STRIPE_MUTATION_TIMEOUT_SECONDS="16",
            FIREBASE_HTTP_TIMEOUT_SECONDS="9",
            R2_METADATA_CONNECT_TIMEOUT_SECONDS="3",
            R2_METADATA_READ_TIMEOUT_SECONDS="8",
            DB_POOL_WAIT_TIMEOUT_SECONDS="4",
            DB_STATEMENT_TIMEOUT_MILLISECONDS="15000",
            DB_LOCK_TIMEOUT_MILLISECONDS="3000",
        )
    )

    assert settings.stripe_read_timeout_seconds == 7
    assert settings.stripe_mutation_timeout_seconds == 16
    assert settings.firebase_http_timeout_seconds == 9
    assert settings.r2_metadata_connect_timeout_seconds == 3
    assert settings.r2_metadata_read_timeout_seconds == 8
    assert settings.db_pool_wait_timeout_seconds == 4
    assert settings.db_statement_timeout_milliseconds == 15000
    assert settings.db_lock_timeout_milliseconds == 3000


@pytest.mark.parametrize(
    "name",
    [
        "STRIPE_READ_TIMEOUT_SECONDS",
        "STRIPE_MUTATION_TIMEOUT_SECONDS",
        "FIREBASE_HTTP_TIMEOUT_SECONDS",
        "R2_METADATA_CONNECT_TIMEOUT_SECONDS",
        "R2_METADATA_READ_TIMEOUT_SECONDS",
        "DB_POOL_WAIT_TIMEOUT_SECONDS",
        "DB_STATEMENT_TIMEOUT_MILLISECONDS",
        "DB_LOCK_TIMEOUT_MILLISECONDS",
    ],
)
@pytest.mark.parametrize("value", ["0", "-1"])
def test_timeout_setting_zero_and_negative_values_are_rejected(name, value):
    with pytest.raises(SettingsError, match=name):
        build_settings(backend_test_env(**{name: value}))


def test_database_lock_timeout_must_be_less_than_statement_timeout():
    with pytest.raises(SettingsError, match="DB_LOCK_TIMEOUT_MILLISECONDS"):
        build_settings(
            backend_test_env(
                DB_LOCK_TIMEOUT_MILLISECONDS="12000",
                DB_STATEMENT_TIMEOUT_MILLISECONDS="12000",
            )
        )


def test_timeout_settings_do_not_introduce_connect_retry_or_rate_settings():
    assert "DB_CONNECT_TIMEOUT_SECONDS" not in BACKEND_ENVIRONMENT_VARIABLES
    assert not any("RETRY" in name for name in BACKEND_ENVIRONMENT_VARIABLES)
    assert not any("RATE" in name for name in BACKEND_ENVIRONMENT_VARIABLES)
    assert not any(name.startswith(("RENDER_", "VERCEL_", "NEON_")) for name in (
        "STRIPE_READ_TIMEOUT_SECONDS",
        "STRIPE_MUTATION_TIMEOUT_SECONDS",
        "FIREBASE_HTTP_TIMEOUT_SECONDS",
        "R2_METADATA_CONNECT_TIMEOUT_SECONDS",
        "R2_METADATA_READ_TIMEOUT_SECONDS",
        "DB_POOL_WAIT_TIMEOUT_SECONDS",
        "DB_STATEMENT_TIMEOUT_MILLISECONDS",
        "DB_LOCK_TIMEOUT_MILLISECONDS",
    ))


def test_stripe_configured_timeouts_reach_separate_read_and_mutation_clients(
    monkeypatch,
):
    captured_timeouts: list[int] = []

    class FakeRequestsClient:
        def __init__(self, *, timeout):
            self.timeout = timeout
            captured_timeouts.append(timeout)

    class FakeStripeClient:
        def __init__(self, api_key, *, http_client):
            self.api_key = api_key
            self.http_client = http_client

    fake_stripe = SimpleNamespace(
        RequestsClient=FakeRequestsClient,
        StripeClient=FakeStripeClient,
    )
    monkeypatch.setattr(stripe_service, "_import_stripe_module", lambda: fake_stripe)
    monkeypatch.setattr(
        stripe_service,
        "_stripe_settings",
        lambda: SimpleNamespace(
            enable_stripe_payments=True,
            stripe_secret_key_value="synthetic-stripe-secret",
            stripe_read_timeout_seconds=6,
            stripe_mutation_timeout_seconds=15,
        ),
    )

    client_pair = stripe_service.get_stripe_client_pair()

    assert client_pair.read.http_client.timeout == 6
    assert client_pair.mutation.http_client.timeout == 15
    assert captured_timeouts == [6, 15]


def test_stripe_read_timeout_maps_safely_and_does_not_call_mutation(monkeypatch):
    mutation_calls: list[str] = []

    def timed_out_read(_payment_intent_id):
        raise TimeoutError("private provider diagnostic")

    fake_read = SimpleNamespace(
        v1=SimpleNamespace(
            payment_intents=SimpleNamespace(retrieve=timed_out_read),
        )
    )
    fake_mutation = SimpleNamespace(
        v1=SimpleNamespace(
            payment_intents=SimpleNamespace(
                create=lambda *_args, **_kwargs: mutation_calls.append("create")
            ),
        )
    )
    monkeypatch.setattr(
        stripe_service,
        "get_stripe_client_pair",
        lambda: stripe_service.StripeClientPair(
            read=fake_read,
            mutation=fake_mutation,
        ),
    )

    with pytest.raises(DependencyReadTimeoutError) as exc_info:
        stripe_service.retrieve_payment_intent("synthetic-payment-intent")

    contract = exc_info.value.contract
    assert contract.code == DEPENDENCY_READ_TIMEOUT_CODE
    assert contract.status_code == 503
    assert "private provider diagnostic" not in contract.detail
    assert mutation_calls == []


def test_stripe_mutation_timeout_is_unknown_outcome_and_preserves_idempotency(
    monkeypatch,
):
    captured_options: list[dict[str, str]] = []

    def timed_out_create(_params, *, options):
        captured_options.append(options)
        raise TimeoutError("private provider diagnostic")

    fake_client = SimpleNamespace(
        v1=SimpleNamespace(
            payment_intents=SimpleNamespace(create=timed_out_create),
        )
    )
    monkeypatch.setattr(
        stripe_service,
        "get_stripe_client_pair",
        lambda: stripe_service.StripeClientPair(
            read=SimpleNamespace(),
            mutation=fake_client,
        ),
    )

    with pytest.raises(DependencyMutationTimeoutUnknownError) as exc_info:
        stripe_service.create_payment_intent(
            amount_cents=500,
            currency="USD",
            idempotency_key="checkout-payment-intent",
            metadata={"source": "test"},
        )

    contract = exc_info.value.contract
    assert contract.code == DEPENDENCY_MUTATION_TIMEOUT_UNKNOWN_CODE
    assert contract.details["outcome"] == "unknown"
    assert "private provider diagnostic" not in contract.detail
    assert captured_options == [{"idempotency_key": "checkout-payment-intent"}]


def test_firebase_initialization_uses_shared_http_timeout(monkeypatch):
    captured: dict[str, object] = {}
    fake_credential = object()
    fake_settings = SimpleNamespace(
        firebase_http_timeout_seconds=8,
        firebase_project_id="pickup-lane-synthetic",
    )

    monkeypatch.setattr(firebase_admin_client.firebase_admin, "_apps", {}, raising=False)
    monkeypatch.setattr(firebase_admin_client, "_firebase_settings", lambda: fake_settings)
    monkeypatch.setattr(
        firebase_admin_client,
        "_load_firebase_credentials",
        lambda settings: fake_credential,
    )

    def fake_initialize_app(credential, options):
        captured["credential"] = credential
        captured["options"] = options

    monkeypatch.setattr(
        firebase_admin_client.firebase_admin,
        "initialize_app",
        fake_initialize_app,
    )

    firebase_admin_client.initialize_firebase_admin()

    assert captured == {
        "credential": fake_credential,
        "options": {
            "httpTimeout": 8,
            "projectId": "pickup-lane-synthetic",
        },
    }


def test_firebase_read_and_mutation_timeouts_have_distinct_semantics(monkeypatch):
    monkeypatch.setattr(firebase_admin_client, "initialize_firebase_admin", lambda: None)
    monkeypatch.setattr(
        firebase_admin_client.auth,
        "verify_id_token",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(TimeoutError("private")),
    )
    monkeypatch.setattr(
        firebase_admin_client.auth,
        "delete_user",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(TimeoutError("private")),
    )

    with pytest.raises(DependencyReadTimeoutError) as read_exc:
        firebase_admin_client.verify_firebase_token("synthetic-token")

    with pytest.raises(DependencyMutationTimeoutUnknownError) as mutation_exc:
        firebase_admin_client.delete_firebase_user("synthetic-auth-user")

    assert read_exc.value.contract.code == DEPENDENCY_READ_TIMEOUT_CODE
    assert mutation_exc.value.contract.code == DEPENDENCY_MUTATION_TIMEOUT_UNKNOWN_CODE
    assert read_exc.value.contract.details["outcome"] == "retry_later"
    assert mutation_exc.value.contract.details["outcome"] == "unknown"


def test_r2_metadata_timeouts_reach_client_config(monkeypatch):
    captured: dict[str, object] = {}

    def fake_boto_client(*_args, **kwargs):
        captured["config"] = kwargs["config"]
        return object()

    monkeypatch.setattr(r2_storage_service.boto3, "client", fake_boto_client)

    r2_storage_service.get_r2_client(_r2_config())

    config = captured["config"]
    assert config.connect_timeout == 2
    assert config.read_timeout == 6
    assert config.retries is None


def test_r2_head_timeout_maps_to_dependency_read_timeout(monkeypatch):
    class FakeClient:
        def head_object(self, **_kwargs):
            raise r2_storage_service.ReadTimeoutError(
                endpoint_url="https://storage.example.test"
            )

    monkeypatch.setattr(r2_storage_service, "get_r2_storage_config", _r2_config)
    monkeypatch.setattr(r2_storage_service, "get_r2_client", lambda _config: FakeClient())

    with pytest.raises(DependencyReadTimeoutError) as exc_info:
        r2_storage_service.get_object_properties("venue/object")

    assert exc_info.value.contract.code == DEPENDENCY_READ_TIMEOUT_CODE
    assert "private provider diagnostic" not in exc_info.value.contract.detail


def test_r2_presigned_url_generation_is_not_metadata_timeout_work(monkeypatch):
    class FakeClient:
        def generate_presigned_url(self, *_args, **_kwargs):
            raise r2_storage_service.ReadTimeoutError(
                endpoint_url="https://storage.example.test"
            )

    monkeypatch.setattr(r2_storage_service, "get_r2_storage_config", _r2_config)
    monkeypatch.setattr(r2_storage_service, "get_r2_client", lambda _config: FakeClient())

    with pytest.raises(R2StorageError):
        r2_storage_service.create_object_upload_url(
            object_key="venue/object",
            content_type="image/png",
        )


def _r2_config() -> R2StorageConfig:
    return R2StorageConfig(
        account_id="synthetic-account",
        access_key_id="synthetic-access-key",
        secret_access_key="synthetic-secret-key",
        endpoint_url="https://storage.example.test",
        bucket_name="synthetic-bucket",
        upload_url_minutes=15,
        read_url_minutes=60,
        max_image_bytes=1024,
        allowed_image_types=frozenset({"image/png"}),
        metadata_connect_timeout_seconds=2,
        metadata_read_timeout_seconds=6,
    )
