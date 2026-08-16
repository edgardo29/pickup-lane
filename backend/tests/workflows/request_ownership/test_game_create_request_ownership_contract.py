from __future__ import annotations

import uuid
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.schemas.game_schema import GameCreate

pytestmark = pytest.mark.suite_type("ordinary")

GAME_CREATE_ALLOWED_FIELDS = {
    "game_type",
    "title",
    "description",
    "venue_id",
    "host_user_id",
    "starts_at",
    "ends_at",
    "timezone",
    "format_label",
    "game_player_group",
    "skill_level",
    "environment_type",
    "total_spots",
    "price_per_player_cents",
    "allow_guests",
    "max_guests_per_booking",
    "waitlist_enabled",
    "is_chat_enabled",
    "custom_rules_text",
    "game_notes",
    "parking_notes",
}
GAME_CREATE_PROTECTED_FIELDS = {
    "id",
    "payment_collection_type",
    "publish_status",
    "game_status",
    "public_visibility_status",
    "join_enforcement_status",
    "venue_name_snapshot",
    "address_snapshot",
    "city_snapshot",
    "state_snapshot",
    "neighborhood_snapshot",
    "created_by_user_id",
    "starts_on_local",
    "sport_type",
    "currency",
    "minimum_age",
    "host_guest_max",
    "policy_mode",
    "custom_cancellation_text",
    "published_at",
    "cancelled_at",
    "cancelled_by_user_id",
    "cancellation_source",
    "cancel_reason",
    "completed_at",
    "completed_by_user_id",
    "created_at",
    "updated_at",
    "deleted_at",
}
STARTS_AT = datetime(2035, 1, 15, 18, 0, tzinfo=UTC)
ENDS_AT = datetime(2035, 1, 15, 20, 0, tzinfo=UTC)
CHICAGO = ZoneInfo("America/Chicago")


def _session() -> Session:
    from backend.database import SessionLocal

    return SessionLocal()


def _install_active_admin_override(admin_user) -> None:
    from backend.main import app
    from backend.services.auth_service import require_active_admin

    app.dependency_overrides[require_active_admin] = lambda: admin_user


def _create_user(db: Session, *, role: str = "player", email_prefix: str = "b1"):
    from backend.models import User

    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        auth_user_id=f"{email_prefix}-{user_id}",
        role=role,
        email=f"{email_prefix}-{user_id}@example.invalid",
        first_name="B1",
        last_name="Owner",
        account_status="active",
        hosting_status="eligible",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.expunge(user)
    return user


def _create_venue(db: Session, *, admin_user):
    from backend.models import Venue

    venue = Venue(
        id=uuid.uuid4(),
        name="B1 Source Park",
        address_line_1="100 Source Truth Way",
        city="Austin",
        state="TX",
        postal_code="78701",
        country_code="US",
        neighborhood="East B1",
        venue_status="approved",
        is_active=True,
        created_by_user_id=admin_user.id,
        approved_by_user_id=admin_user.id,
        approved_at=datetime.now(UTC),
    )
    db.add(venue)
    db.commit()
    db.refresh(venue)
    db.expunge(venue)
    return venue


def _count_games(db: Session) -> int:
    from backend.models import Game

    return int(db.scalar(select(func.count()).select_from(Game)) or 0)


def _get_game(game_id: uuid.UUID):
    from backend.models import Game

    with _session() as db:
        return db.get(Game, game_id)


def _base_payload(venue_id: uuid.UUID, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "game_type": "community",
        "title": "B1 Generic Create",
        "description": "Allowed caller text",
        "venue_id": str(venue_id),
        "starts_at": STARTS_AT.isoformat(),
        "ends_at": ENDS_AT.isoformat(),
        "timezone": "America/Chicago",
        "format_label": "5v5",
        "game_player_group": "coed",
        "skill_level": "any",
        "environment_type": "indoor",
        "total_spots": 12,
        "price_per_player_cents": 1200,
        "allow_guests": True,
        "max_guests_per_booking": 2,
        "waitlist_enabled": True,
        "is_chat_enabled": True,
        "custom_rules_text": "Bring shin guards.",
        "game_notes": "Meet by field one.",
        "parking_notes": "Lot A.",
    }
    payload.update(overrides)
    return payload


def _expected_host_guest_max(format_label: str) -> int:
    home_side, separator, away_side = format_label.strip().lower().partition("v")
    assert separator == "v"
    assert home_side == away_side
    assert home_side.isdigit()
    return max(int(home_side) - 1, 0)


def _resolve_ref(schema: dict[str, object], components: dict[str, object]) -> dict[str, object]:
    ref = schema.get("$ref")
    if isinstance(ref, str):
        name = ref.removeprefix("#/components/schemas/")
        return components[name]
    if "allOf" in schema:
        merged: dict[str, object] = {"properties": {}}
        for item in schema["allOf"]:
            resolved = _resolve_ref(item, components)
            merged["properties"].update(resolved.get("properties", {}))
        return merged
    return schema


def _openapi_request_properties(method: str, path: str) -> set[str]:
    from backend.main import app

    openapi = app.openapi()
    raw_schema = openapi["paths"][path][method.lower()]["requestBody"]["content"][
        "application/json"
    ]["schema"]
    request_schema = _resolve_ref(raw_schema, openapi["components"]["schemas"])
    return set(request_schema.get("properties", {}))


@pytest.mark.no_db_cleanup
@pytest.mark.requirement("WS02-05B1-R1")
def test_game_create_schema_and_openapi_expose_only_request_owned_fields() -> None:
    assert GameCreate.model_config.get("extra") == "forbid"
    assert set(GameCreate.model_fields) == GAME_CREATE_ALLOWED_FIELDS
    assert GAME_CREATE_ALLOWED_FIELDS.isdisjoint(GAME_CREATE_PROTECTED_FIELDS)
    assert _openapi_request_properties("POST", "/games") == GAME_CREATE_ALLOWED_FIELDS


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    (
        ("created_by_user_id", "00000000-0000-4000-8000-000000000001"),
        ("publish_status", "draft"),
        ("payment_collection_type", "in_app"),
        ("venue_name_snapshot", "Caller Forged Park"),
        ("policy_mode", "official_standard"),
        ("host_guest_max", 99),
        ("sport_type", "basketball"),
        ("cancelled_by_user_id", "00000000-0000-4000-8000-000000000002"),
        ("created_at", "2030-01-01T00:00:00+00:00"),
    ),
)
@pytest.mark.requirement("WS02-05B1-R1")
def test_game_create_rejects_representative_protected_overposting_before_persistence(
    client: TestClient,
    field_name: str,
    field_value: object,
) -> None:
    with _session() as db:
        admin = _create_user(db, role="admin", email_prefix="b1-create-admin")
        venue = _create_venue(db, admin_user=admin)
        before_count = _count_games(db)

    _install_active_admin_override(admin)
    payload = _base_payload(venue.id, **{field_name: field_value})

    response = client.post("/games", json=payload)

    assert response.status_code == 422
    with _session() as db:
        assert _count_games(db) == before_count


@pytest.mark.requirement("WS02-05B1-R2")
def test_generic_community_create_derives_protected_fields_from_trusted_sources(
    client: TestClient,
) -> None:
    with _session() as db:
        admin = _create_user(db, role="admin", email_prefix="b1-create-admin")
        host = _create_user(db, email_prefix="b1-create-host")
        venue = _create_venue(db, admin_user=admin)

    _install_active_admin_override(admin)
    payload = _base_payload(venue.id, host_user_id=str(host.id))

    response = client.post("/games", json=payload)

    assert response.status_code == 201, response.text
    game_id = uuid.UUID(response.json()["id"])
    game = _get_game(game_id)

    assert game is not None
    assert game.created_by_user_id == admin.id
    assert game.host_user_id == host.id
    assert game.venue_id == venue.id
    assert game.venue_name_snapshot == venue.name
    assert game.address_snapshot == venue.address_line_1
    assert game.city_snapshot == venue.city
    assert game.state_snapshot == venue.state
    assert game.neighborhood_snapshot == venue.neighborhood
    assert game.payment_collection_type == "external_host"
    assert game.publish_status == "published"
    assert game.game_status == "active"
    assert game.public_visibility_status == "visible"
    assert game.join_enforcement_status == "open"
    assert game.sport_type == "soccer"
    assert game.currency == "USD"
    assert game.minimum_age == 18
    assert game.policy_mode == "custom_hosted"
    assert game.host_guest_max == _expected_host_guest_max("5v5")
    assert game.custom_cancellation_text is None
    assert game.starts_on_local == STARTS_AT.astimezone(CHICAGO).date()
    assert game.published_at is not None
    assert game.cancelled_at is None
    assert game.cancelled_by_user_id is None
    assert game.cancellation_source is None
    assert game.cancel_reason is None
    assert game.completed_at is None
    assert game.completed_by_user_id is None
    assert game.created_at is not None
    assert game.updated_at is not None


@pytest.mark.requirement("WS02-05B1-R2")
def test_generic_official_create_ignores_host_intent_and_applies_official_invariants(
    client: TestClient,
) -> None:
    with _session() as db:
        admin = _create_user(db, role="admin", email_prefix="b1-create-admin")
        caller_supplied_host = _create_user(db, email_prefix="b1-official-host")
        venue = _create_venue(db, admin_user=admin)

    _install_active_admin_override(admin)
    payload = _base_payload(
        venue.id,
        game_type="official",
        title="B1 Official Create",
        host_user_id=str(caller_supplied_host.id),
        custom_rules_text="Caller rule that official games must not keep.",
    )

    response = client.post("/games", json=payload)

    assert response.status_code == 201, response.text
    game = _get_game(uuid.UUID(response.json()["id"]))

    assert game is not None
    assert game.game_type == "official"
    assert game.created_by_user_id == admin.id
    assert game.host_user_id is None
    assert game.venue_name_snapshot == venue.name
    assert game.payment_collection_type == "in_app"
    assert game.policy_mode == "official_standard"
    assert game.minimum_age is None
    assert game.host_guest_max == 0
    assert game.custom_rules_text is None
    assert game.custom_cancellation_text is None
    assert game.sport_type == "soccer"
    assert game.currency == "USD"
    assert game.publish_status == "published"
    assert game.starts_on_local == STARTS_AT.astimezone(CHICAGO).date()
