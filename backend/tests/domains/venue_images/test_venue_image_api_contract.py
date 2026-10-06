from __future__ import annotations

from datetime import datetime, timedelta, timezone
from io import BytesIO
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select

from backend.database import SessionLocal
from backend.models import AdminAction
from backend.observability.timeouts import (
    DatabaseTimeoutError,
    DependencyMutationTimeoutUnknownError,
    DependencyReadTimeoutError,
)
from backend.services.r2_storage_service import (
    R2DownloadedObject,
    R2ObjectNotFoundError,
    R2ObjectUploadTicket,
    R2PublishedObject,
    R2StorageConfig,
)
from backend.tests.support.application_helpers import (
    authenticate_as,
    create_user,
    create_venue,
    set_user_role,
)

pytestmark = pytest.mark.pass_provenance("WS06-02")

_CORRELATION_ID = "123e4567-e89b-42d3-a456-426614174000"


def configure_r2_test_env(monkeypatch):
    monkeypatch.setenv("R2_ACCOUNT_ID", "test-r2-account")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "test-r2-access-key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "test-r2-secret-key")
    monkeypatch.setenv("R2_BUCKET_NAME", "pickup-lane-test")
    monkeypatch.setenv(
        "R2_ENDPOINT_URL",
        "https://test-r2-account.r2.cloudflarestorage.com",
    )
    monkeypatch.setenv("R2_UPLOAD_URL_MINUTES", "15")
    monkeypatch.setenv("R2_READ_URL_MINUTES", "60")
    monkeypatch.setenv("R2_MAX_IMAGE_BYTES", "8388608")
    monkeypatch.setenv(
        "R2_ALLOWED_IMAGE_TYPES",
        "image/jpeg,image/png,image/webp",
    )


def mock_r2_storage(monkeypatch):
    configure_r2_test_env(monkeypatch)

    config = R2StorageConfig(
        account_id="test-r2-account",
        access_key_id="test-r2-access-key",
        secret_access_key="test-r2-secret-key",
        endpoint_url="https://test-r2-account.r2.cloudflarestorage.com",
        bucket_name="pickup-lane-test",
        upload_url_minutes=15,
        read_url_minutes=60,
        max_image_bytes=8388608,
        allowed_image_types=frozenset({"image/jpeg", "image/png", "image/webp"}),
        object_connect_timeout_seconds=2,
        object_read_timeout_seconds=6,
    )
    image_buffer = BytesIO()
    with Image.new("RGB", (8, 8), "navy") as source_image:
        source_image.save(image_buffer, format="JPEG")
    source_bytes = image_buffer.getvalue().ljust(1200, b"\0")

    def fake_upload_url(*, target, object_key: str, content_type: str, config=None):
        return R2ObjectUploadTicket(
            upload_url=f"https://upload.test/{object_key}?signature=upload",
            upload_headers={"Content-Type": content_type},
            object_url=f"https://object.test/{object_key}",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        )

    def fake_read_url(*, target, object_key: str, config=None):
        return f"https://read.test/{object_key}?signature=read"

    def fake_download(*, target, object_key: str, **kwargs):
        return R2DownloadedObject(
            body=source_bytes,
            content_type="image/jpeg",
            size_bytes=len(source_bytes),
            etag='"staging"',
        )

    def fake_publish(
        *, target, object_key: str, body: bytes, content_type: str, config=None
    ):
        return R2PublishedObject(etag=f"etag-{object_key.rsplit('/', maxsplit=1)[-1]}")

    def fake_delete(*, target, object_key: str, config=None):
        return None

    monkeypatch.setattr(
        "backend.services.venue_image_service.get_r2_storage_config",
        lambda: config,
    )
    monkeypatch.setattr(
        "backend.services.venue_image_service.create_object_upload_url",
        fake_upload_url,
    )
    monkeypatch.setattr(
        "backend.services.venue_image_service.create_object_read_url",
        fake_read_url,
    )
    monkeypatch.setattr(
        "backend.services.venue_image_service.download_object",
        fake_download,
    )
    monkeypatch.setattr(
        "backend.services.venue_image_service.publish_object",
        fake_publish,
    )
    monkeypatch.setattr(
        "backend.services.venue_image_service.delete_object",
        fake_delete,
    )


def create_admin_and_venue(client: TestClient) -> tuple[dict, dict]:
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    venue = create_venue(client, admin["id"])
    return admin, venue


def create_venue_image_upload(
    client: TestClient,
    venue_id: str,
    *,
    is_primary: bool = False,
    file_name: str = "field.jpg",
) -> dict:
    response = client.post(
        f"/admin/venues/{venue_id}/images/upload-url",
        json={
            "file_name": file_name,
            "content_type": "image/jpeg",
            "size_bytes": 1200,
            "image_role": "gallery",
            "is_primary": is_primary,
            "sort_order": 0,
            "alt_text": "Indoor soccer field",
            "caption": "Main field view",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def complete_venue_image_upload(client: TestClient, venue_image_id: str) -> dict:
    response = client.post(
        f"/admin/venue-images/{venue_image_id}/complete",
        json={},
    )
    assert response.status_code == 200, response.text
    return response.json()


def list_admin_actions_for_venue_image(
    venue_image_id: str,
) -> list[dict]:
    with SessionLocal() as db:
        actions = db.scalars(
            select(AdminAction)
            .where(AdminAction.target_venue_image_id == UUID(venue_image_id))
            .order_by(AdminAction.created_at, AdminAction.id)
        ).all()
        return [
            {
                "action_type": action.action_type,
                "target_venue_id": str(action.target_venue_id),
                "target_venue_image_id": str(action.target_venue_image_id),
                "reason": action.reason,
                "metadata": action.metadata_,
            }
            for action in actions
        ]


def test_admin_can_create_and_complete_venue_image_upload(
    client: TestClient,
    monkeypatch,
):
    mock_r2_storage(monkeypatch)
    admin, venue = create_admin_and_venue(client)

    authenticate_as(admin["id"])
    upload = create_venue_image_upload(client, venue["id"], is_primary=True)

    assert upload["upload_url"].startswith("https://upload.test/")
    assert upload["upload_headers"] == {"Content-Type": "image/jpeg"}
    image = upload["image"]
    assert image["venue_id"] == venue["id"]
    assert image["uploaded_by_user_id"] == admin["id"]
    assert image["image_status"] == "pending_upload"
    assert image["is_primary"] is True
    assert image["storage_provider"] == "r2"
    assert image["storage_object_key"] == (
        f"venues/{venue['id']}/staging/{image['id']}.jpg"
    )
    assert image["storage_bucket"] == "pickup-lane-test"
    assert image["storage_account_id"] == "test-r2-account"

    completed = complete_venue_image_upload(client, image["id"])

    assert completed["image_status"] == "active"
    assert completed["upload_completed_at"] is not None
    assert completed["etag"].startswith("etag-")
    assert completed["image_url"].startswith("https://read.test/")

    audit_actions = list_admin_actions_for_venue_image(image["id"])
    actions_by_type = {action["action_type"]: action for action in audit_actions}
    assert actions_by_type["create_venue_image"]["target_venue_id"] == venue["id"]
    assert actions_by_type["create_venue_image"]["target_venue_image_id"] == image["id"]
    assert actions_by_type["create_venue_image"]["metadata"] == {
        "source": "venue_image_upload_url",
        "status": "pending_upload",
        "after": {
            "image_status": "pending_upload",
            "image_role": "gallery",
            "is_primary": True,
            "sort_order": 0,
        },
    }
    assert actions_by_type["update_venue_image"]["metadata"] == {
        "source": "venue_image_upload_complete",
        "old_status": "pending_upload",
        "new_status": "active",
        "before": {
            "image_status": "pending_upload",
            "image_role": "gallery",
            "is_primary": True,
            "sort_order": 0,
        },
        "after": {
            "image_status": "active",
            "image_role": "gallery",
            "is_primary": True,
            "sort_order": 0,
        },
    }


def test_venue_images_public_list_returns_only_active_images(
    client: TestClient,
    monkeypatch,
):
    mock_r2_storage(monkeypatch)
    admin, venue = create_admin_and_venue(client)

    authenticate_as(admin["id"])
    active_upload = create_venue_image_upload(client, venue["id"], is_primary=True)
    create_venue_image_upload(client, venue["id"], file_name="pending.jpg")
    active_image = complete_venue_image_upload(client, active_upload["image"]["id"])

    response = client.get(f"/venue-images?venue_id={venue['id']}")

    assert response.status_code == 200, response.text
    images = response.json()
    assert [image["id"] for image in images] == [active_image["id"]]
    assert "image_status" not in images[0]


def test_admin_primary_venue_image_completion_clears_previous_primary(
    client: TestClient,
    monkeypatch,
):
    mock_r2_storage(monkeypatch)
    admin, venue = create_admin_and_venue(client)

    authenticate_as(admin["id"])
    first_upload = create_venue_image_upload(
        client,
        venue["id"],
        is_primary=True,
        file_name="first.jpg",
    )
    first_image = complete_venue_image_upload(client, first_upload["image"]["id"])

    second_upload = create_venue_image_upload(
        client,
        venue["id"],
        is_primary=True,
        file_name="second.jpg",
    )
    second_image = complete_venue_image_upload(client, second_upload["image"]["id"])

    response = client.get(f"/admin/venues/{venue['id']}/images")

    assert response.status_code == 200, response.text
    images_by_id = {image["id"]: image for image in response.json()}
    assert images_by_id[first_image["id"]]["is_primary"] is False
    assert images_by_id[second_image["id"]]["is_primary"] is True


def test_admin_can_hide_venue_image(client: TestClient, monkeypatch):
    mock_r2_storage(monkeypatch)
    admin, venue = create_admin_and_venue(client)

    authenticate_as(admin["id"])
    upload = create_venue_image_upload(client, venue["id"], is_primary=True)
    image = complete_venue_image_upload(client, upload["image"]["id"])

    response = client.patch(
        f"/admin/venue-images/{image['id']}",
        json={"image_status": "hidden"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["image_status"] == "hidden"
    assert response.json()["is_primary"] is False

    audit_actions = list_admin_actions_for_venue_image(image["id"])
    hide_action = next(
        action
        for action in audit_actions
        if (
            action["action_type"] == "update_venue_image"
            and action["metadata"]["source"] == "venue_image_update"
        )
    )
    assert hide_action["target_venue_id"] == venue["id"]
    assert hide_action["reason"] is None
    assert hide_action["metadata"] == {
        "source": "venue_image_update",
        "old_status": "active",
        "new_status": "hidden",
        "before": {
            "image_status": "active",
            "image_role": "gallery",
            "is_primary": True,
            "sort_order": 0,
        },
        "after": {
            "image_status": "hidden",
            "image_role": "gallery",
            "is_primary": False,
            "sort_order": 0,
        },
    }


def test_admin_can_remove_venue_image_with_audit_reason(
    client: TestClient,
    monkeypatch,
):
    mock_r2_storage(monkeypatch)
    admin, venue = create_admin_and_venue(client)

    authenticate_as(admin["id"])
    upload = create_venue_image_upload(client, venue["id"], is_primary=True)
    image = complete_venue_image_upload(client, upload["image"]["id"])

    response = client.patch(
        f"/admin/venue-images/{image['id']}",
        json={
            "image_status": "removed",
            "reason": "Duplicate venue photo.",
        },
    )

    assert response.status_code == 200, response.text
    removed_image = response.json()
    assert removed_image["image_status"] == "removed"
    assert removed_image["is_primary"] is False
    assert removed_image["deleted_at"] is not None

    audit_actions = list_admin_actions_for_venue_image(image["id"])
    remove_action = next(
        action
        for action in audit_actions
        if action["action_type"] == "remove_venue_image"
    )
    assert remove_action["target_venue_id"] == venue["id"]
    assert remove_action["reason"] == "Duplicate venue photo."
    assert remove_action["metadata"] == {
        "source": "venue_image_update",
        "old_status": "active",
        "new_status": "removed",
        "before": {
            "image_status": "active",
            "image_role": "gallery",
            "is_primary": True,
            "sort_order": 0,
        },
        "after": {
            "image_status": "removed",
            "image_role": "gallery",
            "is_primary": False,
            "sort_order": 0,
        },
    }


def test_admin_venue_image_remove_requires_reason_for_audit(
    client: TestClient,
    monkeypatch,
):
    mock_r2_storage(monkeypatch)
    admin, venue = create_admin_and_venue(client)

    authenticate_as(admin["id"])
    upload = create_venue_image_upload(client, venue["id"], is_primary=True)
    image = complete_venue_image_upload(client, upload["image"]["id"])

    response = client.patch(
        f"/admin/venue-images/{image['id']}",
        json={"image_status": "removed", "reason": "   "},
    )

    assert response.status_code == 400, response.text
    assert "remove_venue_image requires a reason" in response.text

    image_response = client.get(f"/admin/venues/{venue['id']}/images")
    assert image_response.status_code == 200, image_response.text
    image_by_id = {item["id"]: item for item in image_response.json()}
    assert image_by_id[image["id"]]["image_status"] == "active"

    audit_actions = list_admin_actions_for_venue_image(image["id"])
    assert not any(
        action["action_type"] == "remove_venue_image" for action in audit_actions
    )


def test_venue_image_upload_rejects_bad_type_and_large_file(
    client: TestClient,
    monkeypatch,
):
    mock_r2_storage(monkeypatch)
    admin, venue = create_admin_and_venue(client)

    authenticate_as(admin["id"])
    bad_type_response = client.post(
        f"/admin/venues/{venue['id']}/images/upload-url",
        json={
            "file_name": "field.gif",
            "content_type": "image/gif",
            "size_bytes": 1200,
        },
    )
    assert bad_type_response.status_code == 400, bad_type_response.text
    assert "content type" in bad_type_response.text

    large_file_response = client.post(
        f"/admin/venues/{venue['id']}/images/upload-url",
        json={
            "file_name": "field.jpg",
            "content_type": "image/jpeg",
            "size_bytes": 9000000,
        },
    )
    assert large_file_response.status_code == 400, large_file_response.text
    assert "larger" in large_file_response.text


def test_venue_image_complete_rejects_missing_object(
    client: TestClient,
    monkeypatch,
):
    mock_r2_storage(monkeypatch)
    admin, venue = create_admin_and_venue(client)

    def fake_missing_object(*, target, object_key: str, **kwargs):
        raise R2ObjectNotFoundError(f"{object_key} was not found")

    monkeypatch.setattr(
        "backend.services.venue_image_service.download_object",
        fake_missing_object,
    )

    authenticate_as(admin["id"])
    upload = create_venue_image_upload(client, venue["id"], is_primary=True)

    response = client.post(
        f"/admin/venue-images/{upload['image']['id']}/complete",
        json={},
        headers={"X-Request-ID": _CORRELATION_ID},
    )

    assert response.status_code == 400, response.text
    detail = {
        "code": "STORAGE.OBJECT_NOT_FOUND",
        "message": "Uploaded image object was not found.",
        "outcome": "not_found",
    }
    assert response.json() == {
        "detail": detail,
        "code": "STORAGE.OBJECT_NOT_FOUND",
        "message": "Uploaded image object was not found.",
        "correlation_id": _CORRELATION_ID,
    }


def test_missing_venue_image_uses_the_exact_ws06_not_found_envelope(
    client: TestClient,
) -> None:
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    authenticate_as(admin["id"])

    response = client.post(
        "/admin/venue-images/00000000-0000-4000-8000-000000000001/complete",
        json={},
        headers={"X-Request-ID": _CORRELATION_ID},
    )

    detail = {
        "code": "API.NOT_FOUND",
        "message": "Venue image not found.",
        "outcome": "not_found",
    }
    assert response.status_code == 404
    assert response.json() == {
        "detail": detail,
        "code": "API.NOT_FOUND",
        "message": "Venue image not found.",
        "correlation_id": _CORRELATION_ID,
    }


@pytest.mark.parametrize(
    ("status_code", "code", "message", "outcome"),
    [
        (400, "STORAGE.IMAGE_INVALID", "Uploaded image content is invalid.", outcome)
        for outcome in (
            "unsupported_content",
            "type_mismatch",
            "corrupt_image",
            "multi_frame",
            "resource_limit",
            "encoded_size_limit",
        )
    ]
    + [
        (
            400,
            "STORAGE.UPLOAD_MISMATCH",
            "Uploaded image metadata does not match the upload request.",
            "metadata_mismatch",
        ),
        (
            400,
            "STORAGE.OBJECT_NOT_FOUND",
            "Uploaded image object was not found.",
            "not_found",
        ),
        (
            502,
            "STORAGE.OBJECT_READ_FAILED",
            "Image storage operation failed.",
            "provider_error",
        ),
        (
            502,
            "STORAGE.OBJECT_READ_FAILED",
            "Image storage operation failed.",
            "rate_limited",
        ),
        (
            502,
            "STORAGE.PUBLICATION_FAILED",
            "Image storage operation failed.",
            "provider_error",
        ),
        (
            502,
            "STORAGE.PUBLICATION_FAILED",
            "Image storage operation failed.",
            "rate_limited",
        ),
        (
            503,
            "STORAGE.MUTATION_OUTCOME_UNKNOWN",
            "Storage mutation outcome is unknown. Check current state before retrying.",
            "unknown",
        ),
        (
            503,
            "STORAGE.TARGET_MISMATCH",
            "Stored image target does not match configured storage.",
            "configuration_error",
        ),
        (
            503,
            "STORAGE.CONFIG_UNAVAILABLE",
            "Image storage configuration is unavailable.",
            "configuration_error",
        ),
        (
            502,
            "STORAGE.READ_URL_FAILED",
            "Image read URL could not be created.",
            "provider_error",
        ),
        (
            503,
            "STORAGE.IMAGE_PROCESSOR_BUSY",
            "Image processor is busy.",
            "retry_later",
        ),
        (
            503,
            "STORAGE.IMAGE_PROCESSOR_UNAVAILABLE",
            "Image processing is unavailable.",
            "not_ready",
        ),
        (
            409,
            "STORAGE.UPLOAD_NOT_PENDING",
            "Venue image upload is no longer pending.",
            "conflict",
        ),
        (404, "API.NOT_FOUND", "Venue image was not found.", "not_found"),
        (
            503,
            "STORAGE.PERSISTENCE_FAILED",
            "Image publication state could not be saved.",
            "failed",
        ),
        (
            503,
            "API.DATABASE_COMMIT_OUTCOME_UNKNOWN",
            "Database commit outcome is unknown. Check current state before retrying.",
            "unknown",
        ),
    ],
)
def test_ws06_non_timeout_failures_use_the_exact_public_api_envelope(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
    code: str,
    message: str,
    outcome: str,
) -> None:
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    authenticate_as(admin["id"])
    detail = {"code": code, "message": message, "outcome": outcome}

    def reject_completion(*args, **kwargs):
        raise HTTPException(status_code=status_code, detail=detail)

    monkeypatch.setattr(
        "backend.routes.venue_image_routes.complete_venue_image_upload",
        reject_completion,
    )

    response = client.post(
        "/admin/venue-images/00000000-0000-4000-8000-000000000001/complete",
        json={},
        headers={"X-Request-ID": _CORRELATION_ID},
    )

    assert response.status_code == status_code
    assert response.json() == {
        "detail": detail,
        "code": code,
        "message": message,
        "correlation_id": _CORRELATION_ID,
    }
    assert response.headers["X-Request-ID"] == _CORRELATION_ID


@pytest.mark.parametrize(
    "failure",
    [
        DependencyReadTimeoutError(
            provider_kind="r2",
            operation="r2.object.download",
        ),
        DependencyMutationTimeoutUnknownError(
            provider_kind="r2",
            operation="r2.object.publish",
        ),
        DatabaseTimeoutError(),
    ],
)
def test_ws06_timeout_failures_keep_the_exact_public_timeout_envelope(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    failure,
) -> None:
    admin = create_user(client)
    set_user_role(admin["id"], "admin")
    authenticate_as(admin["id"])

    def reject_completion(*args, **kwargs):
        raise failure

    monkeypatch.setattr(
        "backend.routes.venue_image_routes.complete_venue_image_upload",
        reject_completion,
    )

    with TestClient(client.app, raise_server_exceptions=False) as public_client:
        response = public_client.post(
            "/admin/venue-images/00000000-0000-4000-8000-000000000001/complete",
            json={},
            headers={"X-Request-ID": _CORRELATION_ID},
        )

    contract = failure.contract
    assert response.status_code == contract.status_code
    assert response.json() == {
        "detail": contract.detail,
        "code": contract.code,
        "message": contract.message,
        "correlation_id": _CORRELATION_ID,
        "details": dict(contract.details),
    }
    assert response.headers["X-Request-ID"] == _CORRELATION_ID


def test_admin_venue_image_routes_reject_non_admin(
    client: TestClient,
    monkeypatch,
):
    mock_r2_storage(monkeypatch)
    admin, venue = create_admin_and_venue(client)
    user = create_user(client)

    authenticate_as(admin["id"])
    upload = create_venue_image_upload(client, venue["id"])
    image_id = upload["image"]["id"]

    authenticate_as(user["id"])
    list_response = client.get(f"/admin/venues/{venue['id']}/images")
    create_response = client.post(
        f"/admin/venues/{venue['id']}/images/upload-url",
        json={
            "file_name": "field.jpg",
            "content_type": "image/jpeg",
            "size_bytes": 1200,
        },
    )
    complete_response = client.post(f"/admin/venue-images/{image_id}/complete", json={})
    update_response = client.patch(
        f"/admin/venue-images/{image_id}",
        json={"image_status": "hidden"},
    )

    assert list_response.status_code == 403, list_response.text
    assert create_response.status_code == 403, create_response.text
    assert complete_response.status_code == 403, complete_response.text
    assert update_response.status_code == 403, update_response.text
