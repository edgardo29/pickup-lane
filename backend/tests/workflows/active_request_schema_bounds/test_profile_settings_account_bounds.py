from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.schemas.auth_schema import AuthDeleteAccountRequest
from backend.schemas.user_schema import UserUpdate
from backend.schemas.user_settings_schema import UserSettingsUpdate

pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.suite_type("ordinary")]


def _text(length: int) -> str:
    return "x" * length


def _assert_rejected(model: type[object], **payload: object) -> None:
    with pytest.raises(ValidationError):
        model(**payload)


@pytest.mark.requirement("WS02-04B2A2A-R1")
def test_profile_update_approved_text_bounds_and_nullability() -> None:
    for field_name, max_length in (
        ("phone", 30),
        ("first_name", 100),
        ("last_name", 100),
        ("home_city", 120),
        ("home_state", 120),
    ):
        accepted = UserUpdate(**{field_name: _text(max_length)})
        assert getattr(accepted, field_name) == _text(max_length)

        _assert_rejected(UserUpdate, **{field_name: _text(max_length + 1)})

        explicit_null = UserUpdate(**{field_name: None})
        assert getattr(explicit_null, field_name) is None

    omitted = UserUpdate()
    assert omitted.phone is None
    assert omitted.first_name is None
    assert omitted.last_name is None
    assert omitted.home_city is None
    assert omitted.home_state is None


@pytest.mark.requirement("WS02-04B2A2A-R1")
def test_settings_update_approved_text_bounds_literals_and_nullability() -> None:
    for field_name in ("selected_city", "selected_state"):
        accepted = UserSettingsUpdate(**{field_name: _text(120)})
        assert getattr(accepted, field_name) == _text(120)

        _assert_rejected(UserSettingsUpdate, **{field_name: _text(121)})

        explicit_null = UserSettingsUpdate(**{field_name: None})
        assert getattr(explicit_null, field_name) is None

    for literal in ("unknown", "allowed", "denied", "skipped"):
        accepted = UserSettingsUpdate(location_permission_status=literal)
        assert accepted.location_permission_status == literal

    _assert_rejected(UserSettingsUpdate, location_permission_status="maybe")

    omitted = UserSettingsUpdate()
    assert omitted.location_permission_status is None
    assert omitted.selected_city is None
    assert omitted.selected_state is None


@pytest.mark.requirement("WS02-04B2A2A-R1")
def test_account_deletion_confirmation_trim_and_literal_boundary() -> None:
    assert AuthDeleteAccountRequest(confirmation="DELETE").confirmation == "DELETE"
    assert AuthDeleteAccountRequest(confirmation="delete").confirmation == "delete"
    assert AuthDeleteAccountRequest(confirmation="  DELETE  ").confirmation == "DELETE"

    _assert_rejected(AuthDeleteAccountRequest, confirmation="REMOVE")
    _assert_rejected(AuthDeleteAccountRequest, confirmation="")
    _assert_rejected(AuthDeleteAccountRequest, confirmation="   ")


@pytest.mark.requirement("WS02-04B2A2A-R1")
def test_included_account_profile_schemas_reject_neutral_unknown_fields() -> None:
    for model in (UserUpdate, UserSettingsUpdate, AuthDeleteAccountRequest):
        payload = {"unsupported_a2a_probe": "value"}
        if model is AuthDeleteAccountRequest:
            payload["confirmation"] = "DELETE"
        _assert_rejected(model, **payload)
