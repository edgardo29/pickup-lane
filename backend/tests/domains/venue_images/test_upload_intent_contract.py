from __future__ import annotations

import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from threading import Barrier, Lock

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import AdminAction, User, Venue, VenueImage
from backend.observability.metrics import MetricsRecorder, metrics_context
from backend.observability.timeouts import DependencyReadTimeoutError
from backend.schemas.venue_image_schema import (
    VenueImageCompleteUpload,
    VenueImageUpdate,
    VenueImageUploadCreate,
)
from backend.services.r2_storage_service import (
    R2ObjectNotFoundError,
    R2ObjectProperties,
    R2ObjectUploadTicket,
    R2StorageConfig,
    R2StorageConfigError,
    R2StorageError,
)


_FUTURE = datetime(2099, 1, 1, tzinfo=timezone.utc)
_COMPLETED = datetime(2025, 1, 1, tzinfo=timezone.utc)


@dataclass
class _R2Fake:
    upload_calls: list[str] = field(default_factory=list)
    read_calls: list[str] = field(default_factory=list)
    metadata_calls: list[str] = field(default_factory=list)
    events: list[str] = field(default_factory=list)
    properties: dict[str, R2ObjectProperties] = field(default_factory=dict)
    metadata_barrier: Barrier | None = None
    metadata_error: BaseException | None = None
    read_error: BaseException | None = None
    lock: Lock = field(default_factory=Lock)


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


def _admin() -> User:
    unique = uuid.uuid4()
    return User(
        id=uuid.uuid4(),
        auth_user_id=f"venue-image-admin-{unique}",
        role="admin",
        email=f"venue-image-admin-{unique}@example.invalid",
        first_name="Upload",
        last_name="Admin",
        account_status="active",
        hosting_status="eligible",
    )


def _venue() -> Venue:
    return Venue(
        id=uuid.uuid4(),
        name="Venue Image Upload Field",
        address_line_1="1 Intent Way",
        city="Austin",
        state="TX",
        postal_code="78701",
        country_code="US",
        venue_status="approved",
        is_active=True,
    )


def _upload_request(index: int = 0) -> VenueImageUploadCreate:
    return VenueImageUploadCreate(
        file_name=f"venue-{index}.jpg",
        content_type="image/jpeg",
        size_bytes=1024,
        image_role="gallery",
        is_primary=False,
        sort_order=min(index, 2),
    )


def _image(
    venue_id: uuid.UUID,
    admin_id: uuid.UUID,
    *,
    image_status: str,
    index: int,
    is_primary: bool = False,
    upload_expires_at: datetime | None = None,
    upload_completed_at: datetime | None = None,
) -> VenueImage:
    return VenueImage(
        id=uuid.uuid4(),
        venue_id=venue_id,
        uploaded_by_user_id=admin_id,
        storage_provider="r2",
        storage_object_key=f"venues/{venue_id}/image-{index}-{uuid.uuid4()}.jpg",
        storage_bucket="synthetic-bucket",
        storage_account_id="synthetic-account",
        content_type="image/jpeg",
        size_bytes=1024,
        etag=f"etag-{index}",
        image_role="gallery",
        image_status=image_status,
        is_primary=is_primary,
        sort_order=min(index, 2),
        upload_expires_at=upload_expires_at,
        upload_completed_at=upload_completed_at,
    )


def _install_r2_fake(monkeypatch: pytest.MonkeyPatch) -> _R2Fake:
    from backend.services import venue_image_service

    fake = _R2Fake()
    config = R2StorageConfig(
        account_id="synthetic-account",
        access_key_id="synthetic-access-key",
        secret_access_key="synthetic-secret",
        endpoint_url="https://r2.example.invalid",
        bucket_name="synthetic-bucket",
        upload_url_minutes=15,
        read_url_minutes=10,
        max_image_bytes=1_000_000,
        allowed_image_types=frozenset({"image/jpeg"}),
        metadata_connect_timeout_seconds=2,
        metadata_read_timeout_seconds=6,
    )

    def create_upload(*, object_key: str, content_type: str) -> R2ObjectUploadTicket:
        with fake.lock:
            fake.upload_calls.append(object_key)
            fake.properties[object_key] = R2ObjectProperties(
                content_type=content_type,
                size_bytes=1024,
                etag="provider-etag",
            )
        return R2ObjectUploadTicket(
            upload_url=f"https://upload.example.invalid/{object_key}",
            upload_headers={"Content-Type": content_type},
            object_url=f"https://object.example.invalid/{object_key}",
            expires_at=_FUTURE,
        )

    def create_read(object_key: str) -> str:
        with fake.lock:
            fake.read_calls.append(object_key)
            fake.events.append("read")
        if fake.read_error is not None:
            raise fake.read_error
        return f"https://read.example.invalid/{object_key}"

    def get_properties(object_key: str) -> R2ObjectProperties:
        with fake.lock:
            fake.metadata_calls.append(object_key)
        if fake.metadata_error is not None:
            raise fake.metadata_error
        if fake.metadata_barrier is not None:
            fake.metadata_barrier.wait(timeout=10)
        return fake.properties.get(
            object_key,
            R2ObjectProperties(
                content_type="image/jpeg",
                size_bytes=1024,
                etag="provider-etag",
            ),
        )

    monkeypatch.setattr(venue_image_service, "get_r2_storage_config", lambda: config)
    monkeypatch.setattr(venue_image_service, "create_object_upload_url", create_upload)
    monkeypatch.setattr(venue_image_service, "create_object_read_url", create_read)
    monkeypatch.setattr(venue_image_service, "get_object_properties", get_properties)
    return fake


def _setup() -> tuple[uuid.UUID, uuid.UUID]:
    with _session() as db:
        admin = _admin()
        venue = _venue()
        db.add_all([admin, venue])
        db.commit()
        return admin.id, venue.id


def _count(db: Session, model: type[object]) -> int:
    return int(db.scalar(select(func.count()).select_from(model)) or 0)


def _selected_count(db: Session, venue_id: uuid.UUID) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(VenueImage)
            .where(
                VenueImage.venue_id == venue_id,
                VenueImage.deleted_at.is_(None),
                VenueImage.image_status.in_({"pending_upload", "active"}),
            )
        )
        or 0
    )


def test_initiation_persists_exact_expiry_and_server_owned_binding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services.venue_image_service import create_venue_image_upload

    fake = _install_r2_fake(monkeypatch)
    admin_id, venue_id = _setup()

    with _session() as db:
        admin = db.get(User, admin_id)
        assert admin is not None
        response = create_venue_image_upload(
            db,
            venue_id=venue_id,
            upload_request=_upload_request(),
            current_admin=admin,
        )

    with _session() as db:
        persisted = db.get(VenueImage, response.image.id)
        actions = db.scalars(
            select(AdminAction).where(
                AdminAction.target_venue_image_id == response.image.id
            )
        ).all()

    assert persisted is not None
    assert persisted.upload_expires_at == _FUTURE
    assert persisted.upload_completed_at is None
    assert persisted.venue_id == venue_id
    assert persisted.uploaded_by_user_id == admin_id
    assert persisted.storage_object_key == response.image.storage_object_key
    assert response.expires_at == persisted.upload_expires_at
    assert response.upload_url.startswith("https://upload.example.invalid/")
    assert len(fake.upload_calls) == 1
    assert len(fake.read_calls) == 1
    assert len(actions) == 1
    assert response.upload_url not in repr(actions[0].metadata)


@pytest.mark.parametrize("venue_state", ["missing", "deleted", "inactive"])
def test_invalid_venue_rejects_before_any_signing_or_persistence(
    monkeypatch: pytest.MonkeyPatch,
    venue_state: str,
) -> None:
    from backend.services.venue_image_service import create_venue_image_upload

    fake = _install_r2_fake(monkeypatch)
    admin_id, persisted_venue_id = _setup()
    venue_id = persisted_venue_id
    if venue_state == "missing":
        venue_id = uuid.uuid4()
    else:
        with _session() as db:
            venue = db.get(Venue, persisted_venue_id)
            assert venue is not None
            if venue_state == "deleted":
                venue.deleted_at = _COMPLETED
            else:
                venue.is_active = False
            db.commit()

    with _session() as db:
        admin = db.get(User, admin_id)
        assert admin is not None
        with pytest.raises(HTTPException) as exc_info:
            create_venue_image_upload(
                db,
                venue_id=venue_id,
                upload_request=_upload_request(),
                current_admin=admin,
            )
        assert exc_info.value.status_code == 404

    with _session() as db:
        assert _count(db, VenueImage) == 0
        assert _count(db, AdminAction) == 0
    assert fake.upload_calls == []
    assert fake.read_calls == []


def test_repeated_identical_initiation_creates_distinct_server_owned_intents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services.venue_image_service import create_venue_image_upload

    fake = _install_r2_fake(monkeypatch)
    admin_id, venue_id = _setup()
    request = _upload_request()

    with _session() as db:
        admin = db.get(User, admin_id)
        assert admin is not None
        first = create_venue_image_upload(
            db,
            venue_id=venue_id,
            upload_request=request,
            current_admin=admin,
        )
        second = create_venue_image_upload(
            db,
            venue_id=venue_id,
            upload_request=request,
            current_admin=admin,
        )

    assert first.image.id != second.image.id
    assert first.image.storage_object_key != second.image.storage_object_key
    assert first.expires_at == second.expires_at == _FUTURE
    assert len(fake.upload_calls) == 2
    assert len(fake.read_calls) == 2
    with _session() as db:
        assert _count(db, VenueImage) == 2
        assert _count(db, AdminAction) == 2


@pytest.mark.parametrize("invalid_kind", ["content_type", "size"])
def test_upload_validation_success_and_client_rejection_emit_no_provider_result(
    monkeypatch: pytest.MonkeyPatch,
    invalid_kind: str,
) -> None:
    from backend.services.venue_image_service import validate_upload_request

    _install_r2_fake(monkeypatch)
    recorder = MetricsRecorder("api", "test", "venue-image-upload-validation")
    with metrics_context(recorder):
        validate_upload_request(_upload_request())
        request = (
            VenueImageUploadCreate(
                file_name="invalid.pdf",
                content_type="application/pdf",
                size_bytes=1024,
            )
            if invalid_kind == "content_type"
            else VenueImageUploadCreate(
                file_name="too-large.jpg",
                content_type="image/jpeg",
                size_bytes=1_000_001,
            )
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_upload_request(request)
        assert exc_info.value.status_code == 400

    assert recorder.snapshot().series == ()


@pytest.mark.parametrize(
    ("failure", "expected_status"),
    [
        (R2StorageConfigError("synthetic configuration failure"), 503),
        (R2StorageError("synthetic signing failure"), 502),
    ],
)
def test_upload_ticket_failure_leaves_no_intent_or_success_audit(
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
    expected_status: int,
) -> None:
    from backend.services import venue_image_service

    fake = _install_r2_fake(monkeypatch)
    monkeypatch.setattr(
        venue_image_service,
        "create_object_upload_url",
        lambda **kwargs: (_ for _ in ()).throw(failure),
    )
    admin_id, venue_id = _setup()

    with _session() as db:
        admin = db.get(User, admin_id)
        assert admin is not None
        with pytest.raises(HTTPException) as exc_info:
            venue_image_service.create_venue_image_upload(
                db,
                venue_id=venue_id,
                upload_request=_upload_request(),
                current_admin=admin,
            )
        assert exc_info.value.status_code == expected_status

    with _session() as db:
        assert _count(db, VenueImage) == 0
        assert _count(db, AdminAction) == 0
    assert fake.read_calls == []


def test_upload_validation_configuration_failure_precedes_signing_and_persistence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from unittest.mock import Mock

    from backend.services import venue_image_service

    signer = Mock(side_effect=AssertionError("upload signer must not be called"))
    monkeypatch.setattr(
        venue_image_service,
        "get_r2_storage_config",
        Mock(side_effect=R2StorageConfigError("synthetic configuration failure")),
    )
    monkeypatch.setattr(venue_image_service, "create_object_upload_url", signer)
    admin_id, venue_id = _setup()

    with _session() as db:
        admin = db.get(User, admin_id)
        assert admin is not None
        with pytest.raises(HTTPException) as exc_info:
            venue_image_service.create_venue_image_upload(
                db,
                venue_id=venue_id,
                upload_request=_upload_request(),
                current_admin=admin,
            )
        assert exc_info.value.status_code == 503

    signer.assert_not_called()
    with _session() as db:
        assert _count(db, VenueImage) == 0
        assert _count(db, AdminAction) == 0


@pytest.mark.parametrize(
    "malformed_url",
    [
        pytest.param(
            "https://foo|bar.example.invalid/object",
            id="invalid-dns-authority",
        ),
        pytest.param(
            "https://999.999.999.999/object",
            id="invalid-ipv4-authority",
        ),
    ],
)
def test_malformed_upload_url_leaves_no_intent_or_success_audit(
    monkeypatch: pytest.MonkeyPatch,
    malformed_url: str,
) -> None:
    from backend.services import r2_storage_service, venue_image_service

    _install_r2_fake(monkeypatch)
    config = venue_image_service.get_r2_storage_config()

    class MalformedUploadSigningClient:
        def generate_presigned_url(self, *args, **kwargs):
            return malformed_url

    monkeypatch.setattr(r2_storage_service, "get_r2_storage_config", lambda: config)
    monkeypatch.setattr(
        r2_storage_service,
        "get_r2_client",
        lambda config: MalformedUploadSigningClient(),
    )
    monkeypatch.setattr(
        venue_image_service,
        "create_object_upload_url",
        r2_storage_service.create_object_upload_url,
    )
    admin_id, venue_id = _setup()

    with _session() as db:
        admin = db.get(User, admin_id)
        assert admin is not None
        with pytest.raises(HTTPException) as exc_info:
            venue_image_service.create_venue_image_upload(
                db,
                venue_id=venue_id,
                upload_request=_upload_request(),
                current_admin=admin,
            )
        assert exc_info.value.status_code == 502

    with _session() as db:
        assert _count(db, VenueImage) == 0
        assert _count(db, AdminAction) == 0


@pytest.mark.parametrize(
    ("expiry", "completed_at"),
    [
        (None, None),
        (_FUTURE, _COMPLETED),
    ],
)
def test_pending_intent_database_constraint_rejects_invalid_rows(
    expiry: datetime | None,
    completed_at: datetime | None,
) -> None:
    admin_id, venue_id = _setup()
    invalid = _image(
        venue_id,
        admin_id,
        image_status="pending_upload",
        index=1,
        upload_expires_at=expiry,
        upload_completed_at=completed_at,
    )

    with _session() as db:
        db.add(invalid)
        with pytest.raises(IntegrityError) as exc_info:
            db.commit()
        db.rollback()
        assert "ck_venue_images_pending_upload_intent" in str(exc_info.value.orig)
        assert db.get(VenueImage, invalid.id) is None


def test_non_pending_rows_may_keep_null_expiry() -> None:
    admin_id, venue_id = _setup()
    image = _image(
        venue_id,
        admin_id,
        image_status="active",
        index=1,
        upload_completed_at=_COMPLETED,
    )

    with _session() as db:
        db.add(image)
        db.commit()
        persisted = db.get(VenueImage, image.id)
        assert persisted is not None
        assert persisted.upload_expires_at is None


@pytest.mark.parametrize(
    ("current_status", "requested_status", "expected_status"),
    [
        ("pending_upload", "pending_upload", 200),
        ("pending_upload", "active", 409),
        ("pending_upload", "hidden", 409),
        ("pending_upload", "removed", 200),
        ("active", "active", 200),
        ("active", "hidden", 200),
        ("active", "removed", 200),
        ("active", "pending_upload", 409),
        ("hidden", "hidden", 200),
        ("hidden", "active", 200),
        ("hidden", "removed", 200),
        ("hidden", "pending_upload", 409),
        ("removed", "pending_upload", 404),
        ("removed", "active", 404),
        ("removed", "hidden", 404),
        ("removed", "removed", 404),
        ("removed", None, 404),
    ],
)
def test_patch_status_transition_matrix(
    monkeypatch: pytest.MonkeyPatch,
    current_status: str,
    requested_status: str | None,
    expected_status: int,
) -> None:
    from backend.services.venue_image_service import update_venue_image

    fake = _install_r2_fake(monkeypatch)
    admin_id, venue_id = _setup()
    image = _image(
        venue_id,
        admin_id,
        image_status=current_status,
        index=1,
        upload_expires_at=_FUTURE if current_status == "pending_upload" else None,
        upload_completed_at=None if current_status == "pending_upload" else _COMPLETED,
    )
    image_id = image.id
    with _session() as db:
        db.add(image)
        db.commit()

    with _session() as db:
        admin = db.get(User, admin_id)
        assert admin is not None
        request = VenueImageUpdate(
            image_status=requested_status,
            reason="Remove invalid image." if requested_status == "removed" else None,
        )
        try:
            result = update_venue_image(
                db,
                venue_image_id=image_id,
                image_update=request,
                current_admin=admin,
            )
        except HTTPException as exc:
            assert exc.status_code == expected_status
        else:
            assert expected_status == 200
            assert result.image_status == requested_status

    with _session() as db:
        persisted = db.get(VenueImage, image_id)
        actions = db.scalars(
            select(AdminAction).where(AdminAction.target_venue_image_id == image_id)
        ).all()

    if expected_status == 200:
        assert persisted is not None
        assert persisted.image_status == requested_status
        assert len(actions) == 1
        assert len(fake.read_calls) == 1
    else:
        assert persisted is not None
        assert persisted.image_status == current_status
        assert actions == []
        assert fake.read_calls == []


def test_expired_and_replayed_completion_reject_before_metadata_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import venue_image_service

    fake = _install_r2_fake(monkeypatch)
    admin_id, venue_id = _setup()
    deadline = datetime(2035, 1, 1, tzinfo=timezone.utc)
    pending = _image(
        venue_id,
        admin_id,
        image_status="pending_upload",
        index=1,
        upload_expires_at=deadline,
    )
    active = _image(
        venue_id,
        admin_id,
        image_status="active",
        index=2,
        upload_completed_at=_COMPLETED,
    )
    hidden = _image(
        venue_id,
        admin_id,
        image_status="hidden",
        index=3,
        upload_completed_at=_COMPLETED,
    )
    with _session() as db:
        db.add_all([pending, active, hidden])
        db.commit()
        pending_id = pending.id
        active_id = active.id
        hidden_id = hidden.id

    monkeypatch.setattr(venue_image_service, "utc_now", lambda: deadline)
    for image_id in (pending_id, active_id, hidden_id):
        with _session() as db:
            admin = db.get(User, admin_id)
            assert admin is not None
            with pytest.raises(HTTPException) as exc_info:
                venue_image_service.complete_venue_image_upload(
                    db,
                    venue_image_id=image_id,
                    current_admin=admin,
                )
            assert exc_info.value.status_code == 409

    assert fake.metadata_calls == []


@pytest.mark.parametrize(
    ("deleted", "expected_status"),
    [(False, 400), (True, 404)],
)
def test_removed_and_deleted_completion_preserve_existing_boundary(
    monkeypatch: pytest.MonkeyPatch,
    deleted: bool,
    expected_status: int,
) -> None:
    from backend.services.venue_image_service import complete_venue_image_upload

    fake = _install_r2_fake(monkeypatch)
    admin_id, venue_id = _setup()
    image = _image(
        venue_id,
        admin_id,
        image_status="removed",
        index=1,
        upload_completed_at=_COMPLETED,
    )
    image.deleted_at = _COMPLETED if deleted else None
    with _session() as db:
        db.add(image)
        db.commit()
        image_id = image.id

    with _session() as db:
        admin = db.get(User, admin_id)
        assert admin is not None
        with pytest.raises(HTTPException) as exc_info:
            complete_venue_image_upload(
                db,
                venue_image_id=image_id,
                current_admin=admin,
            )
        assert exc_info.value.status_code == expected_status

    assert fake.metadata_calls == []
    assert fake.read_calls == []
    with _session() as db:
        assert _count(db, AdminAction) == 0


def test_completion_revalidates_expiry_after_metadata_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import venue_image_service

    fake = _install_r2_fake(monkeypatch)
    admin_id, venue_id = _setup()
    deadline = datetime(2035, 1, 1, tzinfo=timezone.utc)
    image = _image(
        venue_id,
        admin_id,
        image_status="pending_upload",
        index=1,
        upload_expires_at=deadline,
    )
    with _session() as db:
        db.add(image)
        db.commit()
        image_id = image.id
        object_key = image.storage_object_key

    times = iter([deadline - timedelta(seconds=1), deadline])
    monkeypatch.setattr(venue_image_service, "utc_now", lambda: next(times))
    with _session() as db:
        admin = db.get(User, admin_id)
        assert admin is not None
        with pytest.raises(HTTPException) as exc_info:
            venue_image_service.complete_venue_image_upload(
                db,
                venue_image_id=image_id,
                current_admin=admin,
            )
        assert exc_info.value.status_code == 409

    with _session() as db:
        persisted = db.get(VenueImage, image_id)
        assert persisted is not None
        assert persisted.image_status == "pending_upload"
        assert persisted.upload_completed_at is None
        assert _count(db, AdminAction) == 0
    assert fake.metadata_calls == [object_key]
    assert fake.read_calls == []


def test_successful_completion_preserves_expiry_and_applies_primary_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.services import venue_image_service

    fake = _install_r2_fake(monkeypatch)
    admin_id, venue_id = _setup()
    original_expiry = datetime(2035, 1, 1, tzinfo=timezone.utc)
    prior_primary = _image(
        venue_id,
        admin_id,
        image_status="active",
        index=1,
        is_primary=True,
        upload_completed_at=_COMPLETED,
    )
    pending = _image(
        venue_id,
        admin_id,
        image_status="pending_upload",
        index=2,
        is_primary=True,
        upload_expires_at=original_expiry,
    )
    with _session() as db:
        db.add_all([prior_primary, pending])
        db.commit()
        prior_primary_id = prior_primary.id
        pending_id = pending.id

    changed_config = R2StorageConfig(
        account_id="changed-account",
        access_key_id="changed-key",
        secret_access_key="changed-secret",
        endpoint_url="https://changed-r2.example.invalid",
        bucket_name="changed-bucket",
        upload_url_minutes=1,
        read_url_minutes=1,
        max_image_bytes=1_000_000,
        allowed_image_types=frozenset({"image/jpeg"}),
        metadata_connect_timeout_seconds=2,
        metadata_read_timeout_seconds=6,
    )
    monkeypatch.setattr(venue_image_service, "get_r2_storage_config", lambda: changed_config)
    monkeypatch.setattr(
        venue_image_service,
        "utc_now",
        lambda: original_expiry - timedelta(seconds=1),
    )

    with _session() as db:
        admin = db.get(User, admin_id)
        assert admin is not None
        result = venue_image_service.complete_venue_image_upload(
            db,
            venue_image_id=pending_id,
            current_admin=admin,
        )
        assert result.image_status == "active"

    with _session() as db:
        persisted_target = db.get(VenueImage, pending_id)
        persisted_prior = db.get(VenueImage, prior_primary_id)
        assert persisted_target is not None
        assert persisted_prior is not None
        assert persisted_target.upload_expires_at == original_expiry
        assert persisted_target.upload_completed_at == original_expiry - timedelta(
            seconds=1
        )
        assert persisted_target.is_primary is True
        assert persisted_prior.is_primary is False
        active_primary_count = int(
            db.scalar(
                select(func.count())
                .select_from(VenueImage)
                .where(
                    VenueImage.venue_id == venue_id,
                    VenueImage.image_status == "active",
                    VenueImage.is_primary.is_(True),
                    VenueImage.deleted_at.is_(None),
                )
            )
            or 0
        )
        assert active_primary_count == 1
        assert _count(db, AdminAction) == 1
    assert len(fake.metadata_calls) == 1
    assert len(fake.read_calls) == 1


@pytest.mark.parametrize(
    ("content_type", "size_bytes", "expected_status"),
    [
        (None, 1024, 200),
        ("image/png", 1024, 400),
        ("image/jpeg", 1025, 400),
    ],
)
def test_completion_metadata_checks_preserve_pending_state_on_rejection(
    monkeypatch: pytest.MonkeyPatch,
    content_type: str | None,
    size_bytes: int,
    expected_status: int,
) -> None:
    from backend.services.venue_image_service import complete_venue_image_upload

    fake = _install_r2_fake(monkeypatch)
    admin_id, venue_id = _setup()
    image = _image(
        venue_id,
        admin_id,
        image_status="pending_upload",
        index=1,
        upload_expires_at=_FUTURE,
    )
    fake.properties[image.storage_object_key] = R2ObjectProperties(
        content_type=content_type,
        size_bytes=size_bytes,
        etag="metadata-etag",
    )
    with _session() as db:
        db.add(image)
        db.commit()
        image_id = image.id

    with _session() as db:
        admin = db.get(User, admin_id)
        assert admin is not None
        try:
            result = complete_venue_image_upload(
                db,
                venue_image_id=image_id,
                current_admin=admin,
            )
        except HTTPException as exc:
            assert exc.status_code == expected_status
        else:
            assert expected_status == 200
            assert result.image_status == "active"

    with _session() as db:
        persisted = db.get(VenueImage, image_id)
        assert persisted is not None
        if expected_status == 200:
            assert persisted.image_status == "active"
            assert persisted.upload_completed_at is not None
            assert _count(db, AdminAction) == 1
        else:
            assert persisted.image_status == "pending_upload"
            assert persisted.upload_completed_at is None
            assert persisted.upload_expires_at == _FUTURE
            assert _count(db, AdminAction) == 0


@pytest.mark.parametrize(
    ("failure", "expected_status"),
    [
        (R2ObjectNotFoundError("synthetic missing object"), 400),
        (R2StorageConfigError("synthetic configuration failure"), 503),
        (R2StorageError("synthetic provider failure"), 502),
        (
            DependencyReadTimeoutError(
                provider_kind="r2",
                operation="r2.metadata.head",
            ),
            None,
        ),
        (asyncio.CancelledError(), None),
    ],
)
def test_metadata_failure_or_cancellation_leaves_intent_unconsumed(
    monkeypatch: pytest.MonkeyPatch,
    failure: BaseException,
    expected_status: int | None,
) -> None:
    from backend.services.venue_image_service import complete_venue_image_upload

    fake = _install_r2_fake(monkeypatch)
    fake.metadata_error = failure
    admin_id, venue_id = _setup()
    prior_primary = _image(
        venue_id,
        admin_id,
        image_status="active",
        index=1,
        is_primary=True,
        upload_completed_at=_COMPLETED,
    )
    pending = _image(
        venue_id,
        admin_id,
        image_status="pending_upload",
        index=2,
        is_primary=True,
        upload_expires_at=_FUTURE,
    )
    with _session() as db:
        db.add_all([prior_primary, pending])
        db.commit()
        prior_primary_id = prior_primary.id
        pending_id = pending.id

    with _session() as db:
        admin = db.get(User, admin_id)
        assert admin is not None
        if expected_status is None:
            with pytest.raises(type(failure)) as exc_info:
                complete_venue_image_upload(
                    db,
                    venue_image_id=pending_id,
                    current_admin=admin,
                )
            assert exc_info.value is failure
        else:
            with pytest.raises(HTTPException) as exc_info:
                complete_venue_image_upload(
                    db,
                    venue_image_id=pending_id,
                    current_admin=admin,
                )
            assert exc_info.value.status_code == expected_status

    with _session() as db:
        persisted_pending = db.get(VenueImage, pending_id)
        persisted_primary = db.get(VenueImage, prior_primary_id)
        assert persisted_pending is not None
        assert persisted_primary is not None
        assert persisted_pending.image_status == "pending_upload"
        assert persisted_pending.upload_completed_at is None
        assert persisted_pending.upload_expires_at == _FUTURE
        assert persisted_pending.is_primary is True
        assert persisted_primary.is_primary is True
        assert _count(db, AdminAction) == 0
    assert fake.read_calls == []


@pytest.mark.parametrize("workflow", ["initiation", "completion", "patch"])
@pytest.mark.parametrize(
    ("failure_kind", "expected_status", "malformed_url"),
    [
        ("configuration", 503, None),
        ("provider", 502, None),
        (
            "malformed_dns_authority",
            502,
            "https://foo|bar.example.invalid/object",
        ),
        (
            "malformed_ipv4_authority",
            502,
            "https://999.999.999.999/object",
        ),
        ("cancellation", None, None),
    ],
)
def test_read_url_failure_rolls_back_mutation_unit(
    monkeypatch: pytest.MonkeyPatch,
    workflow: str,
    failure_kind: str,
    expected_status: int | None,
    malformed_url: str | None,
) -> None:
    from backend.services import r2_storage_service, venue_image_service
    from backend.services.venue_image_service import (
        complete_venue_image_upload,
        create_venue_image_upload,
        update_venue_image,
    )

    fake = _install_r2_fake(monkeypatch)
    if failure_kind == "configuration":
        fake.read_error = R2StorageConfigError("synthetic read configuration failure")
    elif failure_kind == "provider":
        fake.read_error = R2StorageError("synthetic read signing failure")
    elif failure_kind == "cancellation":
        fake.read_error = asyncio.CancelledError()
    else:
        config = venue_image_service.get_r2_storage_config()
        assert malformed_url is not None

        class MalformedReadSigningClient:
            def generate_presigned_url(self, *args, **kwargs):
                return malformed_url

        monkeypatch.setattr(r2_storage_service, "get_r2_storage_config", lambda: config)
        monkeypatch.setattr(
            r2_storage_service,
            "get_r2_client",
            lambda config: MalformedReadSigningClient(),
        )
        monkeypatch.setattr(
            venue_image_service,
            "create_object_read_url",
            r2_storage_service.create_object_read_url,
        )
    admin_id, venue_id = _setup()

    if workflow == "initiation":
        with _session() as db:
            admin = db.get(User, admin_id)
            assert admin is not None
            if expected_status is None:
                with pytest.raises(asyncio.CancelledError):
                    create_venue_image_upload(
                        db,
                        venue_id=venue_id,
                        upload_request=_upload_request(),
                        current_admin=admin,
                    )
            else:
                with pytest.raises(HTTPException) as exc_info:
                    create_venue_image_upload(
                        db,
                        venue_id=venue_id,
                        upload_request=_upload_request(),
                        current_admin=admin,
                    )
                assert exc_info.value.status_code == expected_status
        with _session() as db:
            assert _count(db, VenueImage) == 0
            assert _count(db, AdminAction) == 0
        return

    image_status = "pending_upload" if workflow == "completion" else "active"
    prior_primary = _image(
        venue_id,
        admin_id,
        image_status="active",
        index=1,
        is_primary=workflow == "completion",
        upload_completed_at=_COMPLETED,
    )
    target = _image(
        venue_id,
        admin_id,
        image_status=image_status,
        index=2,
        is_primary=workflow == "completion",
        upload_expires_at=_FUTURE if workflow == "completion" else None,
        upload_completed_at=None if workflow == "completion" else _COMPLETED,
    )
    target.alt_text = "Before"
    with _session() as db:
        if workflow == "completion":
            prior_primary.is_primary = True
        db.add_all([prior_primary, target])
        db.commit()
        prior_primary_id = prior_primary.id
        target_id = target.id

    with _session() as db:
        admin = db.get(User, admin_id)
        assert admin is not None
        def mutate() -> None:
            if workflow == "completion":
                complete_venue_image_upload(
                    db,
                    venue_image_id=target_id,
                    complete_request=VenueImageCompleteUpload(etag="request-etag"),
                    current_admin=admin,
                )
            else:
                update_venue_image(
                    db,
                    venue_image_id=target_id,
                    image_update=VenueImageUpdate(alt_text="After"),
                    current_admin=admin,
                )

        if expected_status is None:
            with pytest.raises(asyncio.CancelledError):
                mutate()
        else:
            with pytest.raises(HTTPException) as exc_info:
                mutate()
            assert exc_info.value.status_code == expected_status

    with _session() as db:
        persisted_target = db.get(VenueImage, target_id)
        persisted_primary = db.get(VenueImage, prior_primary_id)
        assert persisted_target is not None
        assert persisted_primary is not None
        assert _count(db, AdminAction) == 0
        if workflow == "completion":
            assert persisted_target.image_status == "pending_upload"
            assert persisted_target.upload_completed_at is None
            assert persisted_target.is_primary is True
            assert persisted_primary.is_primary is True
        else:
            assert persisted_target.alt_text == "Before"


@pytest.mark.parametrize("workflow", ["initiation", "completion", "patch"])
def test_successful_mutation_signs_read_url_once_before_commit(
    monkeypatch: pytest.MonkeyPatch,
    workflow: str,
) -> None:
    from backend.services.venue_image_service import (
        complete_venue_image_upload,
        create_venue_image_upload,
        update_venue_image,
    )

    fake = _install_r2_fake(monkeypatch)
    admin_id, venue_id = _setup()
    target_id: uuid.UUID | None = None
    if workflow != "initiation":
        target = _image(
            venue_id,
            admin_id,
            image_status="pending_upload" if workflow == "completion" else "active",
            index=1,
            upload_expires_at=_FUTURE if workflow == "completion" else None,
            upload_completed_at=None if workflow == "completion" else _COMPLETED,
        )
        target_id = target.id
        with _session() as db:
            db.add(target)
            db.commit()

    with _session() as db:
        admin = db.get(User, admin_id)
        assert admin is not None
        original_commit = db.commit

        def tracked_commit() -> None:
            fake.events.append("commit")
            original_commit()

        monkeypatch.setattr(db, "commit", tracked_commit)
        if workflow == "initiation":
            create_venue_image_upload(
                db,
                venue_id=venue_id,
                upload_request=_upload_request(),
                current_admin=admin,
            )
        elif workflow == "completion":
            assert target_id is not None
            complete_venue_image_upload(
                db,
                venue_image_id=target_id,
                current_admin=admin,
            )
        else:
            assert target_id is not None
            update_venue_image(
                db,
                venue_image_id=target_id,
                image_update=VenueImageUpdate(alt_text="After"),
                current_admin=admin,
            )

    assert fake.events == ["read", "commit"]
    assert len(fake.read_calls) == 1


def _complete(
    image_id: uuid.UUID,
    admin_id: uuid.UUID,
) -> str:
    from backend.services.venue_image_service import complete_venue_image_upload

    with _session() as db:
        admin = db.get(User, admin_id)
        assert admin is not None
        try:
            complete_venue_image_upload(
                db,
                venue_image_id=image_id,
                current_admin=admin,
            )
            return "completed"
        except HTTPException as exc:
            return f"http-{exc.status_code}"


def test_concurrent_completion_consumes_intent_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _install_r2_fake(monkeypatch)
    fake.metadata_barrier = Barrier(2)
    admin_id, venue_id = _setup()
    image = _image(
        venue_id,
        admin_id,
        image_status="pending_upload",
        index=1,
        is_primary=True,
        upload_expires_at=_FUTURE,
    )
    prior_primary = _image(
        venue_id,
        admin_id,
        image_status="active",
        index=2,
        is_primary=True,
        upload_completed_at=_COMPLETED,
    )
    with _session() as db:
        db.add_all([image, prior_primary])
        db.commit()
        image_id = image.id
        prior_primary_id = prior_primary.id

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(_complete, image_id, admin_id) for _ in range(2)]
        results = sorted(future.result(timeout=20) for future in futures)

    with _session() as db:
        persisted = db.get(VenueImage, image_id)
        actions = db.scalars(
            select(AdminAction).where(AdminAction.target_venue_image_id == image_id)
        ).all()
        assert persisted is not None
        assert persisted.image_status == "active"
        assert persisted.upload_completed_at is not None
        assert persisted.upload_expires_at == _FUTURE
        assert persisted.is_primary is True
        prior = db.get(VenueImage, prior_primary_id)
        assert prior is not None
        assert prior.is_primary is False
        assert (
            int(
                db.scalar(
                    select(func.count())
                    .select_from(VenueImage)
                    .where(
                        VenueImage.venue_id == venue_id,
                        VenueImage.image_status == "active",
                        VenueImage.is_primary.is_(True),
                        VenueImage.deleted_at.is_(None),
                    )
                )
                or 0
            )
            == 1
        )
        assert len(actions) == 1
    assert results == ["completed", "http-409"]
    assert len(fake.metadata_calls) == 2
    assert len(fake.read_calls) == 1


@pytest.mark.parametrize(
    ("selected_count", "expected_status"),
    [(2, 200), (3, 400)],
)
def test_non_racing_hidden_reactivation_obeys_selected_capacity(
    monkeypatch: pytest.MonkeyPatch,
    selected_count: int,
    expected_status: int,
) -> None:
    from backend.services.venue_image_service import update_venue_image

    fake = _install_r2_fake(monkeypatch)
    admin_id, venue_id = _setup()
    selected = [
        _image(
            venue_id,
            admin_id,
            image_status="active",
            index=index,
            upload_completed_at=_COMPLETED,
        )
        for index in range(selected_count)
    ]
    hidden = _image(
        venue_id,
        admin_id,
        image_status="hidden",
        index=4,
        upload_completed_at=_COMPLETED,
    )
    with _session() as db:
        db.add_all([*selected, hidden])
        db.commit()
        hidden_id = hidden.id

    with _session() as db:
        admin = db.get(User, admin_id)
        assert admin is not None
        try:
            result = update_venue_image(
                db,
                venue_image_id=hidden_id,
                image_update=VenueImageUpdate(image_status="active"),
                current_admin=admin,
            )
        except HTTPException as exc:
            assert exc.status_code == expected_status
        else:
            assert expected_status == 200
            assert result.image_status == "active"

    with _session() as db:
        persisted = db.get(VenueImage, hidden_id)
        assert persisted is not None
        if expected_status == 200:
            assert persisted.image_status == "active"
            assert _selected_count(db, venue_id) == 3
            assert _count(db, AdminAction) == 1
            assert len(fake.read_calls) == 1
        else:
            assert persisted.image_status == "hidden"
            assert _selected_count(db, venue_id) == 3
            assert _count(db, AdminAction) == 0
            assert fake.read_calls == []


def _initiate(
    venue_id: uuid.UUID,
    admin_id: uuid.UUID,
    barrier: Barrier,
    index: int,
) -> str:
    from backend.services.venue_image_service import create_venue_image_upload

    with _session() as db:
        admin = db.get(User, admin_id)
        assert admin is not None
        barrier.wait(timeout=10)
        try:
            create_venue_image_upload(
                db,
                venue_id=venue_id,
                upload_request=_upload_request(index),
                current_admin=admin,
            )
            return "created"
        except HTTPException as exc:
            return f"http-{exc.status_code}"


def _reactivate(
    image_id: uuid.UUID,
    admin_id: uuid.UUID,
    barrier: Barrier,
) -> str:
    from backend.services.venue_image_service import update_venue_image

    with _session() as db:
        admin = db.get(User, admin_id)
        assert admin is not None
        barrier.wait(timeout=10)
        try:
            update_venue_image(
                db,
                venue_image_id=image_id,
                image_update=VenueImageUpdate(image_status="active"),
                current_admin=admin,
            )
            return "reactivated"
        except HTTPException as exc:
            return f"http-{exc.status_code}"


@pytest.mark.parametrize(
    "pairing",
    ["initiation-initiation", "reactivation-reactivation", "mixed"],
)
def test_selected_capacity_producers_serialize_on_venue(
    monkeypatch: pytest.MonkeyPatch,
    pairing: str,
) -> None:
    fake = _install_r2_fake(monkeypatch)
    admin_id, venue_id = _setup()
    selected = [
        _image(
            venue_id,
            admin_id,
            image_status="active",
            index=index,
            upload_completed_at=_COMPLETED,
        )
        for index in (1, 2)
    ]
    hidden = [
        _image(
            venue_id,
            admin_id,
            image_status="hidden",
            index=index,
            upload_completed_at=_COMPLETED,
        )
        for index in (3, 4)
    ]
    with _session() as db:
        db.add_all([*selected, *hidden])
        db.commit()
        hidden_ids = [image.id for image in hidden]

    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        if pairing == "initiation-initiation":
            futures = [
                executor.submit(_initiate, venue_id, admin_id, barrier, index)
                for index in (1, 2)
            ]
        elif pairing == "reactivation-reactivation":
            futures = [
                executor.submit(_reactivate, image_id, admin_id, barrier)
                for image_id in hidden_ids
            ]
        else:
            futures = [
                executor.submit(_initiate, venue_id, admin_id, barrier, 1),
                executor.submit(_reactivate, hidden_ids[0], admin_id, barrier),
            ]
        results = sorted(future.result(timeout=20) for future in futures)

    with _session() as db:
        assert _selected_count(db, venue_id) == 3
        assert _count(db, AdminAction) == 1
        assert _count(db, VenueImage) == 4 + int("created" in results)
        hidden_statuses = {
            image_id: db.get(VenueImage, image_id).image_status
            for image_id in hidden_ids
        }

    assert sum(result in {"created", "reactivated"} for result in results) == 1
    assert results.count("http-400") == 1
    assert len(fake.read_calls) == 1
    assert len(fake.upload_calls) == (
        1
        if pairing == "initiation-initiation"
        else int(results[0] == "created" or results[1] == "created")
    )
    if pairing == "initiation-initiation" or "created" in results:
        assert set(hidden_statuses.values()) == {"hidden"}
    else:
        assert sorted(hidden_statuses.values()) == ["active", "hidden"]
