from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.schemas.venue_image_schema import VenueImageUpdate, VenueImageUploadCreate

pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.suite_type("ordinary")]


def _upload(**overrides: object) -> VenueImageUploadCreate:
    payload = {
        "file_name": "field.jpg",
        "content_type": "image/jpeg",
        "size_bytes": 1024,
    }
    payload.update(overrides)
    return VenueImageUploadCreate(**payload)


def _assert_rejected(model_factory, **payload: object) -> None:
    with pytest.raises(ValidationError):
        model_factory(**payload)


@pytest.mark.requirement("WS02-04B2A2A-R5")
def test_venue_image_role_and_status_literals_are_bounded() -> None:
    assert _upload(image_role="card").image_role == "card"
    assert _upload(image_role="gallery").image_role == "gallery"
    _assert_rejected(_upload, image_role="hero")

    for status in ("pending_upload", "active", "hidden", "removed"):
        assert VenueImageUpdate(image_status=status).image_status == status
    _assert_rejected(VenueImageUpdate, image_status="published")


@pytest.mark.requirement("WS02-04B2A2A-R5")
def test_venue_image_sort_order_bounds_cover_upload_and_update() -> None:
    assert _upload().sort_order == 0
    for factory in (_upload, VenueImageUpdate):
        assert factory(sort_order=0).sort_order == 0
        assert factory(sort_order=2).sort_order == 2
        _assert_rejected(factory, sort_order=-1)
        _assert_rejected(factory, sort_order=3)


@pytest.mark.requirement("WS02-04B2A2A-R5")
def test_venue_image_request_models_reject_neutral_unknown_fields() -> None:
    _assert_rejected(_upload, unsupported_a2a_probe="value")
    _assert_rejected(VenueImageUpdate, unsupported_a2a_probe="value")
