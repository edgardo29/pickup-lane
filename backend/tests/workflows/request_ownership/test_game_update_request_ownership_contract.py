from __future__ import annotations

import uuid
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.schemas.game_schema import GameUpdate

pytestmark = pytest.mark.suite_type("ordinary")

GAME_UPDATE_ALLOWED_FIELDS = {
    "title",
    "description",
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
GAME_UPDATE_PROTECTED_FIELDS = {
    "id",
    "game_type",
    "payment_collection_type",
    "publish_status",
    "game_status",
    "public_visibility_status",
    "join_enforcement_status",
    "venue_id",
    "venue_name_snapshot",
    "address_snapshot",
    "city_snapshot",
    "state_snapshot",
    "neighborhood_snapshot",
    "host_user_id",
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
STARTS_AT = datetime(2035, 3, 15, 18, 0, tzinfo=UTC)
ENDS_AT = datetime(2035, 3, 15, 20, 0, tzinfo=UTC)
UPDATED_STARTS_AT = datetime(2035, 3, 16, 19, 0, tzinfo=UTC)
UPDATED_ENDS_AT = datetime(2035, 3, 16, 21, 0, tzinfo=UTC)
PUBLISHED_AT = datetime(2034, 1, 1, 12, 0, tzinfo=UTC)
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
        name="B1 Update Park",
        address_line_1="200 Update Way",
        city="Austin",
        state="TX",
        postal_code="78702",
        country_code="US",
        neighborhood="North B1",
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


def _create_game(
    db: Session,
    *,
    admin_user,
    host_user,
    venue,
    game_type: str = "community",
):
    from backend.models import Game

    is_official = game_type == "official"
    game = Game(
        id=uuid.uuid4(),
        game_type=game_type,
        payment_collection_type="in_app" if is_official else "external_host",
        publish_status="published",
        game_status="active",
        public_visibility_status="visible",
        join_enforcement_status="open",
        title="B1 Update Seed",
        description="Original description",
        venue_id=venue.id,
        venue_name_snapshot=venue.name,
        address_snapshot=venue.address_line_1,
        city_snapshot=venue.city,
        state_snapshot=venue.state,
        neighborhood_snapshot=venue.neighborhood,
        host_user_id=None if is_official else host_user.id,
        created_by_user_id=admin_user.id,
        starts_at=STARTS_AT,
        ends_at=ENDS_AT,
        starts_on_local=STARTS_AT.astimezone(CHICAGO).date(),
        timezone="America/Chicago",
        sport_type="soccer",
        format_label="5v5",
        game_player_group="coed",
        skill_level="any",
        environment_type="indoor",
        total_spots=12,
        price_per_player_cents=1200,
        currency="USD",
        minimum_age=None if is_official else 18,
        allow_guests=True,
        max_guests_per_booking=2,
        host_guest_max=0 if is_official else _expected_host_guest_max("5v5"),
        waitlist_enabled=True,
        is_chat_enabled=True,
        policy_mode="official_standard" if is_official else "custom_hosted",
        custom_rules_text=None if is_official else "Original rules",
        custom_cancellation_text=None,
        game_notes="Original notes",
        parking_notes="Original parking",
        published_at=PUBLISHED_AT,
        cancelled_at=None,
        cancelled_by_user_id=None,
        cancellation_source=None,
        cancel_reason=None,
        completed_at=None,
        completed_by_user_id=None,
    )
    db.add(game)
    db.commit()
    db.refresh(game)
    db.expunge(game)
    return game


def _expected_host_guest_max(format_label: str) -> int:
    home_side, separator, away_side = format_label.strip().lower().partition("v")
    assert separator == "v"
    assert home_side == away_side
    assert home_side.isdigit()
    return max(int(home_side) - 1, 0)


def _get_game(game_id: uuid.UUID):
    from backend.models import Game

    with _session() as db:
        return db.get(Game, game_id)


def _protected_snapshot(game) -> dict[str, object]:
    return {
        "game_type": game.game_type,
        "payment_collection_type": game.payment_collection_type,
        "publish_status": game.publish_status,
        "game_status": game.game_status,
        "public_visibility_status": game.public_visibility_status,
        "join_enforcement_status": game.join_enforcement_status,
        "venue_id": game.venue_id,
        "venue_name_snapshot": game.venue_name_snapshot,
        "address_snapshot": game.address_snapshot,
        "city_snapshot": game.city_snapshot,
        "state_snapshot": game.state_snapshot,
        "neighborhood_snapshot": game.neighborhood_snapshot,
        "host_user_id": game.host_user_id,
        "created_by_user_id": game.created_by_user_id,
        "sport_type": game.sport_type,
        "currency": game.currency,
        "minimum_age": game.minimum_age,
        "policy_mode": game.policy_mode,
        "custom_cancellation_text": game.custom_cancellation_text,
        "published_at": game.published_at,
        "cancelled_at": game.cancelled_at,
        "cancelled_by_user_id": game.cancelled_by_user_id,
        "cancellation_source": game.cancellation_source,
        "cancel_reason": game.cancel_reason,
        "completed_at": game.completed_at,
        "completed_by_user_id": game.completed_by_user_id,
        "deleted_at": game.deleted_at,
    }


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
@pytest.mark.requirement("WS02-05B1-R3")
def test_game_update_schema_and_openapi_expose_only_request_owned_fields() -> None:
    assert GameUpdate.model_config.get("extra") == "forbid"
    assert set(GameUpdate.model_fields) == GAME_UPDATE_ALLOWED_FIELDS
    assert GAME_UPDATE_ALLOWED_FIELDS.isdisjoint(GAME_UPDATE_PROTECTED_FIELDS)
    assert _openapi_request_properties("PATCH", "/games/{game_id}") == GAME_UPDATE_ALLOWED_FIELDS


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    (
        ("host_user_id", "00000000-0000-4000-8000-000000000001"),
        ("created_by_user_id", "00000000-0000-4000-8000-000000000002"),
        ("venue_id", "00000000-0000-4000-8000-000000000003"),
        ("venue_name_snapshot", "Caller Patched Park"),
        ("payment_collection_type", "none"),
        ("publish_status", "archived"),
        ("game_status", "cancelled"),
        ("policy_mode", "official_standard"),
        ("host_guest_max", 99),
        ("cancel_reason", "caller cancellation"),
        ("updated_at", "2030-01-01T00:00:00+00:00"),
    ),
)
@pytest.mark.requirement("WS02-05B1-R3", "WS02-05B1-R4")
def test_game_update_rejects_protected_overposting_and_preserves_existing_row(
    client: TestClient,
    field_name: str,
    field_value: object,
) -> None:
    with _session() as db:
        admin = _create_user(db, role="admin", email_prefix="b1-update-admin")
        host = _create_user(db, email_prefix="b1-update-host")
        venue = _create_venue(db, admin_user=admin)
        game = _create_game(db, admin_user=admin, host_user=host, venue=venue)
        game_id = game.id
        before_snapshot = _protected_snapshot(game)
        before_title = game.title
        before_description = game.description

    _install_active_admin_override(admin)

    response = client.patch(
        f"/games/{game_id}",
        json={
            "title": "This allowed field must not be applied",
            field_name: field_value,
        },
    )

    assert response.status_code == 422
    after = _get_game(game_id)
    assert after is not None
    assert _protected_snapshot(after) == before_snapshot
    assert after.title == before_title
    assert after.description == before_description


@pytest.mark.requirement("WS02-05B1-R4")
def test_generic_update_mutates_allowed_fields_and_preserves_protected_fields(
    client: TestClient,
) -> None:
    with _session() as db:
        admin = _create_user(db, role="admin", email_prefix="b1-update-admin")
        host = _create_user(db, email_prefix="b1-update-host")
        venue = _create_venue(db, admin_user=admin)
        game = _create_game(db, admin_user=admin, host_user=host, venue=venue)
        game_id = game.id
        before_snapshot = _protected_snapshot(game)

    _install_active_admin_override(admin)

    response = client.patch(
        f"/games/{game_id}",
        json={
            "title": "B1 Allowed Update",
            "description": "Updated description",
            "starts_at": UPDATED_STARTS_AT.isoformat(),
            "ends_at": UPDATED_ENDS_AT.isoformat(),
            "timezone": "America/Chicago",
            "format_label": "6v6",
            "game_player_group": "women",
            "skill_level": "intermediate",
            "environment_type": "outdoor",
            "total_spots": 18,
            "price_per_player_cents": 1300,
            "allow_guests": False,
            "max_guests_per_booking": 1,
            "waitlist_enabled": False,
            "is_chat_enabled": False,
            "custom_rules_text": "Updated allowed rules",
            "game_notes": "Updated notes",
            "parking_notes": "Updated parking",
        },
    )

    assert response.status_code == 200, response.text
    after = _get_game(game_id)
    assert after is not None
    assert after.title == "B1 Allowed Update"
    assert after.description == "Updated description"
    assert after.starts_at == UPDATED_STARTS_AT
    assert after.ends_at == UPDATED_ENDS_AT
    assert after.starts_on_local == UPDATED_STARTS_AT.astimezone(CHICAGO).date()
    assert after.format_label == "6v6"
    assert after.game_player_group == "women"
    assert after.skill_level == "intermediate"
    assert after.environment_type == "outdoor"
    assert after.total_spots == 18
    assert after.price_per_player_cents == 1300
    assert after.allow_guests is False
    assert after.max_guests_per_booking == 1
    assert after.waitlist_enabled is False
    assert after.is_chat_enabled is False
    assert after.custom_rules_text == "Updated allowed rules"
    assert after.game_notes == "Updated notes"
    assert after.parking_notes == "Updated parking"
    assert after.host_guest_max == _expected_host_guest_max("6v6")
    assert _protected_snapshot(after) == before_snapshot
    assert after.updated_at is not None


@pytest.mark.requirement("WS02-05B1-R4")
def test_generic_official_update_keeps_official_forced_fields_service_owned(
    client: TestClient,
) -> None:
    with _session() as db:
        admin = _create_user(db, role="admin", email_prefix="b1-update-admin")
        host = _create_user(db, email_prefix="b1-unused-official-host")
        venue = _create_venue(db, admin_user=admin)
        game = _create_game(
            db,
            admin_user=admin,
            host_user=host,
            venue=venue,
            game_type="official",
        )
        game_id = game.id

    _install_active_admin_override(admin)

    response = client.patch(
        f"/games/{game_id}",
        json={
            "title": "B1 Official Allowed Update",
            "format_label": "7v7",
            "total_spots": 18,
            "custom_rules_text": "Caller supplied official custom rules",
        },
    )

    assert response.status_code == 200, response.text
    after = _get_game(game_id)
    assert after is not None
    assert after.title == "B1 Official Allowed Update"
    assert after.format_label == "7v7"
    assert after.total_spots == 18
    assert after.host_user_id is None
    assert after.payment_collection_type == "in_app"
    assert after.policy_mode == "official_standard"
    assert after.minimum_age is None
    assert after.host_guest_max == 0
    assert after.custom_rules_text is None
    assert after.custom_cancellation_text is None
