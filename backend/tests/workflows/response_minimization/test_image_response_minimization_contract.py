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

GAME_IMAGE_PUBLIC_ALLOWED = {
    "id",
    "game_id",
    "image_url",
    "image_role",
    "is_primary",
    "sort_order",
}
GAME_IMAGE_INTERNAL_FIELDS = {
    "uploaded_by_user_id",
    "image_status",
    "created_at",
    "updated_at",
    "deleted_at",
}
VENUE_IMAGE_PUBLIC_ALLOWED = {
    "id",
    "venue_id",
    "image_url",
    "image_role",
    "is_primary",
    "sort_order",
    "alt_text",
    "caption",
}
VENUE_IMAGE_STORAGE_FIELDS = {
    "uploaded_by_user_id",
    "storage_provider",
    "storage_object_key",
    "storage_bucket",
    "storage_account_id",
    "content_type",
    "size_bytes",
    "etag",
    "image_status",
    "upload_requested_at",
    "upload_completed_at",
    "created_at",
    "updated_at",
    "deleted_at",
}


def _session() -> Session:
    from backend.database import SessionLocal

    return SessionLocal()


def _create_user(
    db: Session,
    *,
    role: str = "player",
    email_prefix: str = "b2-image",
):
    from backend.models import User

    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        auth_user_id=f"{email_prefix}-{user_id}",
        role=role,
        email=f"{email_prefix}-{user_id}@example.invalid",
        email_verified_at=datetime.now(UTC),
        first_name="B2",
        last_name="Image",
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
        name="B2 Image Park",
        address_line_1="500 Gallery Rd",
        city="Chicago",
        state="IL",
        postal_code="60603",
        country_code="US",
        venue_status="approved",
        is_active=True,
        created_by_user_id=admin_user.id,
        approved_by_user_id=admin_user.id,
        approved_at=datetime.now(UTC),
    )
    db.add(venue)
    db.flush()
    return venue


def _create_game(db: Session, *, host_user, admin_user, venue):
    from backend.models import Game

    starts_at = datetime.now(UTC).replace(microsecond=0) + timedelta(days=7)
    game = Game(
        id=uuid.uuid4(),
        game_type="community",
        payment_collection_type="external_host",
        publish_status="published",
        game_status="active",
        public_visibility_status="visible",
        join_enforcement_status="open",
        title="B2 Image Game",
        description="Image response proof.",
        venue_id=venue.id,
        venue_name_snapshot=venue.name,
        address_snapshot="500 Gallery Rd, Chicago, IL 60603",
        city_snapshot=venue.city,
        state_snapshot=venue.state,
        neighborhood_snapshot=None,
        host_user_id=host_user.id,
        created_by_user_id=admin_user.id,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=2),
        starts_on_local=starts_at.astimezone(CHICAGO).date(),
        timezone="America/Chicago",
        sport_type="soccer",
        format_label="5v5",
        game_player_group="coed",
        skill_level="any",
        environment_type="outdoor",
        total_spots=12,
        price_per_player_cents=1400,
        currency="USD",
        minimum_age=18,
        allow_guests=True,
        max_guests_per_booking=2,
        host_guest_max=4,
        waitlist_enabled=True,
        is_chat_enabled=True,
        policy_mode="custom_hosted",
        published_at=datetime.now(UTC),
    )
    db.add(game)
    db.flush()
    return game


def _create_image_rows(db: Session, *, admin):
    from backend.models import GameImage, VenueImage

    venue = _create_venue(db, admin_user=admin)
    game = _create_game(db, host_user=admin, admin_user=admin, venue=venue)
    game_image = GameImage(
        id=uuid.uuid4(),
        game_id=game.id,
        uploaded_by_user_id=admin.id,
        image_url="https://cdn.example.invalid/game-card.jpg",
        image_role="card",
        image_status="active",
        is_primary=True,
        sort_order=0,
    )
    venue_image = VenueImage(
        id=uuid.uuid4(),
        venue_id=venue.id,
        uploaded_by_user_id=admin.id,
        storage_provider="r2",
        storage_object_key=f"venues/{venue.id}/primary-{uuid.uuid4()}.jpg",
        storage_bucket="pickup-lane-test",
        storage_account_id="acct-test",
        content_type="image/jpeg",
        size_bytes=12345,
        etag="test-etag",
        image_role="card",
        image_status="active",
        is_primary=True,
        sort_order=0,
        alt_text="Field view",
        caption="North field",
        upload_completed_at=datetime.now(UTC),
    )
    db.add_all([game_image, venue_image])
    db.flush()
    return venue, game_image, venue_image


def _install_active_admin_override(user) -> None:
    from backend.main import app
    from backend.services.auth_service import require_active_admin

    app.dependency_overrides[require_active_admin] = lambda: user


def _commit_and_detach(db: Session, *objects: object) -> None:
    db.commit()
    for item in objects:
        db.refresh(item)
        db.expunge(item)


def _route(method: str, path: str) -> APIRoute:
    from backend.main import app

    for route in app.routes:
        if isinstance(route, APIRoute) and route.path == path and method in route.methods:
            return route
    raise AssertionError(f"Route not found: {method} {path}")


@pytest.mark.requirement("WS02-05B2-R5")
def test_public_game_and_venue_image_responses_exclude_internal_metadata(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "backend.services.venue_image_service.create_object_read_url",
        lambda object_key: f"https://cdn.example.invalid/{object_key}",
    )

    with _session() as db:
        admin = _create_user(db, role="admin", email_prefix="b2-image-admin")
        venue, game_image, venue_image = _create_image_rows(db, admin=admin)
        venue_id = venue.id
        game_image_id = game_image.id
        venue_image_id = venue_image.id
        _commit_and_detach(db, admin)

    game_image_response = client.get(f"/game-images/{game_image_id}")
    assert game_image_response.status_code == 200
    game_image_data = game_image_response.json()
    assert set(game_image_data) == GAME_IMAGE_PUBLIC_ALLOWED
    assert GAME_IMAGE_INTERNAL_FIELDS.isdisjoint(game_image_data)
    assert game_image_data["image_url"] == "https://cdn.example.invalid/game-card.jpg"

    game_image_list_response = client.get(f"/game-images?image_status=active")
    assert game_image_list_response.status_code == 200
    listed_game_image = next(
        item for item in game_image_list_response.json() if item["id"] == str(game_image_id)
    )
    assert set(listed_game_image) == GAME_IMAGE_PUBLIC_ALLOWED

    venue_image_response = client.get(f"/venue-images?venue_id={venue_id}")
    assert venue_image_response.status_code == 200
    venue_image_data = next(
        item for item in venue_image_response.json() if item["id"] == str(venue_image_id)
    )
    assert set(venue_image_data) == VENUE_IMAGE_PUBLIC_ALLOWED
    assert VENUE_IMAGE_STORAGE_FIELDS.isdisjoint(venue_image_data)
    assert venue_image_data["image_url"].startswith("https://cdn.example.invalid/")
    assert venue_image_data["alt_text"] == "Field view"
    assert venue_image_data["caption"] == "North field"


@pytest.mark.requirement("WS02-05B2-R5")
def test_admin_image_responses_retain_operational_metadata_behind_admin(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "backend.services.venue_image_service.create_object_read_url",
        lambda object_key: f"https://cdn.example.invalid/{object_key}",
    )

    with _session() as db:
        admin = _create_user(db, role="admin", email_prefix="b2-image-admin-rich")
        venue, game_image, venue_image = _create_image_rows(db, admin=admin)
        venue_id = venue.id
        game_image_id = game_image.id
        venue_image_id = venue_image.id
        _commit_and_detach(db, admin)

    _install_active_admin_override(admin)

    admin_game_image_response = client.get(f"/admin/game-images/{game_image_id}")
    assert admin_game_image_response.status_code == 200
    admin_game_image_data = admin_game_image_response.json()
    assert GAME_IMAGE_PUBLIC_ALLOWED.issubset(admin_game_image_data)
    assert GAME_IMAGE_INTERNAL_FIELDS.issubset(admin_game_image_data)

    admin_venue_images_response = client.get(f"/admin/venues/{venue_id}/images")
    assert admin_venue_images_response.status_code == 200
    admin_venue_image_data = next(
        item for item in admin_venue_images_response.json() if item["id"] == str(venue_image_id)
    )
    assert VENUE_IMAGE_PUBLIC_ALLOWED.issubset(admin_venue_image_data)
    assert VENUE_IMAGE_STORAGE_FIELDS.issubset(admin_venue_image_data)
    assert admin_venue_image_data["storage_object_key"]
    assert admin_venue_image_data["storage_bucket"] == "pickup-lane-test"


@pytest.mark.no_db_cleanup
@pytest.mark.requirement("WS02-05B2-R5")
def test_image_routes_declare_public_admin_and_upload_response_models() -> None:
    from backend.schemas import (
        GameImageAdminRead,
        GameImagePublicRead,
        VenueImageAdminRead,
        VenueImagePublicRead,
        VenueImageUploadRead,
    )

    assert _route("GET", "/game-images").response_model == list[GameImagePublicRead]
    assert _route("GET", "/game-images/{game_image_id}").response_model is (
        GameImagePublicRead
    )
    assert _route("GET", "/venue-images").response_model == list[VenueImagePublicRead]
    assert _route("GET", "/admin/game-images").response_model == list[
        GameImageAdminRead
    ]
    assert _route("GET", "/admin/game-images/{game_image_id}").response_model is (
        GameImageAdminRead
    )
    assert _route("GET", "/admin/venues/{venue_id}/images").response_model == list[
        VenueImageAdminRead
    ]
    assert (
        _route("POST", "/admin/venues/{venue_id}/images/upload-url").response_model
        is VenueImageUploadRead
    )
    assert (
        _route("POST", "/admin/venue-images/{venue_image_id}/complete").response_model
        is VenueImageAdminRead
    )
    assert (
        _route("PATCH", "/admin/venue-images/{venue_image_id}").response_model
        is VenueImageAdminRead
    )
