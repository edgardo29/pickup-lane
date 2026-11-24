"""Browse uses published game and venue images without calling real storage."""

import uuid
from datetime import timedelta

import pytest

from backend.models import GameImage, VenueImage


@pytest.mark.page("F15", 12)
def test_card_includes_its_primary_game_image(clock, db, browse_game, browse):
    game = browse_game(starts_at=clock.now + timedelta(hours=6))
    db.add(
        GameImage(
            id=uuid.uuid4(),
            game_id=game.id,
            image_url="https://images.example.test/game.jpg",
            image_role="card",
            image_status="active",
            is_primary=True,
            sort_order=0,
        )
    )
    db.commit()
    assert (
        browse()["games"][0]["primary_image_url"]
        == "https://images.example.test/game.jpg"
    )


@pytest.mark.page("F15", 12)
def test_card_uses_published_venue_image_when_game_image_is_absent(
    clock, db, browse_game, browse, monkeypatch
):
    game = browse_game(starts_at=clock.now + timedelta(hours=6))
    db.add(
        VenueImage(
            id=uuid.uuid4(),
            venue_id=game.venue_id,
            storage_provider="r2",
            storage_object_key="private/source.jpg",
            storage_bucket="synthetic-public-bucket",
            storage_account_id="synthetic-account",
            content_type="image/jpeg",
            size_bytes=10,
            publication_object_key="venues/published.jpg",
            publication_content_type="image/jpeg",
            publication_size_bytes=10,
            publication_etag="synthetic-etag",
            upload_completed_at=clock.now,
            image_role="card",
            image_status="active",
            is_primary=True,
            sort_order=0,
        )
    )
    db.commit()
    calls = []

    def read_url(*, target, object_key):
        calls.append((target.bucket_name, object_key))
        return "https://images.example.test/venue.jpg"

    monkeypatch.setattr(
        "backend.services.game_service.create_object_read_url", read_url
    )
    assert (
        browse()["games"][0]["primary_image_url"]
        == "https://images.example.test/venue.jpg"
    )
    assert calls == [("synthetic-public-bucket", "venues/published.jpg")]


@pytest.mark.page("F15", 12)
@pytest.mark.parametrize("game_type", ["official", "community"])
def test_card_without_media_has_no_image_url(clock, browse_game, browse, game_type):
    browse_game(starts_at=clock.now + timedelta(hours=6), game_type=game_type)
    assert browse()["games"][0]["primary_image_url"] is None
