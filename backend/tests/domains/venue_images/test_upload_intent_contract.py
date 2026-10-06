from __future__ import annotations

import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from io import BytesIO
from threading import Barrier, BoundedSemaphore, Event, Lock, Thread, current_thread

import pytest
from botocore.exceptions import ClientError
from fastapi import HTTPException
from PIL import Image
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.models import AdminAction, User, Venue, VenueImage
from backend.observability.metrics import MetricsRecorder, metrics_context
from backend.schemas.venue_image_schema import VenueImageUpdate, VenueImageUploadCreate
from backend.services.r2_storage_service import (
    R2DownloadedObject,
    R2MutationOutcomeUnknownError,
    R2ObjectUploadTicket,
    R2PublicationCollisionError,
    R2PublishedObject,
    R2StorageConfig,
    R2StorageError,
)
from backend.services.venue_image_processing import (
    ImageContentRejectedError,
    ImageProcessorNotReadyError,
    SanitizedVenueImage,
    sanitize_venue_image,
)

pytestmark = pytest.mark.pass_provenance("WS06-01", "WS06-02")


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _jpeg_bytes() -> bytes:
    output = BytesIO()
    with Image.new("RGB", (8, 6), "navy") as image:
        image.save(output, format="JPEG")
    return output.getvalue()


def _png_bytes(*, size: tuple[int, int] = (8, 6), optimize: bool = False) -> bytes:
    output = BytesIO()
    with Image.new("RGB", size, "navy") as image:
        image.save(output, format="PNG", compress_level=9, optimize=optimize)
    return output.getvalue()


def _animated_png_bytes(*, size: tuple[int, int] = (12, 12)) -> bytes:
    output = BytesIO()
    with (
        Image.new("RGB", size, "navy") as first,
        Image.new("RGB", size, "gold") as second,
    ):
        first.save(
            output,
            format="PNG",
            save_all=True,
            append_images=[second],
            duration=100,
            loop=0,
        )
    return output.getvalue()


def _animated_png_with_corrupt_first_frame() -> bytes:
    source = bytearray(_animated_png_bytes())
    chunk_type_index = source.index(b"IDAT")
    data_length = int.from_bytes(source[chunk_type_index - 4 : chunk_type_index], "big")
    crc_index = chunk_type_index + len(b"IDAT") + data_length
    source[crc_index] ^= 1
    return bytes(source)


def _animated_png_with_corrupt_later_frame() -> bytes:
    source = bytearray(_animated_png_bytes())
    later_frame_data = source.index(b"fdAT") + len(b"fdAT")
    source[later_frame_data] ^= 1
    return bytes(source)


@dataclass
class _StorageFake:
    source: bytes = field(default_factory=_jpeg_bytes)
    uploads: list[tuple[object, str]] = field(default_factory=list)
    reads: list[tuple[object, str]] = field(default_factory=list)
    downloads: list[tuple[object, str]] = field(default_factory=list)
    publications: list[tuple[object, str, bytes, str]] = field(default_factory=list)
    deletes: list[tuple[object, str]] = field(default_factory=list)
    publication_error: BaseException | None = None


class _CommitInterrupt(BaseException):
    pass


class _SessionCleanupInterrupt(BaseException):
    pass


def _config() -> R2StorageConfig:
    return R2StorageConfig(
        account_id="synthetic-account",
        access_key_id="synthetic-access",
        secret_access_key="synthetic-secret",
        endpoint_url="https://synthetic-account.r2.cloudflarestorage.com",
        bucket_name="synthetic-bucket",
        upload_url_minutes=15,
        read_url_minutes=60,
        max_image_bytes=1_000_000,
        allowed_image_types=frozenset({"image/jpeg"}),
        object_connect_timeout_seconds=2,
        object_read_timeout_seconds=6,
    )


def _install_storage_fake(monkeypatch: pytest.MonkeyPatch) -> _StorageFake:
    from backend.services import venue_image_service

    fake = _StorageFake()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

    def create_upload(*, target, object_key: str, content_type: str, config=None):
        fake.uploads.append((target, object_key))
        return R2ObjectUploadTicket(
            upload_url="https://upload.example.invalid/signed",
            upload_headers={"Content-Type": content_type},
            object_url="https://object.example.invalid/private",
            expires_at=expires_at,
        )

    def create_read(*, target, object_key: str, config=None):
        fake.reads.append((target, object_key))
        return "https://read.example.invalid/signed"

    def download(*, target, object_key: str, **kwargs):
        fake.downloads.append((target, object_key))
        return R2DownloadedObject(
            body=fake.source,
            content_type="image/jpeg",
            size_bytes=len(fake.source),
            etag='"staging"',
        )

    def publish(
        *, target, object_key: str, body: bytes, content_type: str, config=None
    ):
        fake.publications.append((target, object_key, body, content_type))
        if fake.publication_error is not None:
            raise fake.publication_error
        return R2PublishedObject(etag='"published"')

    def delete(*, target, object_key: str, config=None):
        fake.deletes.append((target, object_key))

    monkeypatch.setattr(venue_image_service, "get_r2_storage_config", _config)
    monkeypatch.setattr(venue_image_service, "create_object_upload_url", create_upload)
    monkeypatch.setattr(venue_image_service, "create_object_read_url", create_read)
    monkeypatch.setattr(venue_image_service, "download_object", download)
    monkeypatch.setattr(venue_image_service, "publish_object", publish)
    monkeypatch.setattr(venue_image_service, "delete_object", delete)
    return fake


def _setup() -> tuple[uuid.UUID, uuid.UUID]:
    admin = User(
        id=uuid.uuid4(),
        auth_user_id=f"image-admin-{uuid.uuid4()}",
        role="admin",
        email=f"image-admin-{uuid.uuid4()}@example.invalid",
        first_name="Image",
        last_name="Admin",
        account_status="active",
        hosting_status="eligible",
    )
    venue = Venue(
        id=uuid.uuid4(),
        name="Sanitized Image Field",
        address_line_1="1 Pixel Way",
        city="Austin",
        state="TX",
        postal_code="78701",
        country_code="US",
        venue_status="approved",
        is_active=True,
    )
    admin_id = admin.id
    venue_id = venue.id
    with _session() as db:
        db.add_all([admin, venue])
        db.commit()
    return admin_id, venue_id


def _request(
    *,
    size: int | None = None,
    file_name: str = "venue.jpg",
) -> VenueImageUploadCreate:
    return VenueImageUploadCreate(
        file_name=file_name,
        content_type="image/jpeg",
        size_bytes=size if size is not None else len(_jpeg_bytes()),
        image_role="gallery",
        sort_order=0,
    )


def _create_pending(
    monkeypatch: pytest.MonkeyPatch,
    *,
    file_name: str = "venue.jpg",
):
    from backend.services.venue_image_service import create_venue_image_upload

    fake = _install_storage_fake(monkeypatch)
    admin_id, venue_id = _setup()
    with _session() as db:
        response = create_venue_image_upload(
            db,
            venue_id=venue_id,
            upload_request=_request(size=len(fake.source), file_name=file_name),
            current_admin=db.get(User, admin_id),
        )
        image_id = response.image.id
    return fake, admin_id, venue_id, image_id, response


def _assert_processing_slot_is_released() -> None:
    from backend.services import venue_image_service

    assert venue_image_service._IMAGE_PROCESSING_SLOT.acquire(blocking=False)
    venue_image_service._IMAGE_PROCESSING_SLOT.release()


def test_initiation_creates_private_staging_intent_without_read_capability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake, _admin_id, venue_id, image_id, response = _create_pending(monkeypatch)

    assert response.image.image_url is None
    assert response.image.storage_object_key == (
        f"venues/{venue_id}/staging/{image_id}.jpg"
    )
    assert len(fake.uploads) == 1
    assert fake.reads == []
    with _session() as db:
        image = db.get(VenueImage, image_id)
        assert image.image_status == "pending_upload"
        assert image.publication_object_key is None
        assert image.upload_completed_at is None


def test_repeated_initiation_persists_exact_expiry_and_distinct_server_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services.venue_image_service import create_venue_image_upload

    fake = _install_storage_fake(monkeypatch)
    admin_id, venue_id = _setup()
    with _session() as db:
        admin = db.get(User, admin_id)
        first = create_venue_image_upload(
            db, venue_id=venue_id, upload_request=_request(), current_admin=admin
        )
        second = create_venue_image_upload(
            db, venue_id=venue_id, upload_request=_request(), current_admin=admin
        )

    assert first.image.id != second.image.id
    assert first.image.storage_object_key != second.image.storage_object_key
    assert first.expires_at == second.expires_at
    assert len(fake.uploads) == 2
    with _session() as db:
        stored = db.scalars(
            select(VenueImage).where(
                VenueImage.id.in_([first.image.id, second.image.id])
            )
        ).all()
        assert {image.upload_expires_at for image in stored} == {first.expires_at}
        assert {image.storage_account_id for image in stored} == {"synthetic-account"}
        assert {image.storage_bucket for image in stored} == {"synthetic-bucket"}


def test_invalid_venue_rejects_before_signing_or_persistence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services.venue_image_service import create_venue_image_upload

    fake = _install_storage_fake(monkeypatch)
    admin_id, _venue_id = _setup()
    missing_venue_id = uuid.uuid4()
    with _session() as db, pytest.raises(HTTPException) as exc_info:
        create_venue_image_upload(
            db,
            venue_id=missing_venue_id,
            upload_request=_request(),
            current_admin=db.get(User, admin_id),
        )
    assert exc_info.value.status_code == 404
    assert fake.uploads == []
    with _session() as db:
        assert (
            db.scalars(
                select(VenueImage).where(VenueImage.venue_id == missing_venue_id)
            ).all()
            == []
        )


@pytest.mark.parametrize(
    ("expiry_offset", "allowed"),
    [
        (timedelta(microseconds=1), True),
        (timedelta(0), False),
        (timedelta(seconds=-1), False),
    ],
)
def test_completion_enforces_expiry_before_equal_and_after_boundary(
    monkeypatch: pytest.MonkeyPatch,
    expiry_offset: timedelta,
    allowed: bool,
) -> None:
    from backend.services import venue_image_service

    fake, admin_id, _venue_id, image_id, _response = _create_pending(monkeypatch)
    boundary = datetime(2030, 1, 1, tzinfo=timezone.utc)
    with _session() as db:
        image = db.get(VenueImage, image_id)
        image.upload_expires_at = boundary + expiry_offset
        db.commit()
    monkeypatch.setattr(venue_image_service, "utc_now", lambda: boundary)

    with _session() as db:
        if allowed:
            response = venue_image_service.complete_venue_image_upload(
                db,
                venue_image_id=image_id,
                current_admin=db.get(User, admin_id),
            )
            assert response.image_status == "active"
            assert len(fake.downloads) == 1
        else:
            with pytest.raises(HTTPException) as exc_info:
                venue_image_service.complete_venue_image_upload(
                    db,
                    venue_image_id=image_id,
                    current_admin=db.get(User, admin_id),
                )
            assert exc_info.value.status_code == 409
            assert exc_info.value.detail["code"] == "STORAGE.UPLOAD_NOT_PENDING"
            assert fake.downloads == []
    _assert_processing_slot_is_released()


def test_replayed_completion_rejects_before_another_storage_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services.venue_image_service import complete_venue_image_upload

    fake, admin_id, _venue_id, image_id, _response = _create_pending(monkeypatch)
    with _session() as db:
        complete_venue_image_upload(
            db, venue_image_id=image_id, current_admin=db.get(User, admin_id)
        )
    assert len(fake.downloads) == 1

    with _session() as db, pytest.raises(HTTPException) as exc_info:
        complete_venue_image_upload(
            db, venue_image_id=image_id, current_admin=db.get(User, admin_id)
        )
    assert exc_info.value.status_code == 409
    assert len(fake.downloads) == 1


@pytest.mark.parametrize(
    ("current_status", "requested_status", "allowed"),
    [
        ("pending_upload", "pending_upload", True),
        ("pending_upload", "removed", True),
        ("pending_upload", "active", False),
        ("pending_upload", "hidden", False),
        ("active", "active", True),
        ("active", "hidden", True),
        ("active", "removed", True),
        ("active", "pending_upload", False),
        ("hidden", "hidden", True),
        ("hidden", "active", True),
        ("hidden", "removed", True),
        ("hidden", "pending_upload", False),
        ("removed", "removed", False),
        ("removed", "active", False),
        ("removed", "hidden", False),
        ("removed", "pending_upload", False),
    ],
)
def test_status_transition_matrix_preserves_upload_lifecycle(
    current_status: str,
    requested_status: str,
    allowed: bool,
) -> None:
    from backend.services.venue_image_service import (
        validate_venue_image_status_transition,
    )

    if allowed:
        validate_venue_image_status_transition(
            current_status=current_status,
            requested_status=requested_status,
        )
    else:
        with pytest.raises(HTTPException):
            validate_venue_image_status_transition(
                current_status=current_status,
                requested_status=requested_status,
            )


def test_completion_publishes_sanitized_candidate_then_commits_and_cleans_staging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services.venue_image_service import complete_venue_image_upload

    fake, admin_id, venue_id, image_id, initiation = _create_pending(monkeypatch)
    staging_key = initiation.image.storage_object_key
    with _session() as db:
        response = complete_venue_image_upload(
            db,
            venue_image_id=image_id,
            current_admin=db.get(User, admin_id),
        )

    assert response.image_status == "active"
    assert response.image_url == "https://read.example.invalid/signed"
    assert response.storage_object_key.startswith(
        f"venues/{venue_id}/published/{image_id}/"
    )
    assert fake.downloads[0][1] == staging_key
    assert fake.publications[0][1] == response.storage_object_key
    assert fake.publications[0][3] == "image/jpeg"
    assert fake.reads[0][1] == response.storage_object_key
    assert fake.deletes == [(fake.downloads[0][0], staging_key)]

    with _session() as db:
        image = db.get(VenueImage, image_id)
        assert image.image_status == "active"
        assert image.publication_object_key == response.storage_object_key
        assert image.publication_etag == '"published"'
        assert image.publication_size_bytes == len(fake.publications[0][2])
        assert image.upload_completed_at is not None
        audits = db.scalars(
            select(AdminAction).where(
                AdminAction.target_venue_image_id == image_id,
                AdminAction.action_type == "update_venue_image",
            )
        ).all()
        assert len(audits) == 1
    _assert_processing_slot_is_released()


@pytest.mark.parametrize("file_name", ["misleading.png", "venue-image"])
def test_completion_ignores_misleading_or_absent_filename_extension(
    monkeypatch: pytest.MonkeyPatch,
    file_name: str,
) -> None:
    from backend.services.venue_image_service import complete_venue_image_upload

    fake, admin_id, _venue_id, image_id, _response = _create_pending(
        monkeypatch,
        file_name=file_name,
    )

    with _session() as db:
        completed = complete_venue_image_upload(
            db,
            venue_image_id=image_id,
            current_admin=db.get(User, admin_id),
        )

    assert completed.image_status == "active"
    assert completed.content_type == "image/jpeg"
    assert fake.publications[0][3] == "image/jpeg"
    assert fake.publications[0][1].endswith(".jpg")
    _assert_processing_slot_is_released()


def test_staging_recreation_after_activation_cannot_change_publication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import venue_image_service

    fake, admin_id, _venue_id, image_id, initiation = _create_pending(monkeypatch)
    staging_key = initiation.image.storage_object_key
    objects: dict[str, tuple[bytes, str, str]] = {
        staging_key: (fake.source, "image/jpeg", '"staging-original"')
    }

    def download(*, object_key: str, **kwargs) -> R2DownloadedObject:
        body, content_type, etag = objects[object_key]
        return R2DownloadedObject(
            body=body,
            content_type=content_type,
            size_bytes=len(body),
            etag=etag,
        )

    def publish(
        *, object_key: str, body: bytes, content_type: str, **kwargs
    ) -> R2PublishedObject:
        assert object_key not in objects
        etag = '"publication-etag"'
        objects[object_key] = (body, content_type, etag)
        return R2PublishedObject(etag=etag)

    def delete(*, object_key: str, **kwargs) -> None:
        objects.pop(object_key, None)

    def read_url(*, object_key: str, **kwargs) -> str:
        return f"https://read.example.invalid/{object_key}"

    monkeypatch.setattr(venue_image_service, "download_object", download)
    monkeypatch.setattr(venue_image_service, "publish_object", publish)
    monkeypatch.setattr(venue_image_service, "delete_object", delete)
    monkeypatch.setattr(venue_image_service, "create_object_read_url", read_url)

    with _session() as db:
        completed = venue_image_service.complete_venue_image_upload(
            db,
            venue_image_id=image_id,
            current_admin=db.get(User, admin_id),
        )

    publication_key = completed.storage_object_key
    publication_before = objects[publication_key]
    assert staging_key not in objects

    # An unexpired browser capability may recreate only the private staging key.
    objects[staging_key] = (
        b"later-unsafe-upload",
        "image/jpeg",
        '"staging-recreated"',
    )

    with _session() as db:
        stored = db.get(VenueImage, image_id)
        reread = venue_image_service.build_admin_venue_image_read(stored)
        persisted_metadata = (
            stored.publication_object_key,
            stored.publication_content_type,
            stored.publication_size_bytes,
            stored.publication_etag,
        )

    assert objects[publication_key] == publication_before
    assert reread.image_url == completed.image_url
    assert reread.storage_object_key == publication_key
    assert reread.size_bytes == len(publication_before[0])
    assert reread.etag == publication_before[2]
    assert persisted_metadata == (
        publication_key,
        publication_before[1],
        len(publication_before[0]),
        publication_before[2],
    )
    assert objects[staging_key][0] == b"later-unsafe-upload"
    _assert_processing_slot_is_released()


def test_unrecognized_image_is_rejected_and_staging_cleanup_is_attempted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services.venue_image_service import complete_venue_image_upload

    fake, admin_id, _venue_id, image_id, initiation = _create_pending(monkeypatch)
    fake.source = b"not-an-image"
    with _session() as db, pytest.raises(HTTPException) as exc_info:
        complete_venue_image_upload(
            db,
            venue_image_id=image_id,
            current_admin=db.get(User, admin_id),
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["code"] == "STORAGE.IMAGE_INVALID"
    assert exc_info.value.detail["outcome"] == "unsupported_content"
    assert fake.publications == []
    assert fake.deletes[0][1] == initiation.image.storage_object_key
    with _session() as db:
        assert db.get(VenueImage, image_id).image_status == "pending_upload"
    _assert_processing_slot_is_released()


@pytest.mark.parametrize(
    (
        "source",
        "declared_content_type",
        "expected_outcome",
        "max_bytes",
        "max_axis",
    ),
    [
        pytest.param(
            _png_bytes(),
            "image/jpeg",
            "type_mismatch",
            None,
            None,
            id="different-approved-signature",
        ),
        pytest.param(
            _animated_png_with_corrupt_first_frame(),
            "image/png",
            "corrupt_image",
            None,
            None,
            id="multi-frame-invalid-first-frame",
        ),
        pytest.param(
            _animated_png_bytes(),
            "image/png",
            "multi_frame",
            None,
            None,
            id="bounded-multi-frame",
        ),
        pytest.param(
            _animated_png_with_corrupt_later_frame(),
            "image/png",
            "multi_frame",
            None,
            None,
            id="multi-frame-corrupt-later-frame",
        ),
        pytest.param(
            _animated_png_bytes(),
            "image/png",
            "resource_limit",
            None,
            8,
            id="oversized-multi-frame",
        ),
        pytest.param(
            _png_bytes(size=(16, 16), optimize=True),
            "image/png",
            "encoded_size_limit",
            "source_length",
            None,
            id="reencoded-output-over-byte-limit",
        ),
    ],
)
def test_real_processor_rejections_keep_production_completion_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    source: bytes,
    declared_content_type: str,
    expected_outcome: str,
    max_bytes: int | str | None,
    max_axis: int | None,
) -> None:
    from backend.services import venue_image_service
    from backend.services.venue_image_processing import sanitize_venue_image

    fake, admin_id, _venue_id, image_id, initiation = _create_pending(monkeypatch)
    configured_max_bytes = len(source) if max_bytes == "source_length" else 1_000_000
    config = replace(
        _config(),
        max_image_bytes=configured_max_bytes,
        allowed_image_types=frozenset({"image/jpeg", "image/png"}),
    )
    monkeypatch.setattr(venue_image_service, "get_r2_storage_config", lambda: config)
    monkeypatch.setattr(
        venue_image_service,
        "download_object",
        lambda **kwargs: R2DownloadedObject(
            body=source,
            content_type=declared_content_type,
            size_bytes=len(source),
            etag='"staging"',
        ),
    )
    if max_axis is not None:
        monkeypatch.setattr(
            venue_image_service,
            "sanitize_venue_image",
            lambda body, **kwargs: sanitize_venue_image(
                body,
                **kwargs,
                max_axis=max_axis,
            ),
        )
    events: list[tuple[str, str, dict[str, object]]] = []
    monkeypatch.setattr(
        venue_image_service,
        "emit_event",
        lambda name, severity, fields: events.append((name, severity, fields)) or True,
    )
    with _session() as db:
        image = db.get(VenueImage, image_id)
        image.content_type = declared_content_type
        image.size_bytes = len(source)
        db.commit()

    with _session() as db, pytest.raises(HTTPException) as exc_info:
        venue_image_service.complete_venue_image_upload(
            db,
            venue_image_id=image_id,
            current_admin=db.get(User, admin_id),
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == {
        "code": "STORAGE.IMAGE_INVALID",
        "message": "Uploaded image content is invalid.",
        "outcome": expected_outcome,
    }
    assert fake.publications == []
    assert [key for _target, key in fake.deletes] == [
        initiation.image.storage_object_key
    ]
    assert events == [
        (
            "venue_image.validation_rejected",
            "warning",
            {
                "resource_kind": "venue_image",
                "result": expected_outcome,
            },
        )
    ]
    with _session() as db:
        image = db.get(VenueImage, image_id)
        assert image.image_status == "pending_upload"
        assert image.publication_object_key is None
        assert (
            db.scalars(
                select(AdminAction).where(
                    AdminAction.target_venue_image_id == image_id,
                    AdminAction.action_type == "update_venue_image",
                )
            ).all()
            == []
        )
    _assert_processing_slot_is_released()


def test_real_download_success_metric_is_preserved_for_processor_rejection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import r2_storage_service, venue_image_service

    source = b"not-an-approved-image"
    fake, admin_id, _venue_id, image_id, initiation = _create_pending(monkeypatch)
    config = replace(
        _config(),
        max_image_bytes=1_000_000,
        allowed_image_types=frozenset({"image/jpeg"}),
    )
    with _session() as db:
        image = db.get(VenueImage, image_id)
        image.size_bytes = len(source)
        db.commit()

    class Body(BytesIO):
        closed_by_adapter = False

        def close(self) -> None:
            self.closed_by_adapter = True
            super().close()

    body = Body(source)

    class Client:
        def get_object(self, **kwargs):
            return {
                "ResponseMetadata": {"HTTPStatusCode": 200},
                "Body": body,
                "ContentLength": len(source),
                "ContentType": "image/jpeg",
                "ETag": '"staging"',
            }

    monkeypatch.setattr(venue_image_service, "get_r2_storage_config", lambda: config)
    monkeypatch.setattr(
        venue_image_service,
        "download_object",
        r2_storage_service.download_object,
    )
    monkeypatch.setattr(r2_storage_service, "get_r2_client", lambda config: Client())
    events: list[tuple[str, str, dict[str, object]]] = []
    monkeypatch.setattr(
        venue_image_service,
        "emit_event",
        lambda name, severity, fields: events.append((name, severity, fields)) or True,
    )
    recorder = MetricsRecorder("api", "test", "venue-image-download-test")

    with (
        _session() as db,
        metrics_context(recorder),
        pytest.raises(HTTPException) as exc_info,
    ):
        venue_image_service.complete_venue_image_upload(
            db,
            venue_image_id=image_id,
            current_admin=db.get(User, admin_id),
        )

    assert exc_info.value.detail["outcome"] == "unsupported_content"
    assert body.closed_by_adapter is True
    provider_series = [
        series
        for series in recorder.snapshot().series
        if series.name == "provider.operation.outcome.total"
    ]
    assert len(provider_series) == 1
    assert dict(provider_series[0].dimensions) == {
        "operation": "r2.object.download",
        "provider_kind": "r2",
        "result": "succeeded",
    }
    assert events == [
        (
            "venue_image.validation_rejected",
            "warning",
            {"resource_kind": "venue_image", "result": "unsupported_content"},
        )
    ]
    assert fake.publications == []
    assert [key for _target, key in fake.deletes] == [
        initiation.image.storage_object_key
    ]
    _assert_processing_slot_is_released()


@pytest.mark.parametrize("content_type", ["", "   "])
def test_blank_download_content_type_is_a_production_metadata_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    content_type: str,
) -> None:
    from backend.services import r2_storage_service, venue_image_service

    source = _jpeg_bytes()
    fake, admin_id, _venue_id, image_id, initiation = _create_pending(monkeypatch)
    config = _config()

    class Body(BytesIO):
        closed_by_adapter = False

        def close(self) -> None:
            self.closed_by_adapter = True
            super().close()

    body = Body(source)

    class Client:
        def get_object(self, **kwargs):
            return {
                "ResponseMetadata": {"HTTPStatusCode": 200},
                "Body": body,
                "ContentLength": len(source),
                "ContentType": content_type,
                "ETag": '"staging"',
            }

    monkeypatch.setattr(venue_image_service, "get_r2_storage_config", lambda: config)
    monkeypatch.setattr(
        venue_image_service,
        "download_object",
        r2_storage_service.download_object,
    )
    monkeypatch.setattr(r2_storage_service, "get_r2_client", lambda config: Client())
    events: list[tuple[str, str, dict[str, object]]] = []
    monkeypatch.setattr(
        venue_image_service,
        "emit_event",
        lambda name, severity, fields: events.append((name, severity, fields)) or True,
    )
    recorder = MetricsRecorder("api", "test", "venue-image-download-test")

    with (
        _session() as db,
        metrics_context(recorder),
        pytest.raises(HTTPException) as exc_info,
    ):
        venue_image_service.complete_venue_image_upload(
            db,
            venue_image_id=image_id,
            current_admin=db.get(User, admin_id),
        )

    assert exc_info.value.detail == {
        "code": "STORAGE.UPLOAD_MISMATCH",
        "message": "Uploaded image metadata does not match the upload request.",
        "outcome": "metadata_mismatch",
    }
    assert body.closed_by_adapter is True
    provider_series = [
        series
        for series in recorder.snapshot().series
        if series.name == "provider.operation.outcome.total"
    ]
    assert len(provider_series) == 1
    assert dict(provider_series[0].dimensions) == {
        "operation": "r2.object.download",
        "provider_kind": "r2",
        "result": "failed",
    }
    assert events == [
        (
            "venue_image.validation_rejected",
            "warning",
            {"resource_kind": "venue_image", "result": "metadata_mismatch"},
        )
    ]
    assert fake.publications == []
    assert [key for _target, key in fake.deletes] == [
        initiation.image.storage_object_key
    ]
    _assert_processing_slot_is_released()


def test_absent_download_content_type_completes_through_the_production_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import r2_storage_service, venue_image_service

    source = _jpeg_bytes()
    fake, admin_id, _venue_id, image_id, initiation = _create_pending(monkeypatch)
    config = _config()

    class Body(BytesIO):
        closed_by_adapter = False

        def close(self) -> None:
            self.closed_by_adapter = True
            super().close()

    body = Body(source)

    class Client:
        def get_object(self, **kwargs):
            assert kwargs == {
                "Bucket": config.bucket_name,
                "Key": initiation.image.storage_object_key,
            }
            return {
                "ResponseMetadata": {"HTTPStatusCode": 200},
                "Body": body,
                "ContentLength": len(source),
                "ETag": '"staging"',
            }

    monkeypatch.setattr(venue_image_service, "get_r2_storage_config", lambda: config)
    monkeypatch.setattr(
        venue_image_service,
        "download_object",
        r2_storage_service.download_object,
    )
    monkeypatch.setattr(r2_storage_service, "get_r2_client", lambda config: Client())
    events: list[tuple[str, str, dict[str, object]]] = []
    monkeypatch.setattr(
        venue_image_service,
        "emit_event",
        lambda name, severity, fields: events.append((name, severity, fields)) or True,
    )
    recorder = MetricsRecorder("api", "test", "venue-image-download-test")

    with _session() as db, metrics_context(recorder):
        response = venue_image_service.complete_venue_image_upload(
            db,
            venue_image_id=image_id,
            current_admin=db.get(User, admin_id),
        )

    assert response.image_status == "active"
    assert response.content_type == "image/jpeg"
    assert response.storage_object_key == fake.publications[0][1]
    assert body.closed_by_adapter is True
    provider_series = [
        series
        for series in recorder.snapshot().series
        if series.name == "provider.operation.outcome.total"
    ]
    assert len(provider_series) == 1
    assert dict(provider_series[0].dimensions) == {
        "operation": "r2.object.download",
        "provider_kind": "r2",
        "result": "succeeded",
    }
    assert events == []
    assert [key for _target, key in fake.deletes] == [
        initiation.image.storage_object_key
    ]
    with _session() as db:
        image = db.get(VenueImage, image_id)
        assert image.image_status == "active"
        assert image.publication_object_key == response.storage_object_key
        assert image.publication_content_type == response.content_type
        assert image.publication_size_bytes == response.size_bytes
        assert image.publication_etag == response.etag
        audits = db.scalars(
            select(AdminAction).where(
                AdminAction.target_venue_image_id == image_id,
                AdminAction.action_type == "update_venue_image",
            )
        ).all()
        assert len(audits) == 1
    _assert_processing_slot_is_released()


@pytest.mark.parametrize(
    "category",
    [
        "type_mismatch",
        "corrupt_image",
        "multi_frame",
        "resource_limit",
        "encoded_size_limit",
    ],
)
def test_every_processor_rejection_preserves_pending_state_and_reports_exact_outcome(
    monkeypatch: pytest.MonkeyPatch,
    category: str,
) -> None:
    from backend.services import venue_image_service

    fake, admin_id, _venue_id, image_id, initiation = _create_pending(monkeypatch)
    events: list[tuple[str, str, dict[str, object]]] = []
    monkeypatch.setattr(
        venue_image_service,
        "sanitize_venue_image",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            ImageContentRejectedError(category, "synthetic safe rejection")
        ),
    )
    monkeypatch.setattr(
        venue_image_service,
        "emit_event",
        lambda name, severity, fields: events.append((name, severity, fields)) or True,
    )

    with _session() as db, pytest.raises(HTTPException) as exc_info:
        venue_image_service.complete_venue_image_upload(
            db,
            venue_image_id=image_id,
            current_admin=db.get(User, admin_id),
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == {
        "code": "STORAGE.IMAGE_INVALID",
        "message": "Uploaded image content is invalid.",
        "outcome": category,
    }
    assert fake.publications == []
    assert [key for _target, key in fake.deletes] == [
        initiation.image.storage_object_key
    ]
    assert events == [
        (
            "venue_image.validation_rejected",
            "warning",
            {
                "resource_kind": "venue_image",
                "result": category,
            },
        )
    ]
    with _session() as db:
        image = db.get(VenueImage, image_id)
        assert image.image_status == "pending_upload"
        assert image.publication_object_key is None
        assert (
            db.scalars(
                select(AdminAction).where(
                    AdminAction.target_venue_image_id == image_id,
                    AdminAction.action_type == "update_venue_image",
                )
            ).all()
            == []
        )
    _assert_processing_slot_is_released()


def test_validation_cleanup_cancellation_is_not_swallowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import venue_image_service

    fake, admin_id, _venue_id, image_id, initiation = _create_pending(monkeypatch)
    fake.source = b"not-an-image"
    cancellation = asyncio.CancelledError()
    cleanup_attempts: list[str] = []

    def cancel_delete(*, object_key: str, **kwargs) -> None:
        cleanup_attempts.append(object_key)
        raise cancellation

    monkeypatch.setattr(venue_image_service, "delete_object", cancel_delete)
    events: list[tuple[str, str, dict[str, object]]] = []
    monkeypatch.setattr(
        venue_image_service,
        "emit_event",
        lambda name, severity, fields: events.append((name, severity, fields)) or True,
    )

    with _session() as db, pytest.raises(asyncio.CancelledError) as exc_info:
        venue_image_service.complete_venue_image_upload(
            db,
            venue_image_id=image_id,
            current_admin=db.get(User, admin_id),
        )

    assert exc_info.value is cancellation
    assert cleanup_attempts == [initiation.image.storage_object_key]
    assert events == [
        (
            "venue_image.validation_rejected",
            "warning",
            {"resource_kind": "venue_image", "result": "unsupported_content"},
        ),
        (
            "venue_image.cleanup_incomplete",
            "warning",
            {"resource_kind": "staging", "result": "unknown_outcome"},
        ),
    ]
    assert fake.publications == []
    with _session() as db:
        image = db.get(VenueImage, image_id)
        assert image.image_status == "pending_upload"
        assert image.publication_object_key is None
        assert (
            db.scalars(
                select(AdminAction).where(
                    AdminAction.target_venue_image_id == image_id,
                    AdminAction.action_type == "update_venue_image",
                )
            ).all()
            == []
        )
    _assert_processing_slot_is_released()


def test_publication_collision_preserves_staging_and_pending_row(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services.venue_image_service import complete_venue_image_upload

    fake, admin_id, _venue_id, image_id, _response = _create_pending(monkeypatch)
    fake.publication_error = R2PublicationCollisionError("synthetic collision")
    with _session() as db, pytest.raises(HTTPException) as exc_info:
        complete_venue_image_upload(
            db,
            venue_image_id=image_id,
            current_admin=db.get(User, admin_id),
        )
    assert exc_info.value.status_code == 502
    assert exc_info.value.detail["code"] == "STORAGE.PUBLICATION_FAILED"
    assert fake.deletes == []
    with _session() as db:
        image = db.get(VenueImage, image_id)
        assert image.image_status == "pending_upload"
        assert image.publication_object_key is None
    _assert_processing_slot_is_released()


def test_publication_unknown_preserves_candidate_and_staging_without_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services.venue_image_service import complete_venue_image_upload

    fake, admin_id, _venue_id, image_id, _response = _create_pending(monkeypatch)
    fake.publication_error = R2MutationOutcomeUnknownError("synthetic uncertainty")
    with _session() as db, pytest.raises(HTTPException) as exc_info:
        complete_venue_image_upload(
            db,
            venue_image_id=image_id,
            current_admin=db.get(User, admin_id),
        )
    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["code"] == "STORAGE.MUTATION_OUTCOME_UNKNOWN"
    assert fake.deletes == []
    with _session() as db:
        assert db.get(VenueImage, image_id).image_status == "pending_upload"
    _assert_processing_slot_is_released()


def test_ambiguous_409_precondition_response_is_unknown_through_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import r2_storage_service, venue_image_service

    fake, admin_id, _venue_id, image_id, _response = _create_pending(monkeypatch)

    class Client:
        def put_object(self, **kwargs):
            raise ClientError(
                {
                    "Error": {
                        "Code": "PreconditionFailed",
                        "Message": "synthetic contradiction",
                    },
                    "ResponseMetadata": {"HTTPStatusCode": 409},
                },
                "PutObject",
            )

    monkeypatch.setattr(
        r2_storage_service,
        "get_r2_client",
        lambda config, *, disable_retries=False: Client(),
    )
    monkeypatch.setattr(
        venue_image_service,
        "publish_object",
        r2_storage_service.publish_object,
    )

    with _session() as db, pytest.raises(HTTPException) as exc_info:
        venue_image_service.complete_venue_image_upload(
            db,
            venue_image_id=image_id,
            current_admin=db.get(User, admin_id),
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == {
        "code": "STORAGE.MUTATION_OUTCOME_UNKNOWN",
        "message": (
            "Storage mutation outcome is unknown. Check current state before retrying."
        ),
        "outcome": "unknown",
    }
    assert fake.deletes == []
    with _session() as db:
        image = db.get(VenueImage, image_id)
        assert image.image_status == "pending_upload"
        assert image.publication_object_key is None
    _assert_processing_slot_is_released()


def test_processing_slot_rejects_without_provider_or_database_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import venue_image_service

    fake, admin_id, _venue_id, image_id, _response = _create_pending(monkeypatch)
    assert venue_image_service._IMAGE_PROCESSING_SLOT.acquire(blocking=False)
    try:
        with _session() as db, pytest.raises(HTTPException) as exc_info:
            venue_image_service.complete_venue_image_upload(
                db,
                venue_image_id=image_id,
                current_admin=db.get(User, admin_id),
            )
        assert exc_info.value.status_code == 503
        assert exc_info.value.detail["code"] == "STORAGE.IMAGE_PROCESSOR_BUSY"
        assert fake.downloads == []
    finally:
        venue_image_service._IMAGE_PROCESSING_SLOT.release()


def test_processor_readiness_failure_precedes_upload_signing_and_persistence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import venue_image_service

    fake = _install_storage_fake(monkeypatch)
    admin_id, venue_id = _setup()
    monkeypatch.setattr(
        venue_image_service,
        "validate_image_processor_readiness",
        lambda _allowed: (_ for _ in ()).throw(
            ImageProcessorNotReadyError("synthetic unavailable codec")
        ),
    )
    with _session() as db, pytest.raises(HTTPException) as exc_info:
        venue_image_service.create_venue_image_upload(
            db,
            venue_id=venue_id,
            upload_request=_request(size=len(fake.source)),
            current_admin=db.get(User, admin_id),
        )
    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["code"] == "STORAGE.IMAGE_PROCESSOR_UNAVAILABLE"
    assert fake.uploads == []
    with _session() as db:
        assert db.scalars(select(VenueImage)).all() == []


def test_completion_readiness_failure_precedes_storage_work_and_releases_slot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import venue_image_service

    fake, admin_id, _venue_id, image_id, _initiation = _create_pending(monkeypatch)
    events: list[tuple[str, str, dict[str, object]]] = []
    monkeypatch.setattr(
        venue_image_service,
        "validate_image_processor_readiness",
        lambda _allowed: (_ for _ in ()).throw(
            ImageProcessorNotReadyError("synthetic unavailable codec")
        ),
    )
    monkeypatch.setattr(
        venue_image_service,
        "emit_event",
        lambda name, severity, fields: events.append((name, severity, fields)) or True,
    )

    with _session() as db, pytest.raises(HTTPException) as exc_info:
        venue_image_service.complete_venue_image_upload(
            db,
            venue_image_id=image_id,
            current_admin=db.get(User, admin_id),
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == {
        "code": "STORAGE.IMAGE_PROCESSOR_UNAVAILABLE",
        "message": "Image processing is unavailable.",
        "outcome": "not_ready",
    }
    assert fake.downloads == []
    assert fake.publications == []
    assert fake.deletes == []
    assert events == [
        (
            "venue_image.processor_not_ready",
            "error",
            {
                "resource_kind": "venue_image",
                "result": "codec_unavailable",
            },
        )
    ]
    with _session() as db:
        image = db.get(VenueImage, image_id)
        assert image.image_status == "pending_upload"
        assert image.publication_object_key is None
    _assert_processing_slot_is_released()


def test_model_rejects_partial_publication_tuple() -> None:
    admin_id, venue_id = _setup()
    with _session() as db:
        image = VenueImage(
            id=uuid.uuid4(),
            venue_id=venue_id,
            uploaded_by_user_id=admin_id,
            storage_provider="r2",
            storage_object_key=f"venues/{venue_id}/staging/{uuid.uuid4()}.jpg",
            storage_bucket="synthetic-bucket",
            storage_account_id="synthetic-account",
            content_type="image/jpeg",
            size_bytes=100,
            image_role="gallery",
            image_status="active",
            sort_order=0,
            publication_object_key=f"venues/{venue_id}/published/partial.jpg",
        )
        db.add(image)
        with pytest.raises(IntegrityError):
            db.flush()


@pytest.mark.parametrize(
    ("image_status", "published"),
    [
        ("pending_upload", False),
        ("active", True),
        ("hidden", True),
        ("removed", False),
        ("removed", True),
    ],
)
def test_database_accepts_complete_publication_state_matrix(
    image_status: str,
    published: bool,
) -> None:
    admin_id, venue_id = _setup()
    image_id = uuid.uuid4()
    publication = (
        f"venues/{venue_id}/published/{image_id}/{uuid.uuid4()}.jpg"
        if published
        else None
    )
    with _session() as db:
        image = VenueImage(
            id=image_id,
            venue_id=venue_id,
            uploaded_by_user_id=admin_id,
            storage_provider="r2",
            storage_object_key=f"venues/{venue_id}/staging/{image_id}.jpg",
            storage_bucket="synthetic-bucket",
            storage_account_id="synthetic-account",
            content_type="image/jpeg",
            size_bytes=100,
            image_role="gallery",
            image_status=image_status,
            sort_order=0,
            upload_expires_at=(
                datetime.now(timezone.utc) + timedelta(minutes=5)
                if image_status == "pending_upload"
                else None
            ),
            publication_object_key=publication,
            publication_content_type="image/jpeg" if published else None,
            publication_size_bytes=90 if published else None,
            publication_etag='"published"' if published else None,
            upload_completed_at=datetime.now(timezone.utc) if published else None,
            deleted_at=datetime.now(timezone.utc)
            if image_status == "removed"
            else None,
        )
        db.add(image)
        db.commit()
        assert db.get(VenueImage, image_id).image_status == image_status


@pytest.mark.parametrize(
    ("overrides", "constraint_name"),
    [
        (
            {"publication_content_type": None},
            "ck_venue_images_publication_tuple_complete",
        ),
        (
            {
                "image_status": "pending_upload",
                "publication_object_key": None,
                "publication_content_type": None,
                "publication_size_bytes": None,
                "publication_etag": None,
                "upload_completed_at": None,
                "upload_expires_at": None,
            },
            "ck_venue_images_pending_upload_intent",
        ),
        (
            {
                "publication_object_key": None,
                "publication_content_type": None,
                "publication_size_bytes": None,
                "publication_etag": None,
                "upload_completed_at": None,
            },
            "ck_venue_images_publication_status",
        ),
        (
            {"publication_content_type": "image/gif"},
            "ck_venue_images_publication_content_type",
        ),
        (
            {"publication_size_bytes": 0},
            "ck_venue_images_publication_size_bytes",
        ),
        (
            {"publication_size_bytes": 8 * 1024 * 1024 + 1},
            "ck_venue_images_publication_size_bytes",
        ),
        (
            {"publication_object_key": " "},
            "ck_venue_images_publication_object_key_not_empty",
        ),
        (
            {"publication_etag": " "},
            "ck_venue_images_publication_etag_not_empty",
        ),
    ],
)
def test_database_rejects_each_invalid_publication_state(
    overrides: dict[str, object],
    constraint_name: str,
) -> None:
    admin_id, venue_id = _setup()
    image_id = uuid.uuid4()
    values: dict[str, object] = {
        "id": image_id,
        "venue_id": venue_id,
        "uploaded_by_user_id": admin_id,
        "storage_provider": "r2",
        "storage_object_key": f"venues/{venue_id}/staging/{image_id}.jpg",
        "storage_bucket": "synthetic-bucket",
        "storage_account_id": "synthetic-account",
        "content_type": "image/jpeg",
        "size_bytes": 100,
        "image_role": "gallery",
        "image_status": "active",
        "sort_order": 0,
        "publication_object_key": (
            f"venues/{venue_id}/published/{image_id}/candidate.jpg"
        ),
        "publication_content_type": "image/jpeg",
        "publication_size_bytes": 90,
        "publication_etag": '"published"',
        "upload_completed_at": datetime.now(timezone.utc),
    }
    values.update(overrides)

    with _session() as db:
        db.add(VenueImage(**values))
        with pytest.raises(IntegrityError) as exc_info:
            db.flush()

    assert constraint_name in str(exc_info.value.orig)


def test_database_rejects_duplicate_publication_key() -> None:
    admin_id, venue_id = _setup()
    publication_key = f"venues/{venue_id}/published/shared.jpg"

    def image() -> VenueImage:
        image_id = uuid.uuid4()
        return VenueImage(
            id=image_id,
            venue_id=venue_id,
            uploaded_by_user_id=admin_id,
            storage_provider="r2",
            storage_object_key=f"venues/{venue_id}/staging/{image_id}.jpg",
            storage_bucket="synthetic-bucket",
            storage_account_id="synthetic-account",
            content_type="image/jpeg",
            size_bytes=100,
            image_role="gallery",
            image_status="active",
            sort_order=0,
            publication_object_key=publication_key,
            publication_content_type="image/jpeg",
            publication_size_bytes=90,
            publication_etag='"published"',
            upload_completed_at=datetime.now(timezone.utc),
        )

    with _session() as db:
        db.add(image())
        db.commit()
    with _session() as db:
        db.add(image())
        with pytest.raises(IntegrityError) as exc_info:
            db.flush()

    assert "uq_venue_images_publication_object_key" in str(exc_info.value.orig)


def test_active_reader_uses_publication_key_and_persisted_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services.venue_image_service import build_admin_venue_image_read

    fake, _admin_id, venue_id, image_id, _response = _create_pending(monkeypatch)
    completed_at = datetime.now(timezone.utc)
    with _session() as db:
        image = db.get(VenueImage, image_id)
        image.image_status = "active"
        image.publication_object_key = (
            f"venues/{venue_id}/published/{image_id}/winner.jpg"
        )
        image.publication_content_type = "image/jpeg"
        image.publication_size_bytes = 123
        image.publication_etag = '"winner"'
        image.upload_completed_at = completed_at
        db.commit()
        read = build_admin_venue_image_read(image)
    assert read.storage_object_key.endswith("winner.jpg")
    assert read.size_bytes == 123
    assert fake.reads[0][1].endswith("winner.jpg")


def test_commit_return_failure_preserves_objects_and_reports_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services.venue_image_service import complete_venue_image_upload

    fake, admin_id, _venue_id, image_id, initiation = _create_pending(monkeypatch)
    with _session() as db:
        real_commit = db.commit

        def commit_then_raise() -> None:
            real_commit()
            raise RuntimeError("synthetic lost commit acknowledgement")

        monkeypatch.setattr(db, "commit", commit_then_raise)
        with pytest.raises(HTTPException) as exc_info:
            complete_venue_image_upload(
                db,
                venue_image_id=image_id,
                current_admin=db.get(User, admin_id),
            )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["code"] == "API.DATABASE_COMMIT_OUTCOME_UNKNOWN"
    assert fake.deletes == []
    assert initiation.image.storage_object_key not in [
        key for _target, key in fake.deletes
    ]
    with _session() as db:
        image = db.get(VenueImage, image_id)
        assert image.image_status == "active"
        assert image.publication_object_key == fake.publications[0][1]
    _assert_processing_slot_is_released()


def test_commit_unknown_survives_diagnostic_invalidation_and_close_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import venue_image_service

    fake, admin_id, _venue_id, image_id, _initiation = _create_pending(monkeypatch)
    db = _session()
    real_commit = db.commit
    real_close = db.close
    recovery_attempts: list[str] = []

    def commit_then_raise() -> None:
        real_commit()
        raise RuntimeError("synthetic lost commit acknowledgement")

    def reject_event(*args, **kwargs) -> bool:
        recovery_attempts.append("event")
        raise RuntimeError("synthetic event failure")

    def reject_invalidation() -> None:
        recovery_attempts.append("invalidate")
        raise RuntimeError("synthetic invalidation failure")

    def reject_close() -> None:
        recovery_attempts.append("close")
        raise RuntimeError("synthetic close failure")

    monkeypatch.setattr(db, "commit", commit_then_raise)
    monkeypatch.setattr(db, "invalidate", reject_invalidation)
    monkeypatch.setattr(db, "close", reject_close)
    monkeypatch.setattr(venue_image_service, "_emit_venue_image_event", reject_event)
    try:
        with pytest.raises(HTTPException) as exc_info:
            venue_image_service.complete_venue_image_upload(
                db,
                venue_image_id=image_id,
                current_admin=db.get(User, admin_id),
            )
    finally:
        real_close()

    assert exc_info.value.detail["code"] == "API.DATABASE_COMMIT_OUTCOME_UNKNOWN"
    assert isinstance(exc_info.value.__cause__, RuntimeError)
    assert str(exc_info.value.__cause__) == "synthetic lost commit acknowledgement"
    assert recovery_attempts == ["event", "invalidate", "close"]
    assert fake.deletes == []
    with _session() as verification_db:
        stored = verification_db.get(VenueImage, image_id)
        assert stored.image_status == "active"
        assert stored.publication_object_key == fake.publications[0][1]
    _assert_processing_slot_is_released()


def test_precommit_read_signing_failure_cleans_only_owned_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import venue_image_service

    fake, admin_id, _venue_id, image_id, initiation = _create_pending(monkeypatch)
    monkeypatch.setattr(
        venue_image_service,
        "create_object_read_url",
        lambda **kwargs: (_ for _ in ()).throw(
            R2StorageError("synthetic signing failure")
        ),
    )

    with _session() as db, pytest.raises(HTTPException) as exc_info:
        venue_image_service.complete_venue_image_upload(
            db,
            venue_image_id=image_id,
            current_admin=db.get(User, admin_id),
        )

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail["code"] == "STORAGE.READ_URL_FAILED"
    candidate_key = fake.publications[0][1]
    assert [key for _target, key in fake.deletes] == [candidate_key]
    assert initiation.image.storage_object_key not in [
        key for _target, key in fake.deletes
    ]
    with _session() as db:
        image = db.get(VenueImage, image_id)
        assert image.image_status == "pending_upload"
        assert image.publication_object_key is None
    _assert_processing_slot_is_released()


def test_precommit_failure_survives_rollback_failure_and_cleans_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import venue_image_service

    fake, admin_id, _venue_id, image_id, initiation = _create_pending(monkeypatch)
    monkeypatch.setattr(
        venue_image_service,
        "create_object_read_url",
        lambda **kwargs: (_ for _ in ()).throw(
            R2StorageError("synthetic signing failure")
        ),
    )
    db = _session()
    real_rollback = db.rollback
    rollback_attempts = 0

    def reject_rollback() -> None:
        nonlocal rollback_attempts
        rollback_attempts += 1
        raise _SessionCleanupInterrupt("synthetic rollback interruption")

    monkeypatch.setattr(db, "rollback", reject_rollback)
    try:
        with pytest.raises(HTTPException) as exc_info:
            venue_image_service.complete_venue_image_upload(
                db,
                venue_image_id=image_id,
                current_admin=db.get(User, admin_id),
            )
    finally:
        monkeypatch.setattr(db, "rollback", real_rollback)
        db.close()

    assert exc_info.value.detail["code"] == "STORAGE.READ_URL_FAILED"
    assert rollback_attempts == 1
    candidate_key = fake.publications[0][1]
    assert [key for _target, key in fake.deletes] == [candidate_key]
    assert initiation.image.storage_object_key not in [
        key for _target, key in fake.deletes
    ]
    with _session() as verification_db:
        stored = verification_db.get(VenueImage, image_id)
        assert stored.image_status == "pending_upload"
        assert stored.publication_object_key is None
    _assert_processing_slot_is_released()


def test_precommit_base_exception_survives_rollback_and_cleanup_interruptions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import venue_image_service

    fake, admin_id, _venue_id, image_id, initiation = _create_pending(monkeypatch)
    primary = _CommitInterrupt("synthetic precommit interruption")
    monkeypatch.setattr(
        venue_image_service,
        "build_admin_venue_image_read",
        lambda *args, **kwargs: (_ for _ in ()).throw(primary),
    )
    cleanup_attempts: list[str] = []

    def reject_delete(*, object_key: str, **kwargs) -> None:
        cleanup_attempts.append(object_key)
        raise _SessionCleanupInterrupt("synthetic delete interruption")

    monkeypatch.setattr(venue_image_service, "delete_object", reject_delete)
    events: list[tuple[str, str, dict[str, object]]] = []
    monkeypatch.setattr(
        venue_image_service,
        "emit_event",
        lambda name, severity, fields: events.append((name, severity, fields)) or True,
    )
    db = _session()
    real_rollback = db.rollback

    def reject_rollback() -> None:
        raise _SessionCleanupInterrupt("synthetic rollback interruption")

    monkeypatch.setattr(db, "rollback", reject_rollback)
    try:
        with pytest.raises(_CommitInterrupt) as exc_info:
            venue_image_service.complete_venue_image_upload(
                db,
                venue_image_id=image_id,
                current_admin=db.get(User, admin_id),
            )
    finally:
        monkeypatch.setattr(db, "rollback", real_rollback)
        db.close()

    assert exc_info.value is primary
    candidate_key = fake.publications[0][1]
    assert cleanup_attempts == [candidate_key]
    assert initiation.image.storage_object_key not in cleanup_attempts
    assert events == [
        (
            "venue_image.cleanup_incomplete",
            "warning",
            {
                "resource_kind": "publication_candidate",
                "result": "unknown_outcome",
            },
        )
    ]
    with _session() as verification_db:
        stored = verification_db.get(VenueImage, image_id)
        assert stored.image_status == "pending_upload"
        assert stored.publication_object_key is None
    _assert_processing_slot_is_released()


def test_rollback_cleanup_propagates_new_cancellation() -> None:
    from backend.services.venue_image_service import _rollback_preserving_primary_result

    cancellation = asyncio.CancelledError()

    class Session:
        def rollback(self) -> None:
            raise cancellation

    try:
        raise ValueError("synthetic primary failure")
    except ValueError:
        with pytest.raises(asyncio.CancelledError) as raised:
            _rollback_preserving_primary_result(Session())  # type: ignore[arg-type]

    assert raised.value is cancellation


def test_rollback_cleanup_preserves_original_cancellation() -> None:
    from backend.services.venue_image_service import _rollback_preserving_primary_result

    primary = asyncio.CancelledError()
    secondary = asyncio.CancelledError()

    class Session:
        def rollback(self) -> None:
            raise secondary

    with pytest.raises(asyncio.CancelledError) as raised:
        try:
            raise primary
        except asyncio.CancelledError:
            _rollback_preserving_primary_result(Session())  # type: ignore[arg-type]
            raise

    assert raised.value is primary


@pytest.mark.parametrize("failing_flush", [1, 2])
def test_completion_flush_failure_rolls_back_and_cleans_only_owned_candidate(
    monkeypatch: pytest.MonkeyPatch,
    failing_flush: int,
) -> None:
    from backend.services import venue_image_service

    fake, admin_id, _venue_id, image_id, initiation = _create_pending(monkeypatch)
    with _session() as setup_db:
        image = setup_db.get(VenueImage, image_id)
        image.is_primary = True
        setup_db.commit()

    with _session() as db:
        real_flush = db.flush
        flush_count = 0

        def controlled_flush(*args, **kwargs) -> None:
            nonlocal flush_count
            flush_count += 1
            if flush_count == failing_flush:
                raise RuntimeError(f"synthetic flush {failing_flush} failure")
            real_flush(*args, **kwargs)

        monkeypatch.setattr(db, "flush", controlled_flush)
        with pytest.raises(HTTPException) as exc_info:
            venue_image_service.complete_venue_image_upload(
                db,
                venue_image_id=image_id,
                current_admin=db.get(User, admin_id),
            )

    assert exc_info.value.detail["code"] == "STORAGE.PERSISTENCE_FAILED"
    candidate_key = fake.publications[0][1]
    assert [key for _target, key in fake.deletes] == [candidate_key]
    assert initiation.image.storage_object_key not in [
        key for _target, key in fake.deletes
    ]
    with _session() as verification_db:
        stored = verification_db.get(VenueImage, image_id)
        assert stored.image_status == "pending_upload"
        assert stored.publication_object_key is None
        assert (
            verification_db.scalars(
                select(AdminAction).where(
                    AdminAction.target_venue_image_id == image_id,
                    AdminAction.action_type == "update_venue_image",
                )
            ).all()
            == []
        )
    _assert_processing_slot_is_released()


def test_postcommit_cleanup_failure_preserves_success_and_releases_slot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import venue_image_service

    _fake, admin_id, _venue_id, image_id, _initiation = _create_pending(monkeypatch)
    monkeypatch.setattr(
        venue_image_service,
        "delete_object",
        lambda **kwargs: (_ for _ in ()).throw(
            R2MutationOutcomeUnknownError("synthetic cleanup uncertainty")
        ),
    )

    with _session() as db:
        response = venue_image_service.complete_venue_image_upload(
            db,
            venue_image_id=image_id,
            current_admin=db.get(User, admin_id),
        )

    assert response.image_status == "active"
    with _session() as db:
        assert db.get(VenueImage, image_id).publication_object_key == (
            response.storage_object_key
        )
    _assert_processing_slot_is_released()


def test_commit_cancellation_propagates_and_preserves_committed_winner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services.venue_image_service import complete_venue_image_upload

    fake, admin_id, _venue_id, image_id, _response = _create_pending(monkeypatch)
    with _session() as db:
        admin = db.get(User, admin_id)
        real_commit = db.commit

        def commit_then_cancel() -> None:
            real_commit()
            raise asyncio.CancelledError()

        recovery_attempts: list[str] = []

        def reject_recovery(name: str):
            def reject(*args, **kwargs):
                recovery_attempts.append(name)
                raise RuntimeError(f"synthetic {name} failure")

            return reject

        real_close = db.close
        monkeypatch.setattr(db, "commit", commit_then_cancel)
        monkeypatch.setattr(db, "invalidate", reject_recovery("invalidate"))
        monkeypatch.setattr(db, "close", reject_recovery("close"))
        monkeypatch.setattr(
            "backend.services.venue_image_service._emit_venue_image_event",
            reject_recovery("event"),
        )
        with pytest.raises(asyncio.CancelledError):
            complete_venue_image_upload(
                db,
                venue_image_id=image_id,
                current_admin=admin,
            )
        monkeypatch.setattr(db, "close", real_close)
        real_close()

    assert fake.deletes == []
    assert recovery_attempts == ["event", "invalidate", "close"]
    with _session() as db:
        assert db.get(VenueImage, image_id).image_status == "active"
    _assert_processing_slot_is_released()


@pytest.mark.parametrize("original_kind", ["exception", "base_exception"])
@pytest.mark.parametrize("cleanup_site", ["invalidate", "close"])
def test_commit_interruption_survives_each_secondary_base_exception_cleanup_failure(
    monkeypatch: pytest.MonkeyPatch,
    original_kind: str,
    cleanup_site: str,
) -> None:
    from backend.services import venue_image_service

    fake, admin_id, _venue_id, image_id, _response = _create_pending(monkeypatch)
    db = _session()
    real_commit = db.commit
    real_invalidate = db.invalidate
    real_close = db.close
    original_failure: BaseException = (
        RuntimeError("synthetic lost commit acknowledgement")
        if original_kind == "exception"
        else _CommitInterrupt("synthetic commit interruption")
    )
    cleanup_attempts: list[str] = []

    def commit_then_interrupt() -> None:
        real_commit()
        raise original_failure

    def tracked_invalidate() -> None:
        cleanup_attempts.append("invalidate")
        if cleanup_site == "invalidate":
            raise _SessionCleanupInterrupt("synthetic invalidate interruption")
        real_invalidate()

    def tracked_close() -> None:
        cleanup_attempts.append("close")
        if cleanup_site == "close":
            raise _SessionCleanupInterrupt("synthetic close interruption")
        real_close()

    monkeypatch.setattr(db, "commit", commit_then_interrupt)
    monkeypatch.setattr(db, "invalidate", tracked_invalidate)
    monkeypatch.setattr(db, "close", tracked_close)
    try:
        admin = db.get(User, admin_id)
        if original_kind == "exception":
            with pytest.raises(HTTPException) as exc_info:
                venue_image_service.complete_venue_image_upload(
                    db,
                    venue_image_id=image_id,
                    current_admin=admin,
                )
            assert exc_info.value.detail["code"] == (
                "API.DATABASE_COMMIT_OUTCOME_UNKNOWN"
            )
            assert exc_info.value.__cause__ is original_failure
        else:
            with pytest.raises(_CommitInterrupt) as exc_info:
                venue_image_service.complete_venue_image_upload(
                    db,
                    venue_image_id=image_id,
                    current_admin=admin,
                )
            assert exc_info.value is original_failure
    finally:
        monkeypatch.setattr(db, "invalidate", real_invalidate)
        monkeypatch.setattr(db, "close", real_close)
        real_close()

    assert cleanup_attempts == ["invalidate", "close"]
    assert fake.deletes == []
    with _session() as verification_db:
        stored = verification_db.get(VenueImage, image_id)
        assert stored.image_status == "active"
        assert stored.publication_object_key == fake.publications[0][1]
        audits = verification_db.scalars(
            select(AdminAction).where(
                AdminAction.target_venue_image_id == image_id,
                AdminAction.action_type == "update_venue_image",
            )
        ).all()
        assert len(audits) == 1
    _assert_processing_slot_is_released()


def test_completion_target_mismatch_uses_adapter_metric_and_exact_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import r2_storage_service, venue_image_service

    fake, admin_id, _venue_id, image_id, _initiation = _create_pending(monkeypatch)
    with _session() as db:
        image = db.get(VenueImage, image_id)
        image.storage_account_id = "different-account"
        db.commit()

    client_constructed = False

    def fail_client(*args, **kwargs):
        nonlocal client_constructed
        client_constructed = True
        pytest.fail("target mismatch constructed a Cloudflare R2 client")

    events: list[tuple[str, str, dict[str, object]]] = []
    monkeypatch.setattr(
        venue_image_service, "download_object", r2_storage_service.download_object
    )
    monkeypatch.setattr(r2_storage_service, "get_r2_client", fail_client)
    monkeypatch.setattr(
        venue_image_service,
        "emit_event",
        lambda name, severity, fields: events.append((name, severity, fields)) or True,
    )
    recorder = MetricsRecorder("api", "test", "venue-image-target-test")

    with (
        _session() as db,
        metrics_context(recorder),
        pytest.raises(HTTPException) as exc_info,
    ):
        venue_image_service.complete_venue_image_upload(
            db,
            venue_image_id=image_id,
            current_admin=db.get(User, admin_id),
        )

    assert exc_info.value.detail == {
        "code": "STORAGE.TARGET_MISMATCH",
        "message": "Stored image target does not match configured storage.",
        "outcome": "configuration_error",
    }
    assert client_constructed is False
    assert dict(recorder.snapshot().series[0].dimensions) == {
        "operation": "r2.object.download",
        "provider_kind": "r2",
        "result": "configuration_error",
    }
    assert events == [
        (
            "storage.operation_failed",
            "error",
            {
                "provider_kind": "r2",
                "operation": "r2.object.download",
                "result": "configuration_error",
                "stable_error_code": "STORAGE.TARGET_MISMATCH",
            },
        )
    ]
    assert fake.downloads == []
    assert fake.publications == []
    assert fake.deletes == []
    _assert_processing_slot_is_released()


def test_configuration_narrowed_after_initiation_rejects_before_publication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import venue_image_service

    fake, admin_id, _venue_id, image_id, initiation = _create_pending(monkeypatch)
    narrowed = R2StorageConfig(
        **{
            **_config().__dict__,
            "allowed_image_types": frozenset({"image/png"}),
        }
    )
    monkeypatch.setattr(venue_image_service, "get_r2_storage_config", lambda: narrowed)

    with _session() as db, pytest.raises(HTTPException) as exc_info:
        venue_image_service.complete_venue_image_upload(
            db,
            venue_image_id=image_id,
            current_admin=db.get(User, admin_id),
        )

    assert exc_info.value.detail == {
        "code": "STORAGE.IMAGE_INVALID",
        "message": "Uploaded image content is invalid.",
        "outcome": "unsupported_content",
    }
    assert fake.publications == []
    assert [key for _target, key in fake.deletes] == [
        initiation.image.storage_object_key
    ]
    _assert_processing_slot_is_released()


def test_removed_before_and_after_publication_use_only_eligible_read_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import venue_image_service

    pending_fake, admin_id, _venue_id, pending_id, _pending = _create_pending(
        monkeypatch
    )
    with _session() as db:
        pending_response = venue_image_service.update_venue_image(
            db,
            venue_image_id=pending_id,
            image_update=VenueImageUpdate(
                image_status="removed", reason="Discard unused upload."
            ),
            current_admin=db.get(User, admin_id),
        )
    assert pending_response.image_url is None
    assert pending_fake.reads == []

    published_fake, admin_id, _venue_id, published_id, _pending = _create_pending(
        monkeypatch
    )
    with _session() as db:
        active = venue_image_service.complete_venue_image_upload(
            db,
            venue_image_id=published_id,
            current_admin=db.get(User, admin_id),
        )
    publication_key = active.storage_object_key
    published_fake.reads.clear()
    with _session() as db:
        removed_response = venue_image_service.update_venue_image(
            db,
            venue_image_id=published_id,
            image_update=VenueImageUpdate(
                image_status="removed", reason="Retire published image."
            ),
            current_admin=db.get(User, admin_id),
        )
    assert removed_response.image_url == "https://read.example.invalid/signed"
    assert [key for _target, key in published_fake.reads] == [publication_key]


@pytest.mark.parametrize(
    "pairing",
    ["initiation-initiation", "reactivation-reactivation", "mixed"],
)
def test_selected_image_capacity_producers_serialize_on_the_venue(
    monkeypatch: pytest.MonkeyPatch,
    pairing: str,
) -> None:
    from backend.services import venue_image_service

    _install_storage_fake(monkeypatch)
    admin_id, venue_id = _setup()

    def published_image(status: str, sort_order: int) -> VenueImage:
        image_id = uuid.uuid4()
        return VenueImage(
            id=image_id,
            venue_id=venue_id,
            uploaded_by_user_id=admin_id,
            storage_provider="r2",
            storage_object_key=f"venues/{venue_id}/staging/{image_id}.jpg",
            storage_bucket="synthetic-bucket",
            storage_account_id="synthetic-account",
            content_type="image/jpeg",
            size_bytes=100,
            image_role="gallery",
            image_status=status,
            sort_order=sort_order,
            upload_completed_at=datetime.now(timezone.utc),
            publication_object_key=(
                f"venues/{venue_id}/published/{image_id}/{uuid.uuid4()}.jpg"
            ),
            publication_content_type="image/jpeg",
            publication_size_bytes=90,
            publication_etag=f'"{image_id}"',
        )

    existing = [published_image("active", index) for index in (0, 1)]
    hidden = [published_image("hidden", index) for index in (2, 3)]
    with _session() as db:
        db.add_all([*existing, *hidden])
        db.commit()
        hidden_ids = [image.id for image in hidden]

    barrier = Barrier(2)

    def initiate() -> str:
        with _session() as db:
            barrier.wait(timeout=10)
            try:
                venue_image_service.create_venue_image_upload(
                    db,
                    venue_id=venue_id,
                    upload_request=_request(),
                    current_admin=db.get(User, admin_id),
                )
                return "created"
            except HTTPException as exc:
                return f"http-{exc.status_code}"

    def reactivate(image_id: uuid.UUID) -> str:
        with _session() as db:
            barrier.wait(timeout=10)
            try:
                venue_image_service.update_venue_image(
                    db,
                    venue_image_id=image_id,
                    image_update=VenueImageUpdate(image_status="active"),
                    current_admin=db.get(User, admin_id),
                )
                return "reactivated"
            except HTTPException as exc:
                return f"http-{exc.status_code}"

    with ThreadPoolExecutor(max_workers=2) as executor:
        if pairing == "initiation-initiation":
            futures = [executor.submit(initiate), executor.submit(initiate)]
        elif pairing == "reactivation-reactivation":
            futures = [
                executor.submit(reactivate, hidden_ids[0]),
                executor.submit(reactivate, hidden_ids[1]),
            ]
        else:
            futures = [
                executor.submit(initiate),
                executor.submit(reactivate, hidden_ids[0]),
            ]
        results = [future.result(timeout=20) for future in futures]

    assert sum(result in {"created", "reactivated"} for result in results) == 1
    assert results.count("http-400") == 1
    with _session() as db:
        selected = db.scalars(
            select(VenueImage).where(
                VenueImage.venue_id == venue_id,
                VenueImage.deleted_at.is_(None),
                VenueImage.image_status.in_({"pending_upload", "active"}),
            )
        ).all()
        assert len(selected) == 3


def test_independent_completions_commit_one_coherent_winner_and_clean_only_loser(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import venue_image_service

    fake, admin_id, _venue_id, image_id, initiation = _create_pending(monkeypatch)
    monkeypatch.setattr(
        venue_image_service,
        "_IMAGE_PROCESSING_SLOT",
        BoundedSemaphore(value=2),
    )
    loser_reached_publication = Event()
    winner_committed = Event()
    calls_lock = Lock()

    def publish(
        *, target, object_key: str, body: bytes, content_type: str, config=None
    ):
        with calls_lock:
            fake.publications.append((target, object_key, body, content_type))
        if current_thread().name == "completion-loser":
            loser_reached_publication.set()
            assert winner_committed.wait(timeout=10)
        else:
            assert loser_reached_publication.wait(timeout=10)
        return R2PublishedObject(etag=f'"{current_thread().name}"')

    monkeypatch.setattr(venue_image_service, "publish_object", publish)
    monkeypatch.setattr(
        venue_image_service,
        "create_object_read_url",
        lambda *, object_key, **kwargs: f"https://read.example.invalid/{object_key}",
    )
    outcomes: dict[str, object] = {}

    def complete(label: str) -> None:
        try:
            with _session() as db:
                if label == "winner":
                    real_commit = db.commit

                    def tracked_commit() -> None:
                        real_commit()
                        winner_committed.set()

                    db.commit = tracked_commit  # type: ignore[method-assign]
                outcomes[label] = venue_image_service.complete_venue_image_upload(
                    db,
                    venue_image_id=image_id,
                    current_admin=db.get(User, admin_id),
                )
        except BaseException as exc:  # noqa: BLE001 - propagate into the test thread.
            outcomes[label] = exc

    loser = Thread(target=complete, args=("loser",), name="completion-loser")
    winner = Thread(target=complete, args=("winner",), name="completion-winner")
    loser.start()
    winner.start()
    loser.join(timeout=15)
    winner.join(timeout=15)

    assert not loser.is_alive()
    assert not winner.is_alive()
    assert getattr(outcomes["winner"], "image_status", None) == "active"
    assert isinstance(outcomes["loser"], HTTPException)
    assert outcomes["loser"].status_code == 409
    assert outcomes["loser"].detail["code"] == "STORAGE.UPLOAD_NOT_PENDING"

    published_keys = [item[1] for item in fake.publications]
    winner_key = outcomes["winner"].storage_object_key
    loser_key = next(key for key in published_keys if key != winner_key)
    winner_publication = next(
        item for item in fake.publications if item[1] == winner_key
    )
    expected = sanitize_venue_image(
        fake.source,
        declared_content_type="image/jpeg",
        allowed_types=frozenset({"image/jpeg"}),
        max_bytes=1_000_000,
    )
    assert winner_publication[2] == expected.body
    assert winner_publication[3] == expected.content_type
    assert outcomes["winner"].content_type == expected.content_type
    assert outcomes["winner"].size_bytes == len(expected.body)
    assert outcomes["winner"].etag == '"completion-winner"'
    assert outcomes["winner"].image_url == (
        f"https://read.example.invalid/{winner_key}"
    )
    deleted_keys = [key for _target, key in fake.deletes]
    assert deleted_keys.count(initiation.image.storage_object_key) == 1
    assert deleted_keys.count(loser_key) == 1
    assert winner_key not in deleted_keys
    with _session() as db:
        image = db.get(VenueImage, image_id)
        assert image.image_status == "active"
        assert image.publication_object_key == winner_key
        assert image.publication_content_type == expected.content_type
        assert image.publication_size_bytes == len(expected.body)
        assert image.publication_etag == '"completion-winner"'
        audits = db.scalars(
            select(AdminAction).where(
                AdminAction.target_venue_image_id == image_id,
                AdminAction.action_type == "update_venue_image",
            )
        ).all()
        assert len(audits) == 1


def test_forced_same_key_completion_collision_never_overwrites_or_cleans_winner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import venue_image_service

    fake, admin_id, venue_id, image_id, initiation = _create_pending(monkeypatch)
    monkeypatch.setattr(
        venue_image_service,
        "_IMAGE_PROCESSING_SLOT",
        BoundedSemaphore(value=2),
    )
    fixed_key = f"venues/{venue_id}/published/{image_id}/forced.jpg"
    monkeypatch.setattr(
        venue_image_service,
        "build_venue_image_publication_key",
        lambda **kwargs: fixed_key,
    )
    monkeypatch.setattr(
        venue_image_service,
        "sanitize_venue_image",
        lambda *args, **kwargs: SanitizedVenueImage(
            body=current_thread().name.encode(),
            content_type="image/jpeg",
            width=8,
            height=6,
        ),
    )
    publication_barrier = Barrier(2)
    store_lock = Lock()
    stored: dict[str, tuple[bytes, str]] = {}

    def conditional_publish(
        *, target, object_key: str, body: bytes, content_type: str, config=None
    ):
        fake.publications.append((target, object_key, body, content_type))
        publication_barrier.wait(timeout=10)
        with store_lock:
            if object_key in stored:
                raise R2PublicationCollisionError("synthetic conditional collision")
            stored[object_key] = (body, current_thread().name)
        return R2PublishedObject(etag=f'"{current_thread().name}"')

    monkeypatch.setattr(venue_image_service, "publish_object", conditional_publish)
    outcomes: dict[str, object] = {}

    def complete(label: str) -> None:
        try:
            with _session() as db:
                outcomes[label] = venue_image_service.complete_venue_image_upload(
                    db,
                    venue_image_id=image_id,
                    current_admin=db.get(User, admin_id),
                )
        except BaseException as exc:  # noqa: BLE001 - propagate into the test thread.
            outcomes[label] = exc

    threads = [
        Thread(target=complete, args=(label,), name=label)
        for label in ("candidate-a", "candidate-b")
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=15)

    assert all(not thread.is_alive() for thread in threads)
    successes = [
        label
        for label, value in outcomes.items()
        if not isinstance(value, BaseException)
    ]
    failures = [
        label for label, value in outcomes.items() if isinstance(value, HTTPException)
    ]
    assert len(successes) == 1
    assert len(failures) == 1
    assert outcomes[failures[0]].status_code == 502
    assert outcomes[failures[0]].detail["code"] == "STORAGE.PUBLICATION_FAILED"
    stored_body, stored_owner = stored[fixed_key]
    assert stored_owner == successes[0]
    assert stored_body == successes[0].encode()
    assert [key for _target, key in fake.deletes] == [
        initiation.image.storage_object_key
    ]
    with _session() as db:
        image = db.get(VenueImage, image_id)
        assert image.publication_object_key == fixed_key
        assert image.publication_etag == f'"{successes[0]}"'


def test_completion_adopts_metadata_from_independent_concurrent_patch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import venue_image_service

    _fake, admin_id, _venue_id, image_id, _initiation = _create_pending(monkeypatch)
    publication_entered = Event()
    release_publication = Event()

    def publish(
        *, target, object_key: str, body: bytes, content_type: str, config=None
    ):
        publication_entered.set()
        assert release_publication.wait(timeout=10)
        return R2PublishedObject(etag='"patched"')

    monkeypatch.setattr(venue_image_service, "publish_object", publish)
    outcome: dict[str, object] = {}

    def complete() -> None:
        try:
            with _session() as db:
                outcome["value"] = venue_image_service.complete_venue_image_upload(
                    db,
                    venue_image_id=image_id,
                    current_admin=db.get(User, admin_id),
                )
        except BaseException as exc:  # noqa: BLE001 - propagate into the test thread.
            outcome["value"] = exc

    thread = Thread(target=complete, name="completion-with-patch")
    thread.start()
    assert publication_entered.wait(timeout=10)
    with _session() as db:
        venue_image_service.update_venue_image(
            db,
            venue_image_id=image_id,
            image_update=VenueImageUpdate(
                image_role="card",
                is_primary=True,
                sort_order=2,
                alt_text="Fresh alt text",
                caption="Fresh caption",
            ),
            current_admin=db.get(User, admin_id),
        )
    release_publication.set()
    thread.join(timeout=15)

    assert not thread.is_alive()
    response = outcome["value"]
    assert not isinstance(response, BaseException)
    assert response.image_status == "active"
    assert response.image_role == "card"
    assert response.is_primary is True
    assert response.sort_order == 2
    assert response.alt_text == "Fresh alt text"
    assert response.caption == "Fresh caption"
    with _session() as db:
        image = db.get(VenueImage, image_id)
        assert image.image_role == "card"
        assert image.is_primary is True
        assert image.sort_order == 2
        completion_audit = db.scalars(
            select(AdminAction).where(
                AdminAction.target_venue_image_id == image_id,
                AdminAction.action_type == "update_venue_image",
            )
        ).all()[-1]
        assert completion_audit.metadata_["after"]["image_role"] == "card"


def test_completion_respects_independent_concurrent_removal_and_cleans_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import venue_image_service

    fake, admin_id, _venue_id, image_id, initiation = _create_pending(monkeypatch)
    publication_entered = Event()
    release_publication = Event()
    candidate_key: list[str] = []

    def publish(
        *, target, object_key: str, body: bytes, content_type: str, config=None
    ):
        candidate_key.append(object_key)
        publication_entered.set()
        assert release_publication.wait(timeout=10)
        return R2PublishedObject(etag='"removed-race"')

    monkeypatch.setattr(venue_image_service, "publish_object", publish)
    outcome: dict[str, BaseException] = {}

    def complete() -> None:
        try:
            with _session() as db:
                venue_image_service.complete_venue_image_upload(
                    db,
                    venue_image_id=image_id,
                    current_admin=db.get(User, admin_id),
                )
        except BaseException as exc:  # noqa: BLE001 - propagate into the test thread.
            outcome["error"] = exc

    thread = Thread(target=complete, name="completion-with-removal")
    thread.start()
    assert publication_entered.wait(timeout=10)
    with _session() as db:
        venue_image_service.update_venue_image(
            db,
            venue_image_id=image_id,
            image_update=VenueImageUpdate(
                image_status="removed",
                reason="Concurrent administrative removal",
            ),
            current_admin=db.get(User, admin_id),
        )
    release_publication.set()
    thread.join(timeout=15)

    assert not thread.is_alive()
    assert isinstance(outcome["error"], HTTPException)
    assert outcome["error"].status_code in {404, 409}
    deleted_keys = [key for _target, key in fake.deletes]
    assert candidate_key == [deleted_keys[0]]
    assert initiation.image.storage_object_key not in deleted_keys
    with _session() as db:
        image = db.get(VenueImage, image_id)
        assert image.image_status == "removed"
        assert image.publication_object_key is None
