from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from backend.tests.workflows.game_community_roster_chat_need_a_sub_relationship_authorization.test_matrix_scope_and_dependencies_contract import (
    _Identity,
    _auth_headers,
    _community_detail,
    _game,
    _install_auth_identities,
    _recent_time,
    _session,
    _sub_position,
    _sub_post,
    _user,
    _venue,
)

pytestmark = pytest.mark.suite_type("ordinary")


@pytest.mark.requirement("WS03-04C-R3", "WS03-04C-R10")
def test_public_catalog_reads_omit_non_public_rows_and_admin_filters(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import GameImage, VenueImage
    from backend.services import venue_image_service

    monkeypatch.setattr(
        venue_image_service,
        "create_object_read_url",
        lambda object_key: f"https://images.example.invalid/{object_key}",
    )

    with _session() as db:
        owner = _user("public-owner")
        active_venue = _venue(owner.id, "active")
        inactive_venue = _venue(owner.id, "inactive", is_active=False)
        visible_game = _game(
            host_user_id=owner.id,
            venue_id=active_venue.id,
            label="visible",
            starts_delta_days=1,
        )
        hidden_game = _game(
            host_user_id=owner.id,
            venue_id=active_venue.id,
            label="hidden",
            public_visibility_status="hidden",
            starts_delta_days=2,
        )
        visible_post = _sub_post(owner_user_id=owner.id, label="visible")
        hidden_post = _sub_post(
            owner_user_id=owner.id,
            label="hidden",
            public_visibility_status="hidden",
            starts_delta_days=6,
        )
        removed_post = _sub_post(
            owner_user_id=owner.id,
            label="removed",
            post_status="removed",
        )
        visible_position = _sub_position(visible_post.id, "visible")
        hidden_position = _sub_position(hidden_post.id, "hidden")
        active_game_image = GameImage(
            id=uuid.uuid4(),
            game_id=visible_game.id,
            uploaded_by_user_id=owner.id,
            image_url="https://images.example.invalid/game-active.jpg",
            image_role="card",
            image_status="active",
            is_primary=True,
            sort_order=1,
        )
        hidden_game_image = GameImage(
            id=uuid.uuid4(),
            game_id=visible_game.id,
            uploaded_by_user_id=owner.id,
            image_url="https://images.example.invalid/game-hidden.jpg",
            image_role="gallery",
            image_status="hidden",
            is_primary=False,
            sort_order=2,
        )
        active_venue_image = VenueImage(
            id=uuid.uuid4(),
            venue_id=active_venue.id,
            uploaded_by_user_id=owner.id,
            storage_provider="r2",
            storage_object_key="ws03c/venue-active.jpg",
            storage_bucket="synthetic",
            storage_account_id="synthetic-account",
            content_type="image/jpeg",
            size_bytes=128,
            etag="synthetic-active",
            image_role="card",
            image_status="active",
            is_primary=True,
            sort_order=1,
        )
        hidden_venue_image = VenueImage(
            id=uuid.uuid4(),
            venue_id=active_venue.id,
            uploaded_by_user_id=owner.id,
            storage_provider="r2",
            storage_object_key="ws03c/venue-hidden.jpg",
            storage_bucket="synthetic",
            storage_account_id="synthetic-account",
            content_type="image/jpeg",
            size_bytes=128,
            etag="synthetic-hidden",
            image_role="gallery",
            image_status="hidden",
            is_primary=False,
            sort_order=2,
        )
        db.add(owner)
        db.flush()
        db.add_all([active_venue, inactive_venue, visible_post, hidden_post, removed_post])
        db.flush()
        db.add_all([visible_game, hidden_game, visible_position, hidden_position])
        db.flush()
        db.add_all(
            [
                active_game_image,
                hidden_game_image,
                active_venue_image,
                hidden_venue_image,
            ]
        )
        db.commit()
        active_venue_id = active_venue.id
        inactive_venue_id = inactive_venue.id
        visible_game_id = visible_game.id
        hidden_game_id = hidden_game.id
        visible_post_id = visible_post.id
        hidden_post_id = hidden_post.id
        removed_post_id = removed_post.id
        active_game_image_id = active_game_image.id
        hidden_game_image_id = hidden_game_image.id
        active_venue_image_id = active_venue_image.id
        hidden_venue_image_id = hidden_venue_image.id
        visible_game_starts_on = visible_game.starts_on_local.isoformat()

    venue_list = client.get("/venues")
    assert venue_list.status_code == 200
    venue_ids = {item["id"] for item in venue_list.json()}
    assert str(active_venue_id) in venue_ids
    assert str(inactive_venue_id) not in venue_ids
    assert client.get(f"/venues/{active_venue_id}").status_code == 200
    assert client.get(f"/venues/{inactive_venue_id}").status_code == 404
    assert client.get("/venues", params={"include_inactive": "true"}).status_code == 403

    game_list = client.get("/games")
    assert game_list.status_code == 200
    game_ids = {item["id"] for item in game_list.json()}
    assert str(visible_game_id) in game_ids
    assert str(hidden_game_id) not in game_ids
    browse = client.get("/games/browse", params={"starts_on": visible_game_starts_on})
    assert browse.status_code == 200
    browse_ids = {item["id"] for item in browse.json()["games"]}
    assert str(visible_game_id) in browse_ids
    assert str(hidden_game_id) not in browse_ids

    game_images = client.get("/game-images")
    assert game_images.status_code == 200
    game_image_ids = {item["id"] for item in game_images.json()}
    assert str(active_game_image_id) in game_image_ids
    assert str(hidden_game_image_id) not in game_image_ids
    assert client.get(f"/game-images/{active_game_image_id}").status_code == 200
    assert client.get(f"/game-images/{hidden_game_image_id}").status_code == 404
    assert client.get("/game-images", params={"image_status": "hidden"}).status_code == 403

    venue_images = client.get("/venue-images")
    assert venue_images.status_code == 200
    venue_image_ids = {item["id"] for item in venue_images.json()}
    assert str(active_venue_image_id) in venue_image_ids
    assert str(hidden_venue_image_id) not in venue_image_ids

    posts = client.get("/need-a-sub/posts")
    assert posts.status_code == 200
    post_ids = {item["id"] for item in posts.json()}
    assert str(visible_post_id) in post_ids
    assert str(hidden_post_id) not in post_ids
    assert str(removed_post_id) not in post_ids
    assert client.get(f"/need-a-sub/posts/{visible_post_id}").status_code == 200
    assert client.get(f"/need-a-sub/posts/{hidden_post_id}").status_code == 404
    assert client.get(f"/need-a-sub/posts/{removed_post_id}").status_code == 404


@pytest.mark.requirement("WS03-04C-R3", "WS03-04C-R6", "WS03-04C-R10")
def test_hidden_game_and_community_detail_are_publicly_concealed_but_private_for_host(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _session() as db:
        host = _user("hidden-host")
        other = _user("hidden-other")
        venue = _venue(host.id, "hidden")
        hidden_game = _game(
            host_user_id=host.id,
            venue_id=venue.id,
            label="hidden-private",
            public_visibility_status="hidden",
        )
        hidden_detail = _community_detail(
            game_id=hidden_game.id,
            payment_text_moderation_status="hidden",
        )
        hidden_detail.payment_methods_snapshot = [
            {"type": "cash", "value": "synthetic instructions"}
        ]
        db.add_all([host, other])
        db.flush()
        db.add(venue)
        db.flush()
        db.add(hidden_game)
        db.flush()
        db.add(hidden_detail)
        db.commit()
        host_auth_id = host.auth_user_id
        host_email = host.email
        other_auth_id = other.auth_user_id
        other_email = other.email
        hidden_game_id = hidden_game.id
        hidden_detail_id = hidden_detail.id

    _install_auth_identities(
        monkeypatch,
        {
            "host-token": _Identity(
                auth_user_id=host_auth_id,
                email=host_email,
                email_verified=True,
                authenticated_at=_recent_time(),
            ),
            "other-token": _Identity(
                auth_user_id=other_auth_id,
                email=other_email,
                email_verified=True,
                authenticated_at=_recent_time(),
            ),
        },
    )

    assert client.get(f"/games/{hidden_game_id}").status_code == 404
    assert (
        client.get(f"/games/{hidden_game_id}", headers=_auth_headers("other-token")).status_code
        == 404
    )
    host_game = client.get(f"/games/{hidden_game_id}", headers=_auth_headers("host-token"))
    assert host_game.status_code == 200
    assert host_game.headers["cache-control"] == "private, no-store"
    assert host_game.json()["id"] == str(hidden_game_id)

    assert client.get(f"/community-game-details/{hidden_detail_id}").status_code == 404
    host_detail = client.get(
        f"/community-game-details/{hidden_detail_id}",
        headers=_auth_headers("host-token"),
    )
    assert host_detail.status_code == 200
    assert host_detail.headers["cache-control"] == "private, no-store"
    host_detail_json = host_detail.json()
    assert host_detail_json["id"] == str(hidden_detail_id)
    assert host_detail_json["payment_methods_snapshot"] == []
    assert host_detail_json["payment_instructions_snapshot"] is None

    host_detail_list = client.get(
        "/community-game-details",
        params={"game_id": str(hidden_game_id)},
        headers=_auth_headers("host-token"),
    )
    assert host_detail_list.status_code == 200
    assert host_detail_list.headers["cache-control"] == "private, no-store"
    assert [item["id"] for item in host_detail_list.json()] == [str(hidden_detail_id)]
