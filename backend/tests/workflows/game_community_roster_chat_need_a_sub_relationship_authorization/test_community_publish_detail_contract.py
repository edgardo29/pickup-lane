from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from backend.tests.workflows.game_community_roster_chat_need_a_sub_relationship_authorization.test_matrix_scope_and_dependencies_contract import (
    _Identity,
    _auth_headers,
    _community_detail,
    _game,
    _install_auth_identities,
    _recent_time,
    _session,
    _user,
    _venue,
)

pytestmark = pytest.mark.suite_type("ordinary")


def _publish_payload(label: str) -> dict[str, object]:
    starts_at = datetime.now(timezone.utc) + timedelta(days=7)
    ends_at = starts_at + timedelta(hours=1)
    return {
        "starts_at": starts_at.isoformat(),
        "ends_at": ends_at.isoformat(),
        "timezone": "America/Chicago",
        "format_label": "5v5",
        "game_player_group": "coed",
        "skill_level": "any",
        "environment_type": "outdoor",
        "total_spots": 10,
        "price_per_player_cents": 0,
        "venue": {
            "name": f"WS03C Publish Venue {label}",
            "address_line_1": f"{label} Publish Ave",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60601",
            "country_code": "US",
        },
        "payment_methods_snapshot": [],
        "game_notes": f"WS03C publish {label}",
    }


@pytest.mark.requirement("WS03-04C-R2", "WS03-04C-R6", "WS03-04C-R10")
def test_verified_host_publish_creates_host_owned_game_without_provider_attempt(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _session() as db:
        host = _user("publish-host")
        db.add(host)
        db.commit()
        host_auth_id = host.auth_user_id
        host_email = host.email
        host_id = host.id

    _install_auth_identities(
        monkeypatch,
        {
            "host-token": _Identity(
                auth_user_id=host_auth_id,
                email=host_email,
                email_verified=True,
                authenticated_at=_recent_time(),
            )
        },
    )

    published = client.post(
        "/community-games/publish",
        headers=_auth_headers("host-token"),
        json=_publish_payload("free"),
    )
    assert published.status_code == 201
    published_json = published.json()
    assert published_json["status"] == "published"
    created_game_id = published_json["game"]["id"]

    with _session() as db:
        from backend.models import (
            CommunityGameDetail,
            CommunityPublishAttempt,
            Game,
            GameParticipant,
            HostPublishFee,
            Payment,
        )

        game = db.get(Game, created_game_id)
        assert game.host_user_id == host_id
        assert game.created_by_user_id == host_id
        assert game.game_type == "community"
        assert game.payment_collection_type == "none"
        assert game.publish_status == "published"
        assert game.public_visibility_status == "visible"
        assert (
            db.scalar(
                select(func.count())
                .select_from(GameParticipant)
                .where(
                    GameParticipant.game_id == game.id,
                    GameParticipant.user_id == host_id,
                    GameParticipant.participant_type == "host",
                )
            )
            == 1
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(CommunityGameDetail)
                .where(CommunityGameDetail.game_id == game.id)
            )
            == 1
        )
        assert (
            db.scalar(
                select(func.count())
                .select_from(HostPublishFee)
                .where(
                    HostPublishFee.game_id == game.id,
                    HostPublishFee.host_user_id == host_id,
                    HostPublishFee.fee_status == "waived",
                )
            )
            == 1
        )
        assert db.scalar(select(func.count()).select_from(Payment)) == 0
        assert db.scalar(select(func.count()).select_from(CommunityPublishAttempt)) == 0


@pytest.mark.requirement("WS03-04C-R6", "WS03-04C-R9", "WS03-04C-R10")
def test_community_detail_host_edit_and_publish_attempt_status_are_owner_bound(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.models import CommunityPublishAttempt

    with _session() as db:
        host = _user("detail-host")
        other = _user("detail-other")
        venue = _venue(host.id, "detail")
        game = _game(host_user_id=host.id, venue_id=venue.id, label="detail")
        detail = _community_detail(game_id=game.id)
        attempt = CommunityPublishAttempt(
            id=uuid.uuid4(),
            host_user_id=host.id,
            payment_id=None,
            created_game_id=None,
            attempt_status="requires_payment_method",
            publish_payload=_publish_payload("attempt"),
            payment_method_id=None,
            starts_on_local=game.starts_on_local,
            amount_cents=499,
            currency="USD",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=20),
        )
        db.add_all([host, other])
        db.flush()
        db.add(venue)
        db.flush()
        db.add(game)
        db.flush()
        db.add_all([detail, attempt])
        db.commit()
        host_auth_id = host.auth_user_id
        host_email = host.email
        other_auth_id = other.auth_user_id
        other_email = other.email
        game_id = game.id
        detail_id = detail.id
        attempt_id = attempt.id

    _install_auth_identities(
        monkeypatch,
        {
            "host-token": _Identity(
                auth_user_id=host_auth_id,
                email=host_email,
                email_verified=True,
                authenticated_at=_recent_time(),
            ),
            "other-token": _Identity(
                auth_user_id=other_auth_id,
                email=other_email,
                email_verified=True,
                authenticated_at=_recent_time(),
            ),
        },
    )

    host_detail = client.get(
        f"/community-game-details/games/{game_id}/host-edit",
        headers=_auth_headers("host-token"),
    )
    assert host_detail.status_code == 200
    assert host_detail.json()["id"] == str(detail_id)
    assert (
        client.get(
            f"/community-game-details/games/{game_id}/host-edit",
            headers=_auth_headers("other-token"),
        ).status_code
        == 403
    )

    wrong_host_update = client.put(
        f"/community-game-details/games/{game_id}/host-edit",
        headers=_auth_headers("other-token"),
        json={"payment_methods_snapshot": [{"type": "cash", "value": "not allowed"}]},
    )
    assert wrong_host_update.status_code == 403
    host_update = client.put(
        f"/community-game-details/games/{game_id}/host-edit",
        headers=_auth_headers("host-token"),
        json={"payment_methods_snapshot": [{"type": "cash", "value": "field"}]},
    )
    assert host_update.status_code == 200
    assert host_update.json()["payment_methods_snapshot"] == [
        {"type": "cash", "value": "field"}
    ]

    attempt_status = client.get(
        f"/community-games/publish-attempts/{attempt_id}",
        headers=_auth_headers("host-token"),
    )
    assert attempt_status.status_code == 200
    assert attempt_status.json()["attempt_id"] == str(attempt_id)
    assert (
        client.get(
            f"/community-games/publish-attempts/{attempt_id}",
            headers=_auth_headers("other-token"),
        ).status_code
        == 403
    )

    with _session() as db:
        from backend.models import CommunityGameDetail

        stored = db.get(CommunityGameDetail, detail_id)
        assert stored.payment_methods_snapshot == [{"type": "cash", "value": "field"}]


@pytest.mark.requirement("WS03-04C-R2", "WS03-04C-R6", "WS03-04C-R10")
def test_unverified_publish_rejection_creates_no_game_payment_or_attempt(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _session() as db:
        from backend.models import CommunityPublishAttempt, Game, Payment

        unverified = _user("publish-unverified", email_verified=False)
        db.add(unverified)
        db.commit()
        unverified_auth_id = unverified.auth_user_id
        unverified_email = unverified.email
        before_games = db.scalar(select(func.count()).select_from(Game))
        before_attempts = db.scalar(select(func.count()).select_from(CommunityPublishAttempt))
        before_payments = db.scalar(select(func.count()).select_from(Payment))

    _install_auth_identities(
        monkeypatch,
        {
            "unverified-token": _Identity(
                auth_user_id=unverified_auth_id,
                email=unverified_email,
                email_verified=False,
                authenticated_at=_recent_time(),
            )
        },
    )

    rejected = client.post(
        "/community-games/publish",
        headers=_auth_headers("unverified-token"),
        json=_publish_payload("rejected"),
    )
    assert rejected.status_code == 403
    with _session() as db:
        from backend.models import CommunityPublishAttempt, Game, Payment

        assert db.scalar(select(func.count()).select_from(Game)) == before_games
        assert db.scalar(select(func.count()).select_from(CommunityPublishAttempt)) == before_attempts
        assert db.scalar(select(func.count()).select_from(Payment)) == before_payments
