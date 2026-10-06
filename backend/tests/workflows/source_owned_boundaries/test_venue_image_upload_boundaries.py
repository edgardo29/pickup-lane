from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from backend.models import User, Venue, VenueImage
from backend.schemas.venue_image_schema import VenueImageUploadCreate
from backend.services.r2_storage_service import R2ObjectUploadTicket, R2StorageConfig


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _install_storage(monkeypatch: pytest.MonkeyPatch):
    from backend.services import venue_image_service

    upload_calls: list[str] = []
    config = R2StorageConfig(
        account_id="boundary-account",
        access_key_id="access",
        secret_access_key="secret",
        endpoint_url="https://boundary-account.r2.cloudflarestorage.com",
        bucket_name="boundary-bucket",
        upload_url_minutes=15,
        read_url_minutes=60,
        max_image_bytes=2048,
        allowed_image_types=frozenset({"image/jpeg", "image/png", "image/webp"}),
        object_connect_timeout_seconds=2,
        object_read_timeout_seconds=6,
    )

    def create_upload(*, target, object_key: str, content_type: str, config=None):
        upload_calls.append(object_key)
        return R2ObjectUploadTicket(
            upload_url="https://upload.example.invalid",
            upload_headers={"Content-Type": content_type},
            object_url="https://private.example.invalid",
            expires_at=datetime(2035, 1, 1, tzinfo=timezone.utc),
        )

    monkeypatch.setattr(venue_image_service, "get_r2_storage_config", lambda: config)
    monkeypatch.setattr(venue_image_service, "create_object_upload_url", create_upload)
    return upload_calls


def _entities() -> tuple[User, Venue]:
    user = User(
        id=uuid.uuid4(),
        auth_user_id=f"boundary-{uuid.uuid4()}",
        role="admin",
        email=f"boundary-{uuid.uuid4()}@example.invalid",
        first_name="Boundary",
        last_name="Admin",
        account_status="active",
        hosting_status="eligible",
    )
    venue = Venue(
        id=uuid.uuid4(),
        name="Boundary Field",
        address_line_1="1 Boundary Way",
        city="Austin",
        state="TX",
        postal_code="78701",
        country_code="US",
        venue_status="approved",
        is_active=True,
    )
    return user, venue


def _request(index: int, *, content_type: str = "image/jpeg", size: int = 100):
    return VenueImageUploadCreate(
        file_name=f"image-{index}.jpg",
        content_type=content_type,
        size_bytes=size,
        image_role="gallery",
        sort_order=min(index, 2),
    )


@pytest.mark.pass_provenance("WS06-02")
def test_three_selected_staging_intents_are_accepted_and_fourth_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services.venue_image_service import create_venue_image_upload

    upload_calls = _install_storage(monkeypatch)
    admin, venue = _entities()
    with _session() as db:
        db.add_all([admin, venue])
        db.commit()
        responses = [
            create_venue_image_upload(
                db,
                venue_id=venue.id,
                upload_request=_request(index),
                current_admin=admin,
            )
            for index in range(3)
        ]
        with pytest.raises(HTTPException) as exc_info:
            create_venue_image_upload(
                db,
                venue_id=venue.id,
                upload_request=_request(3),
                current_admin=admin,
            )

    assert exc_info.value.status_code == 400
    assert len(upload_calls) == 3
    assert all(response.image.image_url is None for response in responses)
    assert all("/staging/" in response.image.storage_object_key for response in responses)


@pytest.mark.pass_provenance("WS06-02")
@pytest.mark.parametrize(
    ("content_type", "size"),
    [("image/gif", 100), ("image/jpeg", 2049)],
)
def test_declared_policy_rejection_precedes_upload_capability(
    monkeypatch: pytest.MonkeyPatch,
    content_type: str,
    size: int,
) -> None:
    from backend.services.venue_image_service import create_venue_image_upload

    upload_calls = _install_storage(monkeypatch)
    admin, venue = _entities()
    with _session() as db:
        db.add_all([admin, venue])
        db.commit()
        with pytest.raises(HTTPException) as exc_info:
            create_venue_image_upload(
                db,
                venue_id=venue.id,
                upload_request=_request(0, content_type=content_type, size=size),
                current_admin=admin,
            )
        assert db.query(VenueImage).count() == 0

    assert exc_info.value.status_code == 400
    assert upload_calls == []
