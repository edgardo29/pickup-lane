from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from backend.services.r2_storage_service import (
    R2ObjectNotFoundError,
    R2ObjectProperties,
    R2ObjectUploadTicket,
)
from backend.tests.helpers import (
    authenticate_as,
    create_user,
    create_venue,
    set_user_role,
)


def configure_r2_test_env(monkeypatch):
    monkeypatch.setenv("R2_ACCOUNT_ID", "test-r2-account")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "test-r2-access-key")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "test-r2-secret-key")
    monkeypatch.setenv("R2_BUCKET_NAME", "pickup-lane-dev-media")
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

    def fake_upload_url(*, object_key: str, content_type: str):
        return R2ObjectUploadTicket(
            upload_url=f"https://upload.test/{object_key}?signature=upload",
            upload_headers={"Content-Type": content_type},
            object_url=f"https://object.test/{object_key}",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        )

    def fake_read_url(object_key: str):
        return f"https://read.test/{object_key}?signature=read"

    def fake_object_properties(object_key: str):
        return R2ObjectProperties(
            content_type="image/jpeg",
            size_bytes=1200,
            etag=f"etag-{object_key.rsplit('/', maxsplit=1)[-1]}",
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
        "backend.services.venue_image_service.get_object_properties",
        fake_object_properties,
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
    client: TestClient,
    venue_image_id: str,
) -> list[dict]:
    response = client.get(f"/admin/actions?target_venue_image_id={venue_image_id}")
    assert response.status_code == 200, response.text
    return response.json()


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
        f"venues/{venue['id']}/primary-{image['id']}.jpg"
    )
    assert image["storage_bucket"] == "pickup-lane-dev-media"
    assert image["storage_account_id"] == "test-r2-account"

    completed = complete_venue_image_upload(client, image["id"])

    assert completed["image_status"] == "active"
    assert completed["upload_completed_at"] is not None
    assert completed["etag"].startswith("etag-")
    assert completed["image_url"].startswith("https://read.test/")

    audit_actions = list_admin_actions_for_venue_image(client, image["id"])
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
    assert images[0]["image_status"] == "active"


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

    audit_actions = list_admin_actions_for_venue_image(client, image["id"])
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

    audit_actions = list_admin_actions_for_venue_image(client, image["id"])
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

    audit_actions = list_admin_actions_for_venue_image(client, image["id"])
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

    def fake_missing_object_properties(object_key: str):
        raise R2ObjectNotFoundError(f"{object_key} was not found")

    monkeypatch.setattr(
        "backend.services.venue_image_service.get_object_properties",
        fake_missing_object_properties,
    )

    authenticate_as(admin["id"])
    upload = create_venue_image_upload(client, venue["id"], is_primary=True)

    response = client.post(
        f"/admin/venue-images/{upload['image']['id']}/complete",
        json={},
    )

    assert response.status_code == 400, response.text
    assert "object was not found" in response.text


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
