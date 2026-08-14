from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from backend.schemas.user_payment_method_schema import UserPaymentMethodSyncCreate

pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.suite_type("ordinary")]


def _assert_rejected(**overrides: object) -> None:
    payload = {"setup_intent_id": "seti_test", "set_as_default": False}
    payload.update(overrides)
    with pytest.raises(ValidationError):
        UserPaymentMethodSyncCreate(**payload)


@pytest.mark.requirement("WS02-04B2A2B2-R1")
def test_setup_intent_id_is_trimmed_bounded_and_required() -> None:
    assert UserPaymentMethodSyncCreate(setup_intent_id="  seti_123  ").setup_intent_id == "seti_123"
    assert UserPaymentMethodSyncCreate(setup_intent_id="x" * 255).setup_intent_id == "x" * 255

    with pytest.raises(ValidationError):
        UserPaymentMethodSyncCreate(set_as_default=False)
    _assert_rejected(setup_intent_id="   ")
    _assert_rejected(setup_intent_id="x" * 256)


@pytest.mark.requirement("WS02-04B2A2B2-R1")
def test_setup_intent_id_remains_opaque_and_provider_validation_is_delegated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.database import SessionLocal
    from backend.services import payment_method_service

    retrieved: list[str] = []

    def retrieve_setup_intent(setup_intent_id: str):
        retrieved.append(setup_intent_id)
        raise HTTPException(status_code=502, detail="provider rejected setup intent")

    monkeypatch.setattr(payment_method_service, "stripe_payments_enabled", lambda: True)
    monkeypatch.setattr(payment_method_service, "retrieve_setup_intent", retrieve_setup_intent)

    with SessionLocal() as db:
        with pytest.raises(HTTPException) as exc_info:
            payment_method_service.sync_saved_payment_method(
                db,
                SimpleNamespace(stripe_customer_id="cus_b2a2b2"),
                setup_intent_id="opaque-provider-owned-id",
                set_as_default=False,
            )

    assert exc_info.value.status_code == 502
    assert retrieved == ["opaque-provider-owned-id"]
