from __future__ import annotations

import pytest
from sqlalchemy import func, select

from backend.tests.workflows.game_community_roster_chat_need_a_sub_relationship_authorization.test_matrix_scope_and_dependencies_contract import (
    _Identity,
    _auth_headers,
    _game,
    _install_auth_identities,
    _recent_time,
    _session,
    _user,
    _venue,
)

pytestmark = pytest.mark.suite_type("ordinary")


def _relationship_counts(db, game_id) -> dict[str, int]:
    from backend.models import (
        Booking,
        GameParticipant,
        Notification,
        Payment,
        WaitlistEntry,
    )

    return {
        "bookings": db.scalar(
            select(func.count()).select_from(Booking).where(Booking.game_id == game_id)
        )
        or 0,
        "participants": db.scalar(
            select(func.count()).select_from(GameParticipant).where(GameParticipant.game_id == game_id)
        )
        or 0,
        "waitlist_entries": db.scalar(
            select(func.count()).select_from(WaitlistEntry).where(WaitlistEntry.game_id == game_id)
        )
        or 0,
        "payments": db.scalar(
            select(func.count()).select_from(Payment).where(Payment.game_id == game_id)
        )
        or 0,
        "notifications": db.scalar(
            select(func.count()).select_from(Notification).where(Notification.related_game_id == game_id)
        )
        or 0,
    }


@pytest.mark.requirement("WS03-04C-R2", "WS03-04C-R5", "WS03-04C-R10")
def test_verified_join_persists_current_user_and_unverified_join_has_no_side_effects(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _session() as db:
        host = _user("join-host")
        player = _user("join-player")
        unverified = _user("join-unverified", email_verified=False)
        venue = _venue(host.id, "join")
        joinable_game = _game(
            host_user_id=host.id,
            venue_id=venue.id,
            label="joinable",
            total_spots=10,
        )
        rejected_game = _game(
            host_user_id=host.id,
            venue_id=venue.id,
            label="unverified",
            total_spots=10,
            starts_delta_days=31,
        )
        db.add_all([host, player, unverified])
        db.flush()
        db.add(venue)
        db.flush()
        db.add_all([joinable_game, rejected_game])
        db.commit()
        player_auth_id = player.auth_user_id
        player_email = player.email
        player_id = player.id
        unverified_auth_id = unverified.auth_user_id
        unverified_email = unverified.email
        joinable_game_id = joinable_game.id
        rejected_game_id = rejected_game.id

    _install_auth_identities(
        monkeypatch,
        {
            "player-token": _Identity(
                auth_user_id=player_auth_id,
                email=player_email,
                email_verified=True,
                authenticated_at=_recent_time(),
            ),
            "unverified-token": _Identity(
                auth_user_id=unverified_auth_id,
                email=unverified_email,
                email_verified=False,
                authenticated_at=_recent_time(),
            ),
        },
    )

    joined = client.post(
        f"/games/{joinable_game_id}/join",
        headers=_auth_headers("player-token"),
        json={"guest_count": 0},
    )
    assert joined.status_code == 201
    joined_json = joined.json()
    assert joined_json["status"] == "joined"
    assert joined_json["participant_id"]
    assert joined_json["booking_id"]

    with _session() as db:
        from backend.models import Booking, GameParticipant

        participant = db.get(GameParticipant, joined_json["participant_id"])
        booking = db.get(Booking, joined_json["booking_id"])
        assert participant.user_id == player_id
        assert participant.guest_of_user_id is None
        assert participant.participant_status == "confirmed"
        assert booking.buyer_user_id == player_id
        assert booking.booking_status == "confirmed"
        assert booking.payment_status == "not_required"
        before_rejected = _relationship_counts(db, rejected_game_id)

    rejected = client.post(
        f"/games/{rejected_game_id}/join",
        headers=_auth_headers("unverified-token"),
        json={"guest_count": 0},
    )
    assert rejected.status_code == 403
    with _session() as db:
        assert _relationship_counts(db, rejected_game_id) == before_rejected


@pytest.mark.requirement("WS03-04C-R5", "WS03-04C-R9", "WS03-04C-R10")
def test_host_guest_cancel_and_host_edit_authorization_preserve_protected_state(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _session() as db:
        host = _user("host-mut-host")
        other = _user("host-mut-other")
        venue = _venue(host.id, "host-mut")
        game = _game(
            host_user_id=host.id,
            venue_id=venue.id,
            label="host-mut",
            total_spots=10,
        )
        db.add_all([host, other])
        db.flush()
        db.add(venue)
        db.flush()
        db.add(game)
        db.commit()
        host_auth_id = host.auth_user_id
        host_email = host.email
        host_id = host.id
        other_auth_id = other.auth_user_id
        other_email = other.email
        other_id = other.id
        game_id = game.id
        original_title = game.title
        original_status = game.game_status
        original_total_spots = game.total_spots

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

    host_guest = client.post(
        f"/games/{game_id}/guests/add",
        headers=_auth_headers("host-token"),
        json={"guest_count": 1},
    )
    assert host_guest.status_code == 201
    assert host_guest.json()["added_count"] == 1

    with _session() as db:
        before_denied = _relationship_counts(db, game_id)

    denied_cancel = client.post(
        f"/games/{game_id}/cancel",
        headers=_auth_headers("other-token"),
        json={"cancel_reason": "not the host"},
    )
    assert denied_cancel.status_code == 403

    denied_edit = client.patch(
        f"/games/{game_id}/host-edit",
        headers=_auth_headers("other-token"),
        json={"game_notes": "not the host"},
    )
    assert denied_edit.status_code == 403

    allowed_edit = client.patch(
        f"/games/{game_id}/host-edit",
        headers=_auth_headers("host-token"),
        json={"total_spots": 12, "game_notes": "host-owned update"},
    )
    assert allowed_edit.status_code == 200
    assert allowed_edit.json()["total_spots"] == 12

    with _session() as db:
        from backend.models import Game, GameParticipant

        refreshed = db.get(Game, game_id)
        assert refreshed.game_status == original_status
        assert refreshed.cancelled_at is None
        assert refreshed.title == original_title
        assert refreshed.total_spots == 12
        assert refreshed.host_user_id == host_id
        assert refreshed.host_user_id != other_id
        assert _relationship_counts(db, game_id)["bookings"] == before_denied["bookings"]
        assert _relationship_counts(db, game_id)["payments"] == before_denied["payments"]
        assert (
            db.scalar(
                select(func.count())
                .select_from(GameParticipant)
                .where(GameParticipant.game_id == game_id)
            )
            == before_denied["participants"]
        )
        assert original_total_spots != refreshed.total_spots


@pytest.mark.requirement("WS03-04C-R2", "WS03-04C-R5", "WS03-04C-R10")
def test_checkout_payment_intent_rejects_before_payment_rows_for_unverified_user(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider_calls: list[str] = []

    with _session() as db:
        host = _user("checkout-host")
        unverified = _user("checkout-unverified", email_verified=False)
        venue = _venue(host.id, "checkout")
        game = _game(
            host_user_id=host.id,
            venue_id=venue.id,
            label="checkout",
            game_type="official",
            payment_collection_type="in_app",
            total_spots=10,
        )
        game.price_per_player_cents = 1500
        db.add_all([host, unverified])
        db.flush()
        db.add(venue)
        db.flush()
        db.add(game)
        db.commit()
        unverified_auth_id = unverified.auth_user_id
        unverified_email = unverified.email
        game_id = game.id
        before = _relationship_counts(db, game_id)

    from backend.services import checkout_service

    monkeypatch.setattr(checkout_service, "stripe_payments_enabled", lambda: True)
    monkeypatch.setattr(
        checkout_service,
        "create_payment_intent",
        lambda **kwargs: provider_calls.append(str(kwargs)) or None,
    )
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
        f"/checkout/games/{game_id}/payment-intent",
        headers=_auth_headers("unverified-token"),
        json={"guest_count": 0},
    )
    assert rejected.status_code == 403
    assert provider_calls == []
    with _session() as db:
        assert _relationship_counts(db, game_id) == before
