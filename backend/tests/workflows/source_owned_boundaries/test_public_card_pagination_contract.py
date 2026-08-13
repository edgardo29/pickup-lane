from __future__ import annotations

import inspect
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from urllib.parse import urlencode

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

pytestmark = pytest.mark.suite_type("ordinary")


def _user() -> User:
    from backend.models import User

    return User(
        id=uuid.uuid4(),
        auth_user_id=f"ws02-04b1-pagination-{uuid.uuid4()}",
        role="player",
        email=f"ws02-04b1-pagination-{uuid.uuid4()}@example.invalid",
        first_name="Page",
        last_name="User",
        account_status="active",
        hosting_status="eligible",
    )


def _session():
    from backend.database import SessionLocal

    return SessionLocal()


@contextmanager
def _client_overrides(client: TestClient, *, user: User, db: Session) -> Iterator[None]:
    from backend.database import get_db
    from backend.services.auth_service import require_active_user

    def override_db() -> Iterator[Session]:
        yield db

    client.app.dependency_overrides[get_db] = override_db
    client.app.dependency_overrides[require_active_user] = lambda: user
    try:
        yield
    finally:
        client.app.dependency_overrides.clear()


def _get(client: TestClient, path: str, params: dict[str, object] | None = None):
    if params and "?" in path:
        return client.get(f"{path}&{urlencode(params)}")
    return client.get(path, params=params)


@pytest.mark.requirement("WS02-04B1-R3")
@pytest.mark.parametrize(
    ("path", "needs_auth"),
    [
        ("/games/browse", False),
        ("/my-games", True),
        ("/my-games/need-a-sub", True),
        ("/need-a-sub/posts/cards?starts_on=2035-01-01", False),
    ],
)
def test_public_card_routes_default_to_40_reject_below_1_and_bound_cursor(
    client: TestClient,
    path: str,
    needs_auth: bool,
) -> None:
    with _session() as db:
        user = _user()
        db.add(user)
        db.commit()
        context = _client_overrides(client, user=user, db=db) if needs_auth else _client_overrides(client, user=user, db=db)

        with context:
            default_response = _get(client, path)
            below_min_response = _get(client, path, params={"limit": 0})
            oversized_cursor_response = _get(client, path, params={"cursor": "x" * 2001})

        assert default_response.status_code == 200
        assert default_response.json()["limit"] == 40
        assert below_min_response.status_code == 422
        assert below_min_response.json()["code"] == "API.VALIDATION_FAILED"
        assert oversized_cursor_response.status_code == 422
        assert oversized_cursor_response.json()["code"] == "API.VALIDATION_FAILED"


@pytest.mark.requirement("WS02-04B1-R3")
@pytest.mark.parametrize(
    "path",
    [
        "/games/browse",
        "/my-games",
        "/my-games/need-a-sub",
        "/need-a-sub/posts/cards?starts_on=2035-01-01",
    ],
)
def test_public_card_services_clamp_above_100_to_bounded_empty_pages(
    client: TestClient,
    path: str,
) -> None:
    with _session() as db:
        user = _user()
        db.add(user)
        db.commit()

        with _client_overrides(client, user=user, db=db):
            response = _get(client, path, params={"limit": 101})

        assert response.status_code == 200
        assert response.json()["limit"] == 100


@pytest.mark.requirement("WS02-04B1-R3")
@pytest.mark.parametrize(
    ("service_name", "decode_name"),
    [
        ("game", "decode_browse_game_card_cursor"),
        ("game", "decode_my_games_cursor"),
        ("need_a_sub", "decode_my_need_a_sub_cursor"),
        ("need_a_sub", "decode_sub_post_card_cursor"),
    ],
)
def test_public_card_malformed_cursors_raise_service_owned_400(
    service_name: str,
    decode_name: str,
) -> None:
    from backend.services import game_service, need_a_sub_post_service

    service = game_service if service_name == "game" else need_a_sub_post_service
    decode = getattr(service, decode_name)

    with pytest.raises(HTTPException) as exc_info:
        decode("not a valid cursor")

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "cursor is invalid."


@pytest.mark.requirement("WS02-04B1-R3")
def test_public_card_foreign_context_cursors_raise_service_owned_400() -> None:
    from backend.services import game_service, need_a_sub_post_service

    with pytest.raises(HTTPException) as browse_exc:
        game_service.validate_browse_game_card_cursor_context(
            {"starts_on": "2035-01-02"},
            starts_on=date(2035, 1, 1),
        )
    with pytest.raises(HTTPException) as my_games_exc:
        game_service.validate_my_games_cursor_context(
            {"domain": "other", "view": "upcoming", "sort_direction": "asc"},
            view="upcoming",
            sort_direction="asc",
        )
    with pytest.raises(HTTPException) as my_sub_exc:
        need_a_sub_post_service.validate_my_need_a_sub_cursor_context(
            {"domain": "other", "view": "upcoming", "sort_direction": "asc"},
            view="upcoming",
            sort_direction="asc",
        )
    with pytest.raises(HTTPException) as sub_cards_exc:
        need_a_sub_post_service.validate_sub_post_card_cursor_context(
            {"starts_on": "2035-01-02", "view": "all"},
            starts_on=date(2035, 1, 1),
            view="all",
        )

    assert browse_exc.value.status_code == 400
    assert my_games_exc.value.status_code == 400
    assert my_sub_exc.value.status_code == 400
    assert sub_cards_exc.value.status_code == 400


@pytest.mark.requirement("WS02-04B1-R3")
def test_public_card_sources_use_identity_tie_breakers_and_limit_plus_one() -> None:
    from backend.services import game_service, need_a_sub_post_service

    browse_source = inspect.getsource(game_service.list_browse_game_cards)
    my_games_source = inspect.getsource(game_service.list_my_game_cards)
    sub_cards_source = inspect.getsource(need_a_sub_post_service.list_sub_post_cards)
    my_sub_source = inspect.getsource(need_a_sub_post_service.list_my_need_a_sub_cards)

    for source in (browse_source, my_games_source, sub_cards_source, my_sub_source):
        assert ".limit(effective_limit + 1)" in source
        assert "[:effective_limit]" in source
        assert "has_more = len(" in source
        assert ".id.asc()" in source or ".id.desc()" in source

    assert "Game.starts_at.asc()" in browse_source
    assert "Game.created_at.asc()" in browse_source
    assert "Game.id.asc()" in browse_source
    assert "SubPost.starts_at.asc()" in sub_cards_source
    assert "SubPost.created_at.asc()" in sub_cards_source
    assert "SubPost.id.asc()" in sub_cards_source
