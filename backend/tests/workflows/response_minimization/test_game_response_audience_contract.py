from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

pytestmark = pytest.mark.suite_type("ordinary")

CHICAGO = ZoneInfo("America/Chicago")

GAME_DETAIL_PROHIBITED_FIELDS = {
    "created_by_user_id",
    "sport_type",
    "policy_mode",
    "published_at",
    "cancelled_by_user_id",
    "cancellation_source",
    "completed_at",
    "completed_by_user_id",
    "created_at",
    "updated_at",
    "deleted_at",
}
GAME_CARD_PROHIBITED_FIELDS = GAME_DETAIL_PROHIBITED_FIELDS | {
    "description",
    "address_snapshot",
    "host_user_id",
    "host_guest_max",
    "custom_rules_text",
    "custom_cancellation_text",
    "game_notes",
    "parking_notes",
}
PUBLIC_PARTICIPANT_PROHIBITED_FIELDS = {
    "guest_name",
    "guest_email",
    "guest_phone",
    "attendance_status",
    "price_cents",
    "currency",
    "checked_in_at",
    "marked_attendance_by_user_id",
    "attendance_decided_at",
    "attendance_notes",
    "created_at",
    "updated_at",
}


def _session() -> Session:
    from backend.database import SessionLocal

    return SessionLocal()


def _create_user(
    db: Session,
    *,
    role: str = "player",
    email_prefix: str = "b2-game",
):
    from backend.models import User

    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        auth_user_id=f"{email_prefix}-{user_id}",
        role=role,
        email=f"{email_prefix}-{user_id}@example.invalid",
        email_verified_at=datetime.now(UTC),
        phone=f"+1555{str(user_id.int)[-10:]}",
        first_name="B2",
        last_name="Audience",
        account_status="active",
        hosting_status="eligible",
    )
    db.add(user)
    db.flush()
    return user


def _create_venue(db: Session, *, admin_user):
    from backend.models import Venue

    venue = Venue(
        id=uuid.uuid4(),
        name="B2 Response Park",
        address_line_1="200 Audience Ave",
        city="Chicago",
        state="IL",
        postal_code="60601",
        country_code="US",
        neighborhood="Loop",
        venue_status="approved",
        is_active=True,
        created_by_user_id=admin_user.id,
        approved_by_user_id=admin_user.id,
        approved_at=datetime.now(UTC),
    )
    db.add(venue)
    db.flush()
    return venue


def _future_schedule(day_offset: int) -> tuple[datetime, datetime]:
    starts_at = datetime.now(UTC).replace(microsecond=0) + timedelta(
        days=day_offset,
        hours=2,
    )
    return starts_at, starts_at + timedelta(hours=2)


def _create_game(
    db: Session,
    *,
    host_user,
    creator_user,
    venue,
    day_offset: int = 3,
    title: str = "B2 Community Response Game",
):
    from backend.models import Game

    starts_at, ends_at = _future_schedule(day_offset)
    game = Game(
        id=uuid.uuid4(),
        game_type="community",
        payment_collection_type="external_host",
        publish_status="published",
        game_status="active",
        public_visibility_status="visible",
        join_enforcement_status="open",
        title=title,
        description="Runtime response field proof.",
        venue_id=venue.id,
        venue_name_snapshot=venue.name,
        address_snapshot="200 Audience Ave, Chicago, IL 60601",
        city_snapshot=venue.city,
        state_snapshot=venue.state,
        neighborhood_snapshot=venue.neighborhood,
        host_user_id=host_user.id,
        created_by_user_id=creator_user.id,
        starts_at=starts_at,
        ends_at=ends_at,
        starts_on_local=starts_at.astimezone(CHICAGO).date(),
        timezone="America/Chicago",
        sport_type="soccer",
        format_label="5v5",
        game_player_group="coed",
        skill_level="any",
        environment_type="outdoor",
        total_spots=12,
        price_per_player_cents=1200,
        currency="USD",
        minimum_age=18,
        allow_guests=True,
        max_guests_per_booking=2,
        host_guest_max=4,
        waitlist_enabled=True,
        is_chat_enabled=True,
        policy_mode="custom_hosted",
        custom_rules_text="Bring a light and dark shirt.",
        custom_cancellation_text="Coordinate refunds with the host.",
        game_notes="Host-only operational note.",
        parking_notes="Use the east lot.",
        published_at=datetime.now(UTC),
    )
    db.add(game)
    db.flush()
    return game


def _create_participant(db: Session, *, game, user):
    from backend.models import GameParticipant

    participant = GameParticipant(
        id=uuid.uuid4(),
        game_id=game.id,
        participant_type="registered_user",
        user_id=user.id,
        display_name_snapshot="B2 Player",
        participant_status="confirmed",
        attendance_status="unknown",
        cancellation_type="none",
        price_cents=game.price_per_player_cents,
        currency="USD",
        roster_order=1,
        confirmed_at=datetime.now(UTC),
    )
    db.add(participant)
    db.flush()
    return participant


def _install_optional_user_override(user) -> None:
    from backend.main import app
    from backend.services.auth_service import get_optional_current_app_user

    app.dependency_overrides[get_optional_current_app_user] = lambda: user


def _install_current_user_override(user) -> None:
    from backend.main import app
    from backend.services.auth_service import get_current_app_user

    app.dependency_overrides[get_current_app_user] = lambda: user


def _install_active_user_override(user) -> None:
    from backend.main import app
    from backend.services.auth_service import require_active_user

    app.dependency_overrides[require_active_user] = lambda: user


def _install_verified_user_override(user) -> None:
    from backend.main import app
    from backend.services.auth_service import require_verified_user

    app.dependency_overrides[require_verified_user] = lambda: user


def _install_active_admin_override(user) -> None:
    from backend.main import app
    from backend.services.auth_service import require_active_admin

    app.dependency_overrides[require_active_admin] = lambda: user


def _route(method: str, path: str) -> APIRoute:
    from backend.main import app

    for route in app.routes:
        if isinstance(route, APIRoute) and route.path == path and method in route.methods:
            return route
    raise AssertionError(f"Route not found: {method} {path}")


def _commit_and_detach(db: Session, *objects: object) -> None:
    db.commit()
    for item in objects:
        db.refresh(item)
        db.expunge(item)


def _assert_game_detail_minimized(data: dict[str, object]) -> None:
    assert GAME_DETAIL_PROHIBITED_FIELDS.isdisjoint(data)
    assert {
        "id",
        "game_type",
        "title",
        "venue_id",
        "venue_name_snapshot",
        "starts_at",
        "ends_at",
        "price_per_player_cents",
        "host_user_id",
        "host_guest_max",
    }.issubset(data)


@pytest.mark.requirement("WS02-05B2-R1")
@pytest.mark.requirement("WS02-05B2-R2")
def test_game_detail_masks_host_fields_for_public_and_non_host_audiences(
    client: TestClient,
) -> None:
    with _session() as db:
        host = _create_user(db, email_prefix="b2-game-host")
        non_host = _create_user(db, email_prefix="b2-game-player")
        admin = _create_user(db, role="admin", email_prefix="b2-game-admin")
        venue = _create_venue(db, admin_user=admin)
        game = _create_game(db, host_user=host, creator_user=admin, venue=venue)
        game_id = game.id
        host_id = host.id
        _commit_and_detach(db, host, non_host, admin)

    public_response = client.get(f"/games/{game_id}")
    assert public_response.status_code == 200
    public_data = public_response.json()
    _assert_game_detail_minimized(public_data)
    assert public_data["host_user_id"] is None
    assert public_data["host_guest_max"] == 0

    _install_optional_user_override(non_host)
    non_host_response = client.get(f"/games/{game_id}")
    assert non_host_response.status_code == 200
    non_host_data = non_host_response.json()
    _assert_game_detail_minimized(non_host_data)
    assert non_host_data["host_user_id"] is None
    assert non_host_data["host_guest_max"] == 0

    _install_optional_user_override(host)
    host_response = client.get(f"/games/{game_id}")
    assert host_response.status_code == 200
    host_data = host_response.json()
    _assert_game_detail_minimized(host_data)
    assert host_data["host_user_id"] == str(host_id)
    assert host_data["host_guest_max"] == 4

    _install_optional_user_override(admin)
    admin_response = client.get(f"/games/{game_id}")
    assert admin_response.status_code == 200
    admin_data = admin_response.json()
    _assert_game_detail_minimized(admin_data)
    assert admin_data["host_user_id"] == str(host_id)
    assert admin_data["host_guest_max"] == 4


@pytest.mark.requirement("WS02-05B2-R1")
def test_public_game_lists_browse_cards_roster_and_counts_are_minimized(
    client: TestClient,
) -> None:
    with _session() as db:
        host = _create_user(db, email_prefix="b2-game-list-host")
        player = _create_user(db, email_prefix="b2-game-list-player")
        admin = _create_user(db, role="admin", email_prefix="b2-game-list-admin")
        venue = _create_venue(db, admin_user=admin)
        game = _create_game(db, host_user=host, creator_user=admin, venue=venue)
        participant = _create_participant(db, game=game, user=player)
        game_id = game.id
        participant_id = participant.id
        starts_on = game.starts_on_local.isoformat()
        db.commit()

    list_response = client.get("/games")
    assert list_response.status_code == 200
    listed_game = next(item for item in list_response.json() if item["id"] == str(game_id))
    _assert_game_detail_minimized(listed_game)
    assert listed_game["host_user_id"] is None
    assert listed_game["host_guest_max"] == 0

    browse_response = client.get(f"/games/browse?starts_on={starts_on}")
    assert browse_response.status_code == 200
    browse_data = browse_response.json()
    assert {"games", "time_groups", "browse_date", "next_cursor", "has_more"}.issubset(
        browse_data
    )
    browse_game = next(item for item in browse_data["games"] if item["id"] == str(game_id))
    assert GAME_CARD_PROHIBITED_FIELDS.isdisjoint(browse_game)
    assert {
        "display_title",
        "availability",
        "participant_count",
        "price_label",
        "primary_image_url",
    }.issubset(browse_game)

    participants_response = client.get(f"/games/{game_id}/participants")
    assert participants_response.status_code == 200
    participant_data = next(
        item for item in participants_response.json() if item["id"] == str(participant_id)
    )
    assert PUBLIC_PARTICIPANT_PROHIBITED_FIELDS.isdisjoint(participant_data)
    assert {
        "id",
        "game_id",
        "participant_type",
        "user_id",
        "display_name_snapshot",
        "participant_status",
    }.issubset(participant_data)

    counts_response = client.get("/games/participant-counts")
    assert counts_response.status_code == 200
    count_data = next(item for item in counts_response.json() if item["game_id"] == str(game_id))
    assert set(count_data) == {"game_id", "participant_count"}
    assert count_data["participant_count"] == 1


@pytest.mark.requirement("WS02-05B2-R1")
def test_my_games_current_user_card_response_is_minimized(
    client: TestClient,
) -> None:
    with _session() as db:
        host = _create_user(db, email_prefix="b2-my-games-host")
        player = _create_user(db, email_prefix="b2-my-games-player")
        admin = _create_user(db, role="admin", email_prefix="b2-my-games-admin")
        venue = _create_venue(db, admin_user=admin)
        game = _create_game(db, host_user=host, creator_user=admin, venue=venue)
        participant = _create_participant(db, game=game, user=player)
        game_id = game.id
        participant_id = participant.id
        _commit_and_detach(db, player)

    _install_active_user_override(player)
    response = client.get("/my-games?view=upcoming&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"items", "next_cursor", "has_more", "limit"}
    assert data["limit"] == 10

    item = next(
        entry for entry in data["items"] if entry["game"]["id"] == str(game_id)
    )
    assert set(item) == {
        "bucket",
        "game",
        "is_host",
        "participant_id",
        "participant_status",
        "cancellation_type",
        "status_label",
        "status_tone",
    }
    assert item["bucket"] == "upcoming"
    assert item["is_host"] is False
    assert item["participant_id"] == str(participant_id)
    assert item["participant_status"] == "confirmed"

    game_card = item["game"]
    assert GAME_CARD_PROHIBITED_FIELDS.isdisjoint(game_card)
    assert {
        "id",
        "display_title",
        "starts_at",
        "ends_at",
        "venue_name_snapshot",
        "city_snapshot",
        "state_snapshot",
        "availability",
        "participant_count",
        "price_label",
        "primary_image_url",
    }.issubset(game_card)


@pytest.mark.requirement("WS02-05B2-R1")
def test_current_user_game_participants_response_uses_public_participant_projection(
    client: TestClient,
) -> None:
    with _session() as db:
        host = _create_user(db, email_prefix="b2-my-participants-host")
        player = _create_user(db, email_prefix="b2-my-participants-player")
        admin = _create_user(db, role="admin", email_prefix="b2-my-participants-admin")
        venue = _create_venue(db, admin_user=admin)
        game = _create_game(db, host_user=host, creator_user=admin, venue=venue)
        participant = _create_participant(db, game=game, user=player)
        participant_id = participant.id
        game_id = game.id
        _commit_and_detach(db, player)

    _install_current_user_override(player)
    response = client.get("/game-participants/me")
    assert response.status_code == 200
    participant_data = next(
        item for item in response.json() if item["id"] == str(participant_id)
    )
    assert PUBLIC_PARTICIPANT_PROHIBITED_FIELDS.isdisjoint(participant_data)
    assert {
        "id",
        "game_id",
        "booking_id",
        "participant_type",
        "user_id",
        "guest_of_user_id",
        "display_name_snapshot",
        "participant_status",
        "cancellation_type",
        "roster_order",
        "joined_at",
        "confirmed_at",
        "cancelled_at",
    } == set(participant_data)
    assert participant_data["game_id"] == str(game_id)
    assert participant_data["user_id"] == str(player.id)
    assert participant_data["participant_status"] == "confirmed"


@pytest.mark.requirement("WS02-05B2-R1")
@pytest.mark.requirement("WS02-05B2-R2")
def test_game_mutation_returns_use_detail_contract_and_generic_game_read_stays_admin(
    client: TestClient,
) -> None:
    from backend.schemas.game_schema import GameDetailRead, GameRead

    with _session() as db:
        host = _create_user(db, email_prefix="b2-game-mutation-host")
        admin = _create_user(db, role="admin", email_prefix="b2-game-mutation-admin")
        venue = _create_venue(db, admin_user=admin)
        cancel_game = _create_game(
            db,
            host_user=host,
            creator_user=admin,
            venue=venue,
            day_offset=4,
            title="B2 Cancel Response",
        )
        edit_game = _create_game(
            db,
            host_user=host,
            creator_user=admin,
            venue=venue,
            day_offset=5,
            title="B2 Host Edit Response",
        )
        cancel_game_id = cancel_game.id
        edit_game_id = edit_game.id
        host_id = host.id
        _commit_and_detach(db, host, admin)

    _install_verified_user_override(host)

    cancel_response = client.post(
        f"/games/{cancel_game_id}/cancel",
        json={"cancel_reason": "Weather moved this game."},
    )
    assert cancel_response.status_code == 200
    cancel_data = cancel_response.json()
    _assert_game_detail_minimized(cancel_data)
    assert cancel_data["game_status"] == "cancelled"
    assert cancel_data["host_user_id"] == str(host_id)
    assert cancel_data["host_guest_max"] == 4
    assert "cancellation_source" not in cancel_data
    assert "cancelled_by_user_id" not in cancel_data

    edit_response = client.patch(
        f"/games/{edit_game_id}/host-edit",
        json={"parking_notes": "Updated host parking note."},
    )
    assert edit_response.status_code == 200
    edit_data = edit_response.json()
    _assert_game_detail_minimized(edit_data)
    assert edit_data["parking_notes"] == "Updated host parking note."
    assert edit_data["host_user_id"] == str(host_id)

    assert _route("POST", "/games/{game_id}/cancel").response_model is GameDetailRead
    assert _route("PATCH", "/games/{game_id}/host-edit").response_model is GameDetailRead
    assert _route("POST", "/games").response_model is GameRead
    assert _route("PATCH", "/games/{game_id}").response_model is GameRead
    assert _route("DELETE", "/games/{game_id}").response_model is GameRead

    _install_active_admin_override(admin)
    generic_response = client.patch(
        f"/games/{edit_game_id}",
        json={"title": "B2 Admin Generic GameRead Response"},
    )
    assert generic_response.status_code == 200
    generic_data = generic_response.json()
    assert GAME_DETAIL_PROHIBITED_FIELDS.issubset(generic_data)
    assert generic_data["created_by_user_id"]
    assert generic_data["policy_mode"] == "custom_hosted"
