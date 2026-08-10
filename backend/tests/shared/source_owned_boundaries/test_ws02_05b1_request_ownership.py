from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func, select

from backend.database import SessionLocal
from backend.models import Game, User
from backend.schemas import (
    AdminMoneyFinancialOutcomeCreate,
    AdminOfficialGameHostAssign,
    GameCreate,
    GameUpdate,
    PaymentEventUpdate,
    UserUpdate,
)
from backend.services.auth_service import (
    VerifiedFirebaseIdentity,
    get_current_app_user,
    get_verified_firebase_identity,
    require_verified_user,
)
from backend.tests.helpers import create_user, create_venue, set_user_role


REMOVED_GENERIC_GAME_REQUEST_FIELDS = {
    "address_snapshot",
    "cancel_reason",
    "cancelled_at",
    "cancelled_by_user_id",
    "cancellation_source",
    "city_snapshot",
    "completed_at",
    "completed_by_user_id",
    "created_by_user_id",
    "currency",
    "custom_cancellation_text",
    "game_status",
    "host_guest_max",
    "join_enforcement_status",
    "minimum_age",
    "payment_collection_type",
    "policy_mode",
    "public_visibility_status",
    "publish_status",
    "published_at",
    "sport_type",
    "starts_on_local",
    "state_snapshot",
    "venue_name_snapshot",
}


def authenticate_as(client: TestClient, user_id: str) -> None:
    def override_current_user() -> User:
        with SessionLocal() as db:
            db_user = db.get(User, UUID(user_id))
            assert db_user is not None
            return db_user

    def override_firebase_identity() -> VerifiedFirebaseIdentity:
        with SessionLocal() as db:
            db_user = db.get(User, UUID(user_id))
            assert db_user is not None
            return VerifiedFirebaseIdentity(
                auth_user_id=db_user.auth_user_id,
                email=db_user.email,
                email_verified=True,
            )

    client.app.dependency_overrides[get_current_app_user] = override_current_user
    client.app.dependency_overrides[get_verified_firebase_identity] = (
        override_firebase_identity
    )
    client.app.dependency_overrides[require_verified_user] = override_current_user


def game_count() -> int:
    with SessionLocal() as db:
        return db.scalar(select(func.count()).select_from(Game)) or 0


def load_game(game_id: str) -> Game:
    with SessionLocal() as db:
        db_game = db.get(Game, UUID(game_id))
        assert db_game is not None
        db.expunge(db_game)
        return db_game


def future_window() -> tuple[datetime, datetime]:
    starts_at = datetime.now(UTC) + timedelta(days=7)
    return starts_at, starts_at + timedelta(hours=1)


def game_create_payload(venue: dict, **overrides: object) -> dict:
    starts_at, ends_at = future_window()
    payload = {
        "game_type": "official",
        "title": "WS02-05B1 Match",
        "venue_id": venue["id"],
        "starts_at": starts_at.isoformat(),
        "ends_at": ends_at.isoformat(),
        "timezone": "America/Chicago",
        "format_label": "5v5",
        "game_player_group": "coed",
        "skill_level": "any",
        "environment_type": "indoor",
        "total_spots": 10,
        "price_per_player_cents": 1200,
        "allow_guests": True,
        "max_guests_per_booking": 2,
        "waitlist_enabled": True,
        "is_chat_enabled": True,
        "game_notes": "Bring water.",
        "parking_notes": "Street parking.",
    }
    payload.update(overrides)
    return payload


def game_create_model_payload(**overrides: object) -> dict:
    starts_at, ends_at = future_window()
    payload = {
        "game_type": "official",
        "title": "WS02-05B1 Model Match",
        "venue_id": uuid4(),
        "starts_at": starts_at,
        "ends_at": ends_at,
        "format_label": "5v5",
        "environment_type": "indoor",
        "total_spots": 10,
        "price_per_player_cents": 1200,
    }
    payload.update(overrides)
    return payload


def create_game_as_admin(client: TestClient, admin: dict, venue: dict) -> dict:
    authenticate_as(client, admin["id"])
    response = client.post("/games", json=game_create_payload(venue))
    assert response.status_code == status.HTTP_201_CREATED, response.text
    return response.json()


def assert_validation_error(
    response,
    *,
    field_name: str,
    submitted_values: tuple[str, ...] = (),
) -> None:
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT, response.text
    body = response.json()
    assert body["code"] == "API.VALIDATION_FAILED"
    assert isinstance(body["detail"], list)
    assert any(error["loc"] == ["body", field_name] for error in body["detail"])
    assert all(value not in response.text for value in submitted_values)


def request_schema_properties(schema: dict, path: str, method: str) -> set[str]:
    request_schema = schema["paths"][path][method]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    ref = request_schema["$ref"]
    component_name = ref.rsplit("/", 1)[-1]
    component = schema["components"]["schemas"][component_name]
    return set(component.get("properties", {}))


def test_generic_game_create_rejects_overposted_server_fields_before_writes(
    client: TestClient,
) -> None:
    admin = create_user(client)
    other_user = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    before_count = game_count()

    authenticate_as(client, admin["id"])
    response = client.post(
        "/games",
        json=game_create_payload(
            venue,
            created_by_user_id=other_user["id"],
            publish_status="draft",
            venue_name_snapshot="Submitted Field",
        ),
    )

    assert_validation_error(
        response,
        field_name="created_by_user_id",
        submitted_values=(other_user["id"], "draft", "Submitted Field"),
    )
    assert game_count() == before_count


def test_generic_game_create_derives_identity_status_and_snapshots(
    client: TestClient,
) -> None:
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])

    created_game = create_game_as_admin(client, admin, venue)

    assert created_game["created_by_user_id"] == admin["id"]
    assert created_game["venue_name_snapshot"] == venue["name"]
    assert created_game["address_snapshot"] == venue["address_line_1"]
    assert created_game["city_snapshot"] == venue["city"]
    assert created_game["state_snapshot"] == venue["state"]
    assert created_game["publish_status"] == "published"
    assert created_game["game_status"] == "active"
    assert created_game["public_visibility_status"] == "visible"
    assert created_game["join_enforcement_status"] == "open"
    assert created_game["payment_collection_type"] == "in_app"
    assert created_game["policy_mode"] == "official_standard"
    assert created_game["currency"] == "USD"
    assert created_game["sport_type"] == "soccer"
    assert created_game["host_guest_max"] == 0


def test_generic_game_update_rejects_lifecycle_identity_and_snapshot_fields(
    client: TestClient,
) -> None:
    admin = create_user(client)
    other_user = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game_as_admin(client, admin, venue)
    before_game = load_game(game["id"])

    authenticate_as(client, admin["id"])
    response = client.patch(
        f"/games/{game['id']}",
        json={
            "created_by_user_id": other_user["id"],
            "game_status": "cancelled",
            "venue_name_snapshot": "Submitted Update Field",
        },
    )

    assert_validation_error(
        response,
        field_name="created_by_user_id",
        submitted_values=(other_user["id"], "cancelled", "Submitted Update Field"),
    )
    after_game = load_game(game["id"])
    assert after_game.created_by_user_id == before_game.created_by_user_id
    assert after_game.game_status == before_game.game_status
    assert after_game.venue_name_snapshot == before_game.venue_name_snapshot


def test_generic_game_create_and_update_supported_fields_still_work(
    client: TestClient,
) -> None:
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    game = create_game_as_admin(client, admin, venue)

    authenticate_as(client, admin["id"])
    response = client.patch(
        f"/games/{game['id']}",
        json={
            "title": "WS02-05B1 Updated Match",
            "price_per_player_cents": 1500,
            "max_guests_per_booking": 1,
        },
    )

    assert response.status_code == status.HTTP_200_OK, response.text
    body = response.json()
    assert body["title"] == "WS02-05B1 Updated Match"
    assert body["price_per_player_cents"] == 1500
    assert body["max_guests_per_booking"] == 1
    assert body["created_by_user_id"] == admin["id"]


def test_admin_specific_host_assignment_is_not_generic_game_update_input() -> None:
    AdminOfficialGameHostAssign.model_validate(
        {"host_user_id": uuid4(), "reason": "Approved host change"}
    )

    with pytest.raises(ValidationError):
        GameUpdate.model_validate({"host_user_id": uuid4()})


def test_user_and_payment_admin_money_requests_reject_privileged_overposting() -> None:
    for payload in (
        {"role": "admin"},
        {"email_verified_at": datetime.now(UTC).isoformat()},
        {"deleted_at": datetime.now(UTC).isoformat()},
    ):
        with pytest.raises(ValidationError):
            UserUpdate.model_validate(payload)

    for payload in (
        {"raw_payload": {"provider": "payload"}},
        {"provider_event_id": "event-id"},
        {"provider": "stripe"},
    ):
        with pytest.raises(ValidationError):
            PaymentEventUpdate.model_validate(payload)

    with pytest.raises(ValidationError):
        AdminMoneyFinancialOutcomeCreate.model_validate(
            {
                "outcome": "credit",
                "reason": "Approved adjustment",
                "idempotency_key": "ws02-05b1-key",
                "host_user_id": uuid4(),
                "amount_cents": 0,
                "provider_charge_id": "provider-owned",
            }
        )


def test_openapi_no_longer_advertises_removed_generic_game_request_fields(
    client: TestClient,
) -> None:
    schema = client.get("/openapi.json").json()
    create_properties = request_schema_properties(schema, "/games", "post")
    update_properties = request_schema_properties(schema, "/games/{game_id}", "patch")
    host_assign_properties = request_schema_properties(
        schema,
        "/admin/official-games/{game_id}/host",
        "post",
    )

    assert REMOVED_GENERIC_GAME_REQUEST_FIELDS.isdisjoint(create_properties)
    assert REMOVED_GENERIC_GAME_REQUEST_FIELDS.isdisjoint(update_properties)
    assert {"game_type", "venue_id", "starts_at", "price_per_player_cents"} <= (
        create_properties
    )
    assert {"title", "price_per_player_cents", "max_guests_per_booking"} <= (
        update_properties
    )
    assert "host_user_id" in host_assign_properties


def test_game_request_models_reject_removed_privileged_fields() -> None:
    for field_name in REMOVED_GENERIC_GAME_REQUEST_FIELDS:
        create_payload = game_create_model_payload(**{field_name: "submitted"})
        with pytest.raises(ValidationError):
            GameCreate.model_validate(create_payload)
        with pytest.raises(ValidationError):
            GameUpdate.model_validate({field_name: "submitted"})
