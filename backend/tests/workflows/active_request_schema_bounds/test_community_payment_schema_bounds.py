from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from backend.schemas.community_game_detail_schema import (
    CommunityGameDetailCreate,
    CommunityGameDetailHostUpsert,
    CommunityGameDetailUpdate,
)
from backend.schemas.community_game_publish_schema import CommunityGamePublishCreate
from backend.schemas.community_payment_schema import CommunityPaymentMethodSnapshot

pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.suite_type("ordinary")]

_PAYMENT_TYPES = ("venmo", "zelle", "cash_app", "paypal", "apple_cash", "cash", "other")


def _method(method_type: str = "venmo", value: object = "a2a-player") -> dict[str, object]:
    return {"type": method_type, "value": value}


def _assert_rejected(model_factory, **overrides: object) -> None:
    with pytest.raises(ValidationError):
        model_factory(**overrides)


def _publish(**overrides: object) -> CommunityGamePublishCreate:
    payload = {
        "starts_at": "2035-01-15T18:00:00Z",
        "ends_at": "2035-01-15T20:00:00Z",
        "format_label": "5v5",
        "environment_type": "indoor",
        "total_spots": 12,
        "price_per_player_cents": 1200,
        "venue": {
            "name": "A2A Field",
            "address_line_1": "1 Test Way",
            "city": "Austin",
            "state": "TX",
            "postal_code": "78701",
        },
    }
    payload.update(overrides)
    return CommunityGamePublishCreate(**payload)


def _detail_create(**overrides: object) -> CommunityGameDetailCreate:
    payload = {"game_id": uuid.uuid4()}
    payload.update(overrides)
    return CommunityGameDetailCreate(**payload)


@pytest.mark.requirement("WS02-04B2A2A-R3")
def test_payment_method_count_bounds_cover_publish_detail_update_and_upsert() -> None:
    for factory in (_publish, _detail_create, CommunityGameDetailUpdate, CommunityGameDetailHostUpsert):
        assert len(factory(payment_methods_snapshot=[]).payment_methods_snapshot or []) == 0
        two = factory(payment_methods_snapshot=[_method("venmo"), _method("zelle")])
        assert len(two.payment_methods_snapshot or []) == 2
        _assert_rejected(
            factory,
            payment_methods_snapshot=[_method("venmo"), _method("zelle"), _method("cash")],
        )


@pytest.mark.requirement("WS02-04B2A2A-R3")
def test_payment_method_type_literals_and_value_bounds_are_enforced() -> None:
    for method_type in _PAYMENT_TYPES:
        assert CommunityPaymentMethodSnapshot(type=method_type, value="handle").type == method_type

    _assert_rejected(CommunityPaymentMethodSnapshot, type="wire", value="handle")

    assert CommunityPaymentMethodSnapshot(type="venmo", value="x").value == "x"
    assert CommunityPaymentMethodSnapshot(type="venmo", value="x" * 255).value == "x" * 255
    assert CommunityPaymentMethodSnapshot(type="venmo", value="  player  ").value == "player"
    _assert_rejected(CommunityPaymentMethodSnapshot, type="venmo", value="x" * 256)
    _assert_rejected(CommunityPaymentMethodSnapshot, type="venmo", value="   ")
    _assert_rejected(CommunityPaymentMethodSnapshot, type="venmo", value=123)


@pytest.mark.requirement("WS02-04B2A2A-R3")
def test_duplicate_payment_method_types_reject_on_create_update_and_upsert_paths() -> None:
    duplicate_methods = [_method("venmo", "first"), _method("venmo", "second")]
    for factory in (_publish, _detail_create, CommunityGameDetailHostUpsert):
        _assert_rejected(factory, payment_methods_snapshot=duplicate_methods)

    assert CommunityGameDetailUpdate().payment_methods_snapshot is None
    _assert_rejected(CommunityGameDetailUpdate, payment_methods_snapshot=duplicate_methods)


@pytest.mark.requirement("WS02-04B2A2A-R3")
def test_payment_instructions_are_null_only_and_nested_unknown_fields_reject() -> None:
    for factory in (_publish, _detail_create, CommunityGameDetailUpdate, CommunityGameDetailHostUpsert):
        assert factory().payment_instructions_snapshot is None
        assert factory(payment_instructions_snapshot=None).payment_instructions_snapshot is None
        _assert_rejected(factory, payment_instructions_snapshot="pay after the game")

    _assert_rejected(
        CommunityPaymentMethodSnapshot,
        type="venmo",
        value="player",
        unsupported_nested_probe="value",
    )
