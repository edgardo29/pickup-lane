from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from backend.services.game_service import load_game_card_metadata
from backend.services.official_game_query_service import (
    load_official_game_list_card_data,
)

pytestmark = [
    pytest.mark.no_db_cleanup,
    pytest.mark.pass_provenance("WS06-02"),
]


def _result(rows: list[tuple[object, ...]]) -> Mock:
    result = Mock()
    result.all.return_value = rows
    return result


def test_browse_card_projection_keeps_persisted_target_and_publication_key() -> None:
    game_id = uuid.uuid4()
    venue_id = uuid.uuid4()
    object_key = f"venues/{venue_id}/published/image/attempt.jpg"
    db = Mock()
    db.execute.side_effect = [
        _result([]),
        _result([]),
        _result(
            [(venue_id, "r2", "persisted-account", "persisted-bucket", object_key)]
        ),
    ]

    _participants, _game_images, venue_images = load_game_card_metadata(
        db,
        [SimpleNamespace(id=game_id, venue_id=venue_id)],
    )

    reference = venue_images[venue_id]
    assert reference.object_key == object_key
    assert reference.target.provider == "r2"
    assert reference.target.account_id == "persisted-account"
    assert reference.target.bucket_name == "persisted-bucket"


def test_official_game_projection_keeps_persisted_target_and_publication_key() -> None:
    game_id = uuid.uuid4()
    venue_id = uuid.uuid4()
    object_key = f"venues/{venue_id}/published/image/attempt.webp"
    db = Mock()
    db.execute.side_effect = [
        _result([]),
        _result(
            [(venue_id, "r2", "persisted-account", "persisted-bucket", object_key)]
        ),
    ]

    _booked_spots, venue_images = load_official_game_list_card_data(
        db,
        [SimpleNamespace(id=game_id, venue_id=venue_id)],
    )

    reference = venue_images[venue_id]
    assert reference.object_key == object_key
    assert reference.target.provider == "r2"
    assert reference.target.account_id == "persisted-account"
    assert reference.target.bucket_name == "persisted-bucket"
