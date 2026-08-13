from __future__ import annotations

import inspect
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.schemas.venue_image_schema import VenueImageUploadCreate

pytestmark = pytest.mark.suite_type("ordinary")


@dataclass
class _R2Fake:
    upload_calls: list[tuple[str, str]]
    read_calls: list[str]
    properties: dict[str, object]


def _admin() -> User:
    from backend.models import User

    return User(
        id=uuid.uuid4(),
        auth_user_id=f"ws02-04b1-venue-admin-{uuid.uuid4()}",
        role="admin",
        email=f"ws02-04b1-venue-admin-{uuid.uuid4()}@example.invalid",
        first_name="Venue",
        last_name="Admin",
        account_status="active",
        hosting_status="eligible",
    )


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _venue() -> Venue:
    from backend.models import Venue

    return Venue(
        id=uuid.uuid4(),
        name="Boundary Gym",
        address_line_1="1 Image Way",
        city="Austin",
        state="TX",
        postal_code="78701",
        country_code="US",
        venue_status="approved",
        is_active=True,
    )


def _upload_request(index: int, *, content_type: str = "image/jpeg", size_bytes: int = 1024) -> VenueImageUploadCreate:
    return VenueImageUploadCreate(
        file_name=f"venue-{index}.jpg",
        content_type=content_type,
        size_bytes=size_bytes,
        image_role="gallery",
        is_primary=False,
        sort_order=min(index, 2),
    )


def _count(db: Session, model: type[object]) -> int:
    return int(db.scalar(select(func.count()).select_from(model)) or 0)


def _install_r2_fake(monkeypatch: pytest.MonkeyPatch, *, max_image_bytes: int = 2048) -> _R2Fake:
    from backend.services import venue_image_service
    from backend.services.r2_storage_service import R2ObjectProperties, R2ObjectUploadTicket, R2StorageConfig

    fake = _R2Fake(upload_calls=[], read_calls=[], properties={})
    config = R2StorageConfig(
        account_id="synthetic-account",
        access_key_id="synthetic-access-key",
        secret_access_key="synthetic-secret-key",
        endpoint_url="https://r2.example.invalid",
        bucket_name="synthetic-bucket",
        upload_url_minutes=15,
        read_url_minutes=15,
        max_image_bytes=max_image_bytes,
        allowed_image_types=frozenset({"image/jpeg", "image/png", "image/webp"}),
        metadata_connect_timeout_seconds=2,
        metadata_read_timeout_seconds=2,
    )

    def get_r2_storage_config() -> R2StorageConfig:
        return config

    def create_object_upload_url(*, object_key: str, content_type: str) -> R2ObjectUploadTicket:
        fake.upload_calls.append((object_key, content_type))
        fake.properties.setdefault(
            object_key,
            R2ObjectProperties(content_type=content_type, size_bytes=1024, etag="etag"),
        )
        return R2ObjectUploadTicket(
            upload_url="https://r2.example.invalid/upload",
            upload_headers={"Content-Type": content_type},
            object_url=f"https://r2.example.invalid/{object_key}",
            expires_at=datetime(2035, 1, 1, tzinfo=timezone.utc),
        )

    def create_object_read_url(object_key: str) -> str:
        fake.read_calls.append(object_key)
        return f"https://r2.example.invalid/read/{object_key}"

    def get_object_properties(object_key: str) -> R2ObjectProperties:
        return fake.properties[object_key]

    monkeypatch.setattr(venue_image_service, "get_r2_storage_config", get_r2_storage_config)
    monkeypatch.setattr(venue_image_service, "create_object_upload_url", create_object_upload_url)
    monkeypatch.setattr(venue_image_service, "create_object_read_url", create_object_read_url)
    monkeypatch.setattr(venue_image_service, "get_object_properties", get_object_properties)
    return fake


@pytest.mark.requirement("WS02-04B1-R8")
def test_three_selected_venue_images_are_accepted_and_fourth_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import VenueImage
    from backend.services.venue_image_service import create_venue_image_upload

    fake = _install_r2_fake(monkeypatch)
    with _session() as db:
        admin = _admin()
        venue = _venue()
        db.add(admin)
        db.add(venue)
        db.commit()

        accepted = [
            create_venue_image_upload(
                db,
                venue_id=venue.id,
                upload_request=_upload_request(index),
                current_admin=admin,
            )
            for index in range(3)
        ]

        with pytest.raises(HTTPException) as exc_info:
            create_venue_image_upload(
                db,
                venue_id=venue.id,
                upload_request=_upload_request(4),
                current_admin=admin,
            )
        db.rollback()

        assert [item.image.image_status for item in accepted] == ["pending_upload"] * 3
        assert exc_info.value.status_code == 400
        assert _count(db, VenueImage) == 3
        assert len(fake.upload_calls) == 3


@pytest.mark.requirement("WS02-04B1-R8")
@pytest.mark.parametrize(
    "upload_request",
    [
        _upload_request(1, content_type="application/pdf"),
        _upload_request(2, size_bytes=2049),
    ],
)
def test_declared_size_and_type_checks_happen_before_upload_authorization(
    monkeypatch: pytest.MonkeyPatch,
    upload_request: VenueImageUploadCreate,
) -> None:
    from backend.models import VenueImage
    from backend.services.venue_image_service import create_venue_image_upload

    fake = _install_r2_fake(monkeypatch, max_image_bytes=2048)
    with _session() as db:
        admin = _admin()
        venue = _venue()
        db.add(admin)
        db.add(venue)
        db.commit()

        with pytest.raises(HTTPException) as exc_info:
            create_venue_image_upload(
                db,
                venue_id=venue.id,
                upload_request=upload_request,
                current_admin=admin,
            )

        assert exc_info.value.status_code == 400
        assert fake.upload_calls == []
        assert _count(db, VenueImage) == 0


@pytest.mark.requirement("WS02-04B1-R8")
def test_stored_metadata_mismatches_reject_completion_without_activating_image(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import VenueImage
    from backend.services.r2_storage_service import R2ObjectProperties
    from backend.services.venue_image_service import complete_venue_image_upload, create_venue_image_upload

    fake = _install_r2_fake(monkeypatch)
    with _session() as db:
        admin = _admin()
        venue = _venue()
        db.add(admin)
        db.add(venue)
        db.commit()

        size_mismatch = create_venue_image_upload(
            db,
            venue_id=venue.id,
            upload_request=_upload_request(1, size_bytes=1024),
            current_admin=admin,
        )
        fake.properties[size_mismatch.image.storage_object_key] = R2ObjectProperties(
            content_type="image/jpeg",
            size_bytes=1025,
            etag="etag-size",
        )
        with pytest.raises(HTTPException) as size_exc:
            complete_venue_image_upload(db, venue_image_id=size_mismatch.image.id, current_admin=admin)
        db.rollback()

        type_mismatch = create_venue_image_upload(
            db,
            venue_id=venue.id,
            upload_request=_upload_request(2, size_bytes=1024),
            current_admin=admin,
        )
        fake.properties[type_mismatch.image.storage_object_key] = R2ObjectProperties(
            content_type="image/png",
            size_bytes=1024,
            etag="etag-type",
        )
        with pytest.raises(HTTPException) as type_exc:
            complete_venue_image_upload(db, venue_image_id=type_mismatch.image.id, current_admin=admin)
        db.rollback()

        statuses = db.scalars(select(VenueImage.image_status).order_by(VenueImage.created_at.asc())).all()
        assert size_exc.value.status_code == 400
        assert type_exc.value.status_code == 400
        assert statuses == ["pending_upload", "pending_upload"]


@pytest.mark.requirement("WS02-04B1-R8")
def test_missing_provider_content_type_is_recorded_as_current_source_behavior_only() -> None:
    from backend.services import venue_image_service

    source = inspect.getsource(venue_image_service.complete_venue_image_upload)

    assert 'object_content_type = (object_properties.content_type or "").lower()' in source
    assert "if object_content_type and object_content_type != venue_image.content_type" in source
