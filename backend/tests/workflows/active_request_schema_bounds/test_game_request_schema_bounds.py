from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from backend.schemas.admin_official_game_schema import (
    AdminOfficialGameCreate,
    AdminOfficialGameUpdate,
)
from backend.schemas.checkout_schema import GameCheckoutPaymentIntentCreate
from backend.schemas.community_game_publish_schema import CommunityGamePublishCreate
from backend.schemas.game_schema import (
    GameBookingGuestAddCreate,
    GameCancelCreate,
    GameCreate,
    GameGuestAddCreate,
    GameGuestRemoveCreate,
    GameHostEdit,
    GameJoinCreate,
    GameUpdate,
)
from backend.schemas.sub_post_position_schema import SubPostPositionCreate
from backend.schemas.sub_post_schema import SubPostCreate, SubPostUpdate

pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.suite_type("ordinary")]

_STARTS_AT = datetime(2035, 1, 15, 18, 0, tzinfo=timezone.utc)
_ENDS_AT = datetime(2035, 1, 15, 20, 0, tzinfo=timezone.utc)


def _assert_rejected(model_factory, **overrides: object) -> None:
    with pytest.raises(ValidationError):
        model_factory(**overrides)


def _venue_payload() -> dict[str, str]:
    return {
        "name": "A2A Field",
        "address_line_1": "1 Test Way",
        "city": "Austin",
        "state": "TX",
        "postal_code": "78701",
    }


def _game_create(**overrides: object) -> GameCreate:
    payload = {
        "game_type": "community",
        "title": "A2A Game",
        "venue_id": uuid.uuid4(),
        "starts_at": _STARTS_AT,
        "ends_at": _ENDS_AT,
        "format_label": "5v5",
        "environment_type": "indoor",
        "total_spots": 12,
        "price_per_player_cents": 1200,
    }
    payload.update(overrides)
    return GameCreate(**payload)


def _community_publish(**overrides: object) -> CommunityGamePublishCreate:
    payload = {
        "starts_at": _STARTS_AT,
        "ends_at": _ENDS_AT,
        "format_label": "5v5",
        "environment_type": "indoor",
        "total_spots": 12,
        "price_per_player_cents": 1200,
        "venue": _venue_payload(),
    }
    payload.update(overrides)
    return CommunityGamePublishCreate(**payload)


def _official_create(**overrides: object) -> AdminOfficialGameCreate:
    payload = {
        "starts_at": _STARTS_AT,
        "ends_at": _ENDS_AT,
        "format_label": "5v5",
        "environment_type": "indoor",
        "total_spots": 12,
        "price_per_player_cents": 1200,
    }
    payload.update(overrides)
    return AdminOfficialGameCreate(**payload)


def _sub_post_create(**overrides: object) -> SubPostCreate:
    payload = {
        "format_label": "5v5",
        "environment_type": "indoor",
        "skill_level": "any",
        "game_player_group": "coed",
        "starts_at": _STARTS_AT,
        "ends_at": _ENDS_AT,
        "location_name": "A2A Field",
        "address_line_1": "1 Test Way",
        "city": "Austin",
        "state": "TX",
        "postal_code": "78701",
        "subs_needed": 1,
        "price_due_at_venue_cents": 0,
        "positions": [SubPostPositionCreate(position_label="field_player")],
    }
    payload.update(overrides)
    return SubPostCreate(**payload)


@pytest.mark.requirement("WS02-04B2A2A-R2")
def test_total_spots_bounds_cover_active_create_and_update_shapes() -> None:
    model_factories = (
        _community_publish,
        _game_create,
        GameUpdate,
        GameHostEdit,
        _official_create,
        AdminOfficialGameUpdate,
    )
    for factory in model_factories:
        assert factory(total_spots=6).total_spots == 6
        assert factory(total_spots=99).total_spots == 99
        _assert_rejected(factory, total_spots=5)
        _assert_rejected(factory, total_spots=100)


@pytest.mark.requirement("WS02-04B2A2A-R2")
def test_price_per_player_cents_bounds_cover_active_create_and_update_shapes() -> None:
    model_factories = (
        _community_publish,
        _game_create,
        GameUpdate,
        GameHostEdit,
        _official_create,
        AdminOfficialGameUpdate,
    )
    for factory in model_factories:
        assert factory(price_per_player_cents=0).price_per_player_cents == 0
        assert factory(price_per_player_cents=99_900).price_per_player_cents == 99_900
        _assert_rejected(factory, price_per_player_cents=-1)
        _assert_rejected(factory, price_per_player_cents=99_901)


@pytest.mark.requirement("WS02-04B2A2A-R2")
def test_max_guests_per_booking_bounds_only_on_exposing_active_shapes() -> None:
    for factory in (_game_create, GameUpdate, _official_create, AdminOfficialGameUpdate):
        assert factory(max_guests_per_booking=0).max_guests_per_booking == 0
        assert factory(max_guests_per_booking=2).max_guests_per_booking == 2
        _assert_rejected(factory, max_guests_per_booking=-1)
        _assert_rejected(factory, max_guests_per_booking=3)


@pytest.mark.requirement("WS02-04B2A2A-R2")
def test_join_checkout_and_booking_guest_count_boundaries() -> None:
    for factory in (GameJoinCreate, GameCheckoutPaymentIntentCreate):
        assert factory(guest_count=0).guest_count == 0
        assert factory(guest_count=2).guest_count == 2
        _assert_rejected(factory, guest_count=-1)
        _assert_rejected(factory, guest_count=3)

    assert GameBookingGuestAddCreate(guest_count=1).guest_count == 1
    assert GameBookingGuestAddCreate(guest_count=2).guest_count == 2
    _assert_rejected(GameBookingGuestAddCreate, guest_count=0)
    _assert_rejected(GameBookingGuestAddCreate, guest_count=3)


@pytest.mark.requirement("WS02-04B2A2A-R2")
def test_host_guest_add_and_guest_removal_do_not_invent_host_upper_bound() -> None:
    assert GameGuestAddCreate(guest_count=1).guest_count == 1
    assert GameGuestAddCreate(guest_count=3).guest_count == 3
    _assert_rejected(GameGuestAddCreate, guest_count=0)

    assert GameGuestRemoveCreate(remove_count=1).remove_count == 1
    _assert_rejected(GameGuestRemoveCreate, remove_count=0)


@pytest.mark.requirement("WS02-04B2A2A-R2")
def test_cancellation_and_join_consent_version_bounds_and_nullability() -> None:
    assert GameCancelCreate(cancel_reason="x" * 500).cancel_reason == "x" * 500
    assert GameCancelCreate().cancel_reason is None
    assert GameCancelCreate(cancel_reason=None).cancel_reason is None
    _assert_rejected(GameCancelCreate, cancel_reason="x" * 501)

    assert GameJoinCreate(auto_charge_consent_version="v" * 50).auto_charge_consent_version == "v" * 50
    assert GameJoinCreate().auto_charge_consent_version is None
    assert GameJoinCreate(auto_charge_consent_version=None).auto_charge_consent_version is None
    _assert_rejected(GameJoinCreate, auto_charge_consent_version="v" * 51)


@pytest.mark.requirement("WS02-04B2A2A-R2")
def test_need_a_sub_price_due_at_venue_bounds_cover_create_and_update() -> None:
    for factory in (_sub_post_create, SubPostUpdate):
        assert factory(price_due_at_venue_cents=0).price_due_at_venue_cents == 0
        assert factory(price_due_at_venue_cents=99_900).price_due_at_venue_cents == 99_900
        _assert_rejected(factory, price_due_at_venue_cents=-1)
        _assert_rejected(factory, price_due_at_venue_cents=99_901)
