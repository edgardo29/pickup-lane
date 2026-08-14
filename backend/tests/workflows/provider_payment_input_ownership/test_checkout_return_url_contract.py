from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.schemas.checkout_schema import GameCheckoutPaymentIntentCreate

pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.suite_type("ordinary")]


def _settings():
    return SimpleNamespace(cors_allowed_origins=["https://app.pickuplane.example"])


def _valid_url(game_id: uuid.UUID) -> str:
    return f"https://app.pickuplane.example/games/{game_id}/checkout"


@pytest.mark.requirement("WS02-04B2A2B2-R3")
def test_checkout_return_url_is_optional_trimmed_and_exactly_scoped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import checkout_service

    game_id = uuid.uuid4()
    monkeypatch.setattr(checkout_service, "get_settings", _settings)

    assert checkout_service.validate_checkout_return_url(None, game_id=game_id) is None
    assert checkout_service.validate_checkout_return_url(
        f"  {_valid_url(game_id)}  ",
        game_id=game_id,
    ) == _valid_url(game_id)


@pytest.mark.requirement("WS02-04B2A2B2-R3")
@pytest.mark.parametrize(
    "url_factory",
    [
        lambda game_id: "   ",
        lambda game_id: "not-a-url",
        lambda game_id: f"ftp://app.pickuplane.example/games/{game_id}/checkout",
        lambda game_id: f"https://user:pass@app.pickuplane.example/games/{game_id}/checkout",
        lambda game_id: f"https://evil.example/games/{game_id}/checkout",
        lambda game_id: f"https://app.pickuplane.example/games/{uuid.uuid4()}/checkout",
        lambda game_id: f"https://app.pickuplane.example/games/{game_id}/checkout?next=/admin",
        lambda game_id: f"https://app.pickuplane.example/games/{game_id}/checkout#done",
    ],
)
def test_checkout_return_url_rejects_unowned_redirect_shapes(
    monkeypatch: pytest.MonkeyPatch,
    url_factory,
) -> None:
    from backend.services import checkout_service

    monkeypatch.setattr(checkout_service, "get_settings", _settings)
    with pytest.raises(HTTPException) as exc_info:
        checkout_service.validate_checkout_return_url(url_factory(uuid.uuid4()), game_id=uuid.uuid4())

    assert exc_info.value.status_code == 400


@pytest.mark.requirement("WS02-04B2A2B2-R3")
def test_invalid_checkout_return_url_rejects_before_db_or_provider_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import checkout_service

    def fail_if_called(*args, **kwargs):
        raise AssertionError("checkout should validate return_url before DB/provider work")

    monkeypatch.setattr(checkout_service, "get_settings", _settings)
    monkeypatch.setattr(checkout_service, "get_locked_active_game_or_404", fail_if_called)
    monkeypatch.setattr(checkout_service, "require_stripe_payments_enabled", fail_if_called)

    with pytest.raises(HTTPException) as exc_info:
        checkout_service.create_game_checkout_payment_intent_workflow(
            object(),
            uuid.uuid4(),
            GameCheckoutPaymentIntentCreate(
                guest_count=0,
                return_url="https://evil.example/games/not-this/checkout",
            ),
            SimpleNamespace(id=uuid.uuid4()),
        )

    assert exc_info.value.status_code == 400
