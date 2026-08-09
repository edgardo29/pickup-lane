from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.schemas.admin_money_financial_outcome_schema import (
    AdminMoneyFinancialOutcomeCreate,
)
from backend.schemas.admin_official_game_schema import (
    AdminOfficialGameCreate,
    AdminOfficialGamePlayerRemovalExecute,
    AdminOfficialGameUpdate,
)
from backend.schemas.admin_review_schema import AdminReviewCaseClose
from backend.schemas.auth_schema import AuthDeleteAccountRequest
from backend.schemas.chat_message_schema import ChatMessageCreate
from backend.schemas.checkout_schema import GameCheckoutPaymentIntentCreate
from backend.schemas.community_game_detail_schema import (
    CommunityGameDetailCreate,
    CommunityGameDetailHostUpsert,
    CommunityGameDetailUpdate,
)
from backend.schemas.community_game_publish_schema import CommunityGamePublishCreate
from backend.schemas.game_schema import (
    GameBookingGuestAddCreate,
    GameCreate,
    GameGuestAddCreate,
    GameGuestRemoveCreate,
    GameHostEdit,
    GameJoinCreate,
    GameUpdate,
)
from backend.schemas.sub_post_chat_message_schema import SubPostChatMessageCreate
from backend.schemas.sub_post_schema import SubPostCreate, SubPostUpdate
from backend.schemas.support_flag_schema import SupportFlagResolve
from backend.schemas.user_schema import UserUpdate
from backend.schemas.user_settings_schema import UserSettingsCreate, UserSettingsUpdate
from backend.schemas.venue_image_schema import VenueImageUpdate, VenueImageUploadCreate

pytestmark = pytest.mark.no_db_cleanup


def assert_invalid(schema_class, payload: dict) -> None:
    with pytest.raises(ValidationError):
        schema_class.model_validate(payload)


def future_window() -> tuple[datetime, datetime]:
    starts_at = datetime.now(timezone.utc) + timedelta(days=7)
    return starts_at, starts_at + timedelta(hours=2)


def venue_payload() -> dict:
    return {
        "name": "A2A Field",
        "address_line_1": "10 Boundaries Ave",
        "city": "Chicago",
        "state": "IL",
        "postal_code": "60601",
    }


def game_create_payload(**overrides: object) -> dict:
    starts_at, ends_at = future_window()
    payload = {
        "game_type": "community",
        "title": "A2A Match",
        "venue_id": uuid4(),
        "host_user_id": uuid4(),
        "starts_at": starts_at,
        "ends_at": ends_at,
        "format_label": "5v5",
        "environment_type": "indoor",
        "total_spots": 10,
        "price_per_player_cents": 1200,
    }
    payload.update(overrides)
    return payload


def community_publish_payload(**overrides: object) -> dict:
    starts_at, ends_at = future_window()
    payload = {
        "starts_at": starts_at,
        "ends_at": ends_at,
        "format_label": "5v5",
        "environment_type": "indoor",
        "total_spots": 10,
        "price_per_player_cents": 1200,
        "venue": venue_payload(),
    }
    payload.update(overrides)
    return payload


def admin_official_create_payload(**overrides: object) -> dict:
    starts_at, ends_at = future_window()
    payload = {
        "starts_at": starts_at,
        "ends_at": ends_at,
        "format_label": "5v5",
        "environment_type": "indoor",
        "total_spots": 10,
        "price_per_player_cents": 1200,
        "venue": venue_payload(),
    }
    payload.update(overrides)
    return payload


def sub_post_create_payload(**overrides: object) -> dict:
    starts_at, ends_at = future_window()
    payload = {
        "format_label": "5v5",
        "environment_type": "indoor",
        "skill_level": "any",
        "game_player_group": "coed",
        "starts_at": starts_at,
        "ends_at": ends_at,
        "location_name": "A2A Field",
        "address_line_1": "10 Boundaries Ave",
        "city": "Chicago",
        "state": "IL",
        "postal_code": "60601",
        "subs_needed": 1,
        "price_due_at_venue_cents": 1200,
        "positions": [{"position_label": "goalkeeper", "spots_needed": 1}],
    }
    payload.update(overrides)
    return payload


@pytest.mark.parametrize(
    ("schema_class", "payload"),
    (
        (GameCreate, game_create_payload()),
        (GameUpdate, {"total_spots": 10, "price_per_player_cents": 1200}),
        (GameHostEdit, {"total_spots": 10, "price_per_player_cents": 1200}),
        (CommunityGamePublishCreate, community_publish_payload()),
        (AdminOfficialGameCreate, admin_official_create_payload()),
        (AdminOfficialGameUpdate, {"total_spots": 10, "price_per_player_cents": 1200}),
    ),
)
def test_active_game_capacity_and_price_bounds_accept_approved_values(
    schema_class,
    payload: dict,
) -> None:
    schema_class.model_validate(payload)


@pytest.mark.parametrize(
    ("schema_class", "payload_factory"),
    (
        (GameCreate, game_create_payload),
        (CommunityGamePublishCreate, community_publish_payload),
        (AdminOfficialGameCreate, admin_official_create_payload),
    ),
)
def test_active_create_schemas_reject_capacity_and_price_outside_product_bounds(
    schema_class,
    payload_factory,
) -> None:
    assert_invalid(schema_class, payload_factory(total_spots=5))
    assert_invalid(schema_class, payload_factory(total_spots=100))
    assert_invalid(schema_class, payload_factory(price_per_player_cents=-1))
    assert_invalid(schema_class, payload_factory(price_per_player_cents=99_901))


@pytest.mark.parametrize(
    "schema_class",
    (GameUpdate, GameHostEdit, AdminOfficialGameUpdate),
)
def test_active_update_schemas_reject_capacity_and_price_outside_product_bounds(
    schema_class,
) -> None:
    assert_invalid(schema_class, {"total_spots": 5})
    assert_invalid(schema_class, {"total_spots": 100})
    assert_invalid(schema_class, {"price_per_player_cents": -1})
    assert_invalid(schema_class, {"price_per_player_cents": 99_901})


@pytest.mark.parametrize(
    ("schema_class", "payload"),
    (
        (GameCreate, game_create_payload(max_guests_per_booking=2)),
        (GameUpdate, {"max_guests_per_booking": 2}),
        (AdminOfficialGameCreate, admin_official_create_payload(max_guests_per_booking=2)),
        (AdminOfficialGameUpdate, {"max_guests_per_booking": 2}),
    ),
)
def test_active_game_request_schemas_enforce_two_guest_booking_maximum(
    schema_class,
    payload: dict,
) -> None:
    schema_class.model_validate(payload)
    invalid_payload = dict(payload)
    invalid_payload["max_guests_per_booking"] = 3
    assert_invalid(schema_class, invalid_payload)


def test_generic_game_requests_do_not_accept_direct_host_guest_max() -> None:
    assert_invalid(GameCreate, game_create_payload(host_guest_max=-1))
    assert_invalid(GameCreate, game_create_payload(host_guest_max=3))
    assert_invalid(GameUpdate, {"host_guest_max": -1})
    assert_invalid(GameUpdate, {"host_guest_max": 3})


@pytest.mark.parametrize(
    "schema_class",
    (GameJoinCreate, GameCheckoutPaymentIntentCreate),
)
def test_player_join_and_checkout_guest_count_is_zero_through_two(schema_class) -> None:
    schema_class.model_validate({"guest_count": 0})
    schema_class.model_validate({"guest_count": 2})
    assert_invalid(schema_class, {"guest_count": -1})
    assert_invalid(schema_class, {"guest_count": 3})


def test_booking_guest_add_uses_player_maximum_but_host_guest_add_does_not() -> None:
    GameBookingGuestAddCreate.model_validate({"guest_count": 1})
    GameBookingGuestAddCreate.model_validate({"guest_count": 2})
    assert_invalid(GameBookingGuestAddCreate, {"guest_count": 0})
    assert_invalid(GameBookingGuestAddCreate, {"guest_count": 3})

    GameGuestAddCreate.model_validate({"guest_count": 3})
    assert_invalid(GameGuestAddCreate, {"guest_count": 0})


def test_guest_removal_requires_positive_remove_count() -> None:
    GameGuestRemoveCreate.model_validate({"remove_count": 1})
    assert_invalid(GameGuestRemoveCreate, {"remove_count": 0})


def test_active_profile_updates_reject_dormant_or_server_managed_fields() -> None:
    UserUpdate.model_validate(
        {
            "email": "player@example.com",
            "phone": "+15555550123",
            "first_name": "Alex",
            "last_name": "Player",
            "home_city": "Chicago",
            "home_state": "Illinois",
        }
    )
    assert_invalid(UserUpdate, {"profile_photo_url": "https://example.invalid/photo.jpg"})
    assert_invalid(UserUpdate, {"email_verified_at": datetime.now(timezone.utc)})


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("email", "a" * 256),
        ("phone", "1" * 31),
        ("first_name", "a" * 101),
        ("last_name", "a" * 101),
        ("home_city", "a" * 121),
        ("home_state", "a" * 121),
    ),
)
def test_active_profile_update_lengths_match_current_storage(field_name, value) -> None:
    assert_invalid(UserUpdate, {field_name: value})


def test_account_delete_confirmation_is_validated_in_request_schema() -> None:
    assert AuthDeleteAccountRequest.model_validate(
        {"confirmation": " delete "}
    ).confirmation == "delete"
    assert_invalid(AuthDeleteAccountRequest, {"confirmation": "remove"})


@pytest.mark.parametrize("schema_class", (UserSettingsCreate, UserSettingsUpdate))
def test_active_settings_location_permission_status_is_source_owned(schema_class) -> None:
    payload = {"location_permission_status": "allowed"}
    if schema_class is UserSettingsCreate:
        payload["user_id"] = uuid4()
    schema_class.model_validate(payload)
    payload["location_permission_status"] = "maybe"
    assert_invalid(schema_class, payload)


@pytest.mark.parametrize("schema_class", (SubPostCreate, SubPostUpdate))
def test_need_a_sub_active_price_due_at_venue_uses_approved_ceiling(schema_class) -> None:
    if schema_class is SubPostCreate:
        schema_class.model_validate(sub_post_create_payload(price_due_at_venue_cents=99_900))
        assert_invalid(schema_class, sub_post_create_payload(price_due_at_venue_cents=99_901))
        assert_invalid(schema_class, sub_post_create_payload(price_due_at_venue_cents=-1))
    else:
        schema_class.model_validate({"price_due_at_venue_cents": 99_900})
        assert_invalid(schema_class, {"price_due_at_venue_cents": 99_901})
        assert_invalid(schema_class, {"price_due_at_venue_cents": -1})


@pytest.mark.parametrize(
    "schema_class",
    (ChatMessageCreate, SubPostChatMessageCreate),
)
def test_active_chat_messages_preserve_approved_three_hundred_character_bound(
    schema_class,
) -> None:
    schema_class.model_validate({"chat_id": uuid4(), "message_body": "x" * 300})
    assert_invalid(schema_class, {"chat_id": uuid4(), "message_body": "x" * 301})


@pytest.mark.parametrize(
    "schema_class",
    (
        CommunityGamePublishCreate,
        CommunityGameDetailCreate,
        CommunityGameDetailUpdate,
        CommunityGameDetailHostUpsert,
    ),
)
def test_community_payment_snapshots_are_typed_bounded_and_deduplicated(
    schema_class,
) -> None:
    payload = {
        "payment_methods_snapshot": [
            {"type": "venmo", "value": " @pickup "},
            {"type": "cash", "value": "Bring cash"},
        ],
    }
    if schema_class is CommunityGamePublishCreate:
        payload = community_publish_payload(**payload)
    elif schema_class is CommunityGameDetailCreate:
        payload["game_id"] = uuid4()

    parsed = schema_class.model_validate(payload)
    assert parsed.payment_methods_snapshot[0].value == "@pickup"

    duplicate_payload = dict(payload)
    duplicate_payload["payment_methods_snapshot"] = [
        {"type": "cash", "value": "one"},
        {"type": "cash", "value": "two"},
    ]
    assert_invalid(schema_class, duplicate_payload)

    too_many_payload = dict(payload)
    too_many_payload["payment_methods_snapshot"] = [
        {"type": "venmo", "value": "one"},
        {"type": "zelle", "value": "two"},
        {"type": "cash", "value": "three"},
    ]
    assert_invalid(schema_class, too_many_payload)

    invalid_item_payload = dict(payload)
    invalid_item_payload["payment_methods_snapshot"] = [
        {"type": "venmo", "value": "one", "extra": "not allowed"},
    ]
    assert_invalid(schema_class, invalid_item_payload)


@pytest.mark.parametrize(
    "schema_class",
    (
        CommunityGamePublishCreate,
        CommunityGameDetailCreate,
        CommunityGameDetailUpdate,
        CommunityGameDetailHostUpsert,
    ),
)
def test_community_payment_instructions_are_not_client_supplied(schema_class) -> None:
    payload = {"payment_instructions_snapshot": None}
    if schema_class is CommunityGamePublishCreate:
        payload = community_publish_payload(**payload)
    elif schema_class is CommunityGameDetailCreate:
        payload["game_id"] = uuid4()
    schema_class.model_validate(payload)

    invalid_payload = dict(payload)
    invalid_payload["payment_instructions_snapshot"] = "pay me after the game"
    assert_invalid(schema_class, invalid_payload)


def test_active_admin_outcome_fields_use_proven_service_values() -> None:
    AdminOfficialGamePlayerRemovalExecute.model_validate(
        {
            "preview_token": "x" * 64,
            "outcome": "refund_cash_and_remove_party",
            "reason": "Roster correction",
        }
    )
    AdminMoneyFinancialOutcomeCreate.model_validate(
        {
            "outcome": "credit",
            "reason": "Approved fee credit",
            "idempotency_key": "a2a-money-key",
            "host_user_id": uuid4(),
            "amount_cents": 0,
        }
    )
    AdminReviewCaseClose.model_validate(
        {
            "outcome": "no_action_needed",
            "reason": "Reviewed",
        }
    )
    SupportFlagResolve.model_validate(
        {
            "outcome": "duplicate",
            "reason": "Already handled",
        }
    )

    assert_invalid(
        AdminOfficialGamePlayerRemovalExecute,
        {"preview_token": "x" * 64, "outcome": "refund", "reason": "No"},
    )
    assert_invalid(
        AdminMoneyFinancialOutcomeCreate,
        {
            "outcome": "cash_bonus",
            "reason": "Unsupported",
            "idempotency_key": "a2a-money-key",
        },
    )
    assert_invalid(AdminReviewCaseClose, {"outcome": "closed", "reason": "No"})
    assert_invalid(SupportFlagResolve, {"outcome": "closed", "reason": "No"})


def test_active_admin_reason_and_note_fields_have_operational_ceiling() -> None:
    AdminOfficialGameCreate.model_validate(admin_official_create_payload(reason="x" * 1000))
    assert_invalid(AdminOfficialGameCreate, admin_official_create_payload(reason="x" * 1001))
    AdminMoneyFinancialOutcomeCreate.model_validate(
        {
            "outcome": "manual_review",
            "reason": "x" * 1000,
            "internal_note": "y" * 1000,
            "idempotency_key": "a2a-reason-key",
            "host_user_id": uuid4(),
            "amount_cents": 0,
        }
    )
    assert_invalid(
        AdminMoneyFinancialOutcomeCreate,
        {
            "outcome": "manual_review",
            "reason": "x" * 1001,
            "idempotency_key": "a2a-reason-key",
        },
    )


def test_venue_image_metadata_uses_existing_roles_statuses_and_selected_slots() -> None:
    VenueImageUploadCreate.model_validate(
        {
            "file_name": "field.jpg",
            "content_type": "image/jpeg",
            "size_bytes": 1024,
            "image_role": "gallery",
            "sort_order": 2,
        }
    )
    VenueImageUpdate.model_validate(
        {"image_role": "card", "image_status": "active", "sort_order": 2}
    )
    assert_invalid(
        VenueImageUploadCreate,
        {
            "file_name": "field.jpg",
            "content_type": "image/jpeg",
            "size_bytes": 1024,
            "image_role": "hero",
        },
    )
    assert_invalid(VenueImageUpdate, {"image_status": "approved"})
    assert_invalid(
        VenueImageUploadCreate,
        {
            "file_name": "field.jpg",
            "content_type": "image/jpeg",
            "size_bytes": 1024,
            "sort_order": 3,
        },
    )
    assert_invalid(VenueImageUpdate, {"sort_order": 3})
