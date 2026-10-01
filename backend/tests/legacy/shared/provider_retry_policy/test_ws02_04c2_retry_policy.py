from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from backend import firebase_admin_client
from backend.observability.timeouts import (
    DependencyMutationTimeoutUnknownError,
)
from backend.services import stripe_service

pytestmark = pytest.mark.no_db_cleanup

REPO_ROOT = Path(__file__).resolve().parents[4]


def test_source_does_not_configure_provider_retry_counts() -> None:
    stripe_source = (REPO_ROOT / "backend/services/stripe_service.py").read_text()
    r2_source = (REPO_ROOT / "backend/services/r2_storage_service.py").read_text()
    firebase_source = (REPO_ROOT / "backend/firebase_admin_client.py").read_text()

    assert "max_network_retries" not in stripe_source
    assert "retries=" not in r2_source
    assert "retries =" not in r2_source
    assert "httpTimeout" in firebase_source
    assert "retry" not in firebase_source.lower()


def test_stripe_mutation_timeout_wrappers_do_not_call_provider_twice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def timed_out(label: str):
        def _call(*_args, **_kwargs):
            calls.append(label)
            raise TimeoutError("private provider diagnostic")

        return _call

    monkeypatch.setattr(stripe_service, "get_stripe_module", lambda: SimpleNamespace())

    mutation_client = SimpleNamespace(
        v1=SimpleNamespace(
            payment_intents=SimpleNamespace(confirm=timed_out("confirm")),
            payment_methods=SimpleNamespace(detach=timed_out("detach")),
            customers=SimpleNamespace(update=timed_out("customer_update")),
        )
    )
    monkeypatch.setattr(
        stripe_service,
        "get_stripe_client_pair",
        lambda: stripe_service.StripeClientPair(
            read=SimpleNamespace(),
            mutation=mutation_client,
        ),
    )

    with pytest.raises(DependencyMutationTimeoutUnknownError):
        stripe_service.confirm_payment_intent(
            "synthetic-payment-intent",
            payment_method_id="synthetic-payment-method",
        )

    with pytest.raises(DependencyMutationTimeoutUnknownError):
        stripe_service.detach_payment_method("synthetic-payment-method")

    with pytest.raises(DependencyMutationTimeoutUnknownError):
        stripe_service.set_customer_default_payment_method(
            customer_id="synthetic-customer",
            payment_method_id="synthetic-payment-method",
        )

    with pytest.raises(DependencyMutationTimeoutUnknownError):
        stripe_service.clear_customer_default_payment_method(
            customer_id="synthetic-customer",
        )

    assert calls == ["confirm", "detach", "customer_update", "customer_update"]


def test_firebase_delete_timeout_does_not_call_provider_twice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def timed_out_delete(*_args, **_kwargs) -> None:
        calls.append("delete")
        raise TimeoutError("private provider diagnostic")

    monkeypatch.setattr(firebase_admin_client, "initialize_firebase_admin", lambda: None)
    monkeypatch.setattr(firebase_admin_client.auth, "delete_user", timed_out_delete)

    with pytest.raises(DependencyMutationTimeoutUnknownError):
        firebase_admin_client.delete_firebase_user("synthetic-auth-user")

    assert calls == ["delete"]


def test_relevant_provider_services_do_not_create_unbounded_async_tasks() -> None:
    service_paths = [
        "backend/services/platform_notice_service.py",
        "backend/services/game_chat_service.py",
        "backend/services/sub_post_chat_service.py",
        "backend/services/need_a_sub_notification_service.py",
        "backend/services/game_waitlist_service.py",
        "backend/services/account_deletion_service.py",
        "backend/services/payment_method_service.py",
        "backend/services/stripe_webhook_service.py",
    ]

    for service_path in service_paths:
        source = (REPO_ROOT / service_path).read_text()
        assert "asyncio.gather(" not in source
        assert "asyncio.create_task(" not in source
        assert ".create_task(" not in source
