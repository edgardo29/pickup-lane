from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.suite_type("ordinary")


def _provider_payload(
    *,
    uid: str = "firebase-user",
    email: str = "verified-policy@example.invalid",
    email_verified: bool,
) -> dict[str, object]:
    return {
        "uid": uid,
        "email": email,
        "email_verified": email_verified,
        "auth_time": 1_700_000_000,
    }


def _install_provider_identity(
    monkeypatch: pytest.MonkeyPatch,
    *,
    uid: str = "firebase-user",
    email: str = "verified-policy@example.invalid",
    email_verified: bool,
) -> None:
    import backend.services.auth_service as auth_service

    payload = _provider_payload(uid=uid, email=email, email_verified=email_verified)

    def verify_token(token: str) -> dict[str, object]:
        if token != "valid-token":
            raise ValueError("invalid synthetic token")
        return dict(payload)

    monkeypatch.setattr(auth_service, "verify_firebase_token", verify_token)


def _auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer valid-token"}


def _create_user(
    *,
    auth_user_id: str = "firebase-user",
    email: str = "verified-policy@example.invalid",
    role: str = "player",
    email_verified_at: datetime | None = None,
) -> uuid.UUID:
    from backend.database import SessionLocal
    from backend.models import User

    user = User(
        id=uuid.uuid4(),
        auth_user_id=auth_user_id,
        role=role,
        email=email,
        email_verified_at=email_verified_at,
        phone=f"+1555{uuid.uuid4().hex[:10]}",
        first_name="Verified",
        last_name="Policy",
        date_of_birth=date(1991, 2, 3),
        account_status="active",
        hosting_status="eligible",
    )
    with SessionLocal() as db:
        db.add(user)
        db.commit()
        return user.id


def _email_verified_at(user_id: uuid.UUID) -> datetime | None:
    from backend.database import SessionLocal
    from backend.models import User

    with SessionLocal() as db:
        user = db.get(User, user_id)
        assert user is not None
        return user.email_verified_at


def _community_publish_payload() -> dict[str, Any]:
    return {
        "starts_at": "2031-06-01T18:00:00Z",
        "ends_at": "2031-06-01T19:00:00Z",
        "format_label": "5v5",
        "environment_type": "outdoor",
        "total_spots": 10,
        "price_per_player_cents": 1200,
        "venue": {
            "name": "Synthetic Park",
            "address_line_1": "123 Test Ave",
            "city": "Austin",
            "state": "TX",
            "postal_code": "78701",
        },
    }


def _community_host_edit_payload(payment_value: str) -> dict[str, Any]:
    return {
        "payment_methods_snapshot": [
            {"type": "cash", "value": payment_value},
        ],
        "payment_instructions_snapshot": None,
    }


def _create_community_host_edit_state(host_user_id: uuid.UUID) -> uuid.UUID:
    from backend.database import SessionLocal
    from backend.models import CommunityGameDetail, Game, Venue

    now = datetime.now(timezone.utc).replace(microsecond=0)
    starts_at = now + timedelta(days=30)
    venue = Venue(
        id=uuid.uuid4(),
        name="Host Edit Court",
        address_line_1="42 Runtime Proof Ave",
        city="Austin",
        state="TX",
        postal_code="78701",
        country_code="US",
        venue_status="approved",
        is_active=True,
        created_by_user_id=host_user_id,
        approved_by_user_id=host_user_id,
        approved_at=now,
    )
    game = Game(
        id=uuid.uuid4(),
        game_type="community",
        payment_collection_type="external_host",
        publish_status="published",
        game_status="active",
        public_visibility_status="visible",
        join_enforcement_status="open",
        title="Host Edit Runtime Proof",
        venue_id=venue.id,
        venue_name_snapshot=venue.name,
        address_snapshot=venue.address_line_1,
        city_snapshot=venue.city,
        state_snapshot=venue.state,
        host_user_id=host_user_id,
        created_by_user_id=host_user_id,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=2),
        starts_on_local=starts_at.date(),
        timezone="UTC",
        sport_type="soccer",
        format_label="5v5",
        game_player_group="coed",
        skill_level="any",
        environment_type="outdoor",
        total_spots=10,
        price_per_player_cents=1200,
        currency="USD",
        allow_guests=True,
        max_guests_per_booking=2,
        host_guest_max=4,
        waitlist_enabled=True,
        is_chat_enabled=True,
        policy_mode="custom_hosted",
        published_at=now,
    )
    detail = CommunityGameDetail(
        id=uuid.uuid4(),
        game_id=game.id,
        payment_methods_snapshot=[
            {"type": "cash", "value": "original host payment note"},
        ],
        payment_instructions_snapshot=None,
    )
    with SessionLocal() as db:
        db.add(venue)
        db.flush()
        db.add(game)
        db.flush()
        db.add(detail)
        db.commit()
        return game.id


def _community_game_detail_state(game_id: uuid.UUID) -> dict[str, object]:
    from sqlalchemy import select

    from backend.database import SessionLocal
    from backend.models import CommunityGameDetail

    with SessionLocal() as db:
        detail = db.scalar(
            select(CommunityGameDetail).where(CommunityGameDetail.game_id == game_id)
        )
        assert detail is not None
        return {
            "payment_methods_snapshot": detail.payment_methods_snapshot,
            "payment_instructions_snapshot": detail.payment_instructions_snapshot,
        }


@pytest.mark.requirement("WS03-01-R4", "WS03-01-R5", "WS03-01-R8")
@pytest.mark.parametrize(
    ("name", "method", "path", "payload", "role"),
    [
        (
            "game join",
            "POST",
            f"/games/{uuid.uuid4()}/join",
            {"guest_count": 0},
            "player",
        ),
        (
            "checkout payment intent",
            "POST",
            f"/checkout/games/{uuid.uuid4()}/payment-intent",
            {"guest_count": 0},
            "player",
        ),
        (
            "community publish",
            "POST",
            "/community-games/publish",
            _community_publish_payload(),
            "player",
        ),
        (
            "Need-a-Sub request",
            "POST",
            f"/need-a-sub/posts/{uuid.uuid4()}/requests",
            {"sub_post_position_id": str(uuid.uuid4())},
            "player",
        ),
        (
            "game chat ensure",
            "POST",
            f"/game-chats/for-game/{uuid.uuid4()}",
            {},
            "player",
        ),
        (
            "private chat message",
            "POST",
            "/chat-messages",
            {"chat_id": str(uuid.uuid4()), "message_body": "Ready to play"},
            "player",
        ),
        ("admin entry", "GET", "/admin/me", None, "admin"),
    ],
)
def test_current_provider_unverified_state_denies_sensitive_route_families_and_clears_stale_snapshot(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None,
    role: str,
) -> None:
    del name
    _install_provider_identity(monkeypatch, email_verified=False)
    user_id = _create_user(
        role=role,
        email_verified_at=datetime.now(timezone.utc),
    )

    response = client.request(
        method,
        path,
        headers=_auth_headers(),
        json=payload,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Verified email required."
    assert _email_verified_at(user_id) is None


@pytest.mark.requirement("WS03-01-R4")
def test_current_provider_verified_host_can_update_community_game_detail_host_edit(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth_user_id = "verified-community-host"
    email = "verified-community-host@example.invalid"
    _install_provider_identity(
        monkeypatch,
        uid=auth_user_id,
        email=email,
        email_verified=True,
    )
    user_id = _create_user(
        auth_user_id=auth_user_id,
        email=email,
        email_verified_at=datetime.now(timezone.utc),
    )
    game_id = _create_community_host_edit_state(user_id)
    payload = _community_host_edit_payload("updated host payment note")

    response = client.put(
        f"/community-game-details/games/{game_id}/host-edit",
        headers=_auth_headers(),
        json=payload,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["game_id"] == str(game_id)
    assert body["payment_methods_snapshot"] == payload["payment_methods_snapshot"]
    assert _community_game_detail_state(game_id) == {
        "payment_methods_snapshot": payload["payment_methods_snapshot"],
        "payment_instructions_snapshot": None,
    }


@pytest.mark.requirement("WS03-01-R4")
def test_current_provider_unverified_state_denies_community_host_edit_and_preserves_detail(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth_user_id = "unverified-community-host"
    email = "unverified-community-host@example.invalid"
    _install_provider_identity(
        monkeypatch,
        uid=auth_user_id,
        email=email,
        email_verified=False,
    )
    user_id = _create_user(
        auth_user_id=auth_user_id,
        email=email,
        email_verified_at=datetime.now(timezone.utc),
    )
    game_id = _create_community_host_edit_state(user_id)
    before_detail = _community_game_detail_state(game_id)

    response = client.put(
        f"/community-game-details/games/{game_id}/host-edit",
        headers=_auth_headers(),
        json=_community_host_edit_payload("blocked host payment note"),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Verified email required."
    assert _email_verified_at(user_id) is None
    assert _community_game_detail_state(game_id) == before_detail


@pytest.mark.requirement("WS03-01-R4", "WS03-01-R5")
def test_current_provider_verified_state_restores_missing_snapshot_and_authorizes_admin_path(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_provider_identity(monkeypatch, email_verified=True)
    user_id = _create_user(role="admin", email_verified_at=None)

    response = client.get("/admin/me", headers=_auth_headers())

    assert response.status_code == 200
    assert response.json()["role"] == "admin"
    assert _email_verified_at(user_id) is not None


@pytest.mark.requirement("WS03-01-R4", "WS03-01-R8")
@pytest.mark.parametrize(
    "path",
    [
        "/games/browse",
        "/need-a-sub/posts",
        "/community-game-details",
    ],
)
def test_public_and_optional_auth_reads_do_not_require_verified_email(
    client: TestClient,
    path: str,
) -> None:
    response = client.get(path)

    assert response.status_code == 200


@pytest.mark.requirement("WS03-01-R4", "WS03-01-R5", "WS03-01-R8")
def test_unverified_provider_identity_can_use_bootstrap_auth_sync_without_snapshot_authority(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_provider_identity(
        monkeypatch,
        uid="bootstrap-uid",
        email="bootstrap-user@example.invalid",
        email_verified=False,
    )

    response = client.post("/auth/sync-user", headers=_auth_headers())

    assert response.status_code == 200
    assert response.json()["email"] == "bootstrap-user@example.invalid"
    assert response.json()["email_verified_at"] is None
    from backend.database import SessionLocal
    from backend.models import User

    with SessionLocal() as db:
        user = db.query(User).filter(User.auth_user_id == "bootstrap-uid").one()
        assert user.email_verified_at is None


@pytest.mark.requirement("WS03-01-R4", "WS03-01-R8")
def test_unverified_user_can_update_allowed_profile_setup_fields(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_provider_identity(monkeypatch, email_verified=False)
    user_id = _create_user(email_verified_at=None)

    response = client.patch(
        "/users/me",
        headers=_auth_headers(),
        json={"first_name": "Profile", "home_city": "Austin"},
    )

    assert response.status_code == 200
    assert response.json()["first_name"] == "Profile"
    assert response.json()["home_city"] == "Austin"
    assert _email_verified_at(user_id) is None


@pytest.mark.requirement("WS03-01-R4", "WS03-01-R8")
def test_active_user_read_and_status_surfaces_are_not_verified_mutation_gates(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_provider_identity(monkeypatch, email_verified=False)
    _create_user(email_verified_at=None)

    my_games_response = client.get("/my-games", headers=_auth_headers())
    status_response = client.get(
        f"/community-games/publish-attempts/{uuid.uuid4()}",
        headers=_auth_headers(),
    )

    assert my_games_response.status_code == 200
    assert my_games_response.json()["items"] == []
    assert status_response.status_code == 404
    assert status_response.json()["detail"] != "Verified email required."
