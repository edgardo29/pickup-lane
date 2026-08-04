from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi.testclient import TestClient

from backend.tests.helpers import create_sub_post, create_user


def test_sub_post_positions_list_for_post(client: TestClient):
    owner = create_user(client)
    post = create_sub_post(client, owner["id"])

    response = client.get(f"/need-a-sub/posts/{post['id']}/positions")

    assert response.status_code == 200, response.text
    positions = response.json()
    assert len(positions) == 2
    assert {position["player_group"] for position in positions} == {"men", "women"}


def test_sub_post_positions_missing_post_returns_404(client: TestClient):
    response = client.get(
        "/need-a-sub/posts/00000000-0000-4000-8000-000000000000/positions"
    )

    assert response.status_code == 404, response.text


def test_sub_post_positions_hide_non_public_posts(client: TestClient):
    from backend.database import SessionLocal
    from backend.models import SubPost

    owner = create_user(client)
    post = create_sub_post(client, owner["id"])

    with SessionLocal() as db:
        db_post = db.get(SubPost, UUID(post["id"]))
        db_post.starts_at = datetime.now(UTC) - timedelta(minutes=5)
        db_post.ends_at = datetime.now(UTC) + timedelta(minutes=55)
        db_post.expires_at = db_post.starts_at
        db.commit()

    response = client.get(f"/need-a-sub/posts/{post['id']}/positions")

    assert response.status_code == 404, response.text
