from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.database import SessionLocal
from backend.models import Booking, GameParticipant, WaitlistEntry
from backend.tests.support.auth import authenticate_as
from backend.tests.support.api_helpers import (
    create_game,
    create_game_participant,
    create_venue,
)
from backend.tests.support.factories import create_user


def _count_user_booking_participant_and_waitlist_rows(
    *,
    game_id: str,
    user_id: str,
) -> tuple[int, int, int]:
    with SessionLocal() as db:
        game_uuid = UUID(game_id)
        user_uuid = UUID(user_id)
        booking_count = db.scalar(
            select(func.count())
            .select_from(Booking)
            .where(
                Booking.game_id == game_uuid,
                Booking.buyer_user_id == user_uuid,
            )
        )
        participant_count = db.scalar(
            select(func.count())
            .select_from(GameParticipant)
            .where(
                GameParticipant.game_id == game_uuid,
                GameParticipant.user_id == user_uuid,
            )
        )
        waitlist_count = db.scalar(
            select(func.count())
            .select_from(WaitlistEntry)
            .where(
                WaitlistEntry.game_id == game_uuid,
                WaitlistEntry.user_id == user_uuid,
            )
        )
    return (
        int(booking_count or 0),
        int(participant_count or 0),
        int(waitlist_count or 0),
    )


def _get_participant_status_fields(participant_id: str) -> dict[str, object]:
    with SessionLocal() as db:
        participant = db.get(GameParticipant, UUID(participant_id))
        assert participant is not None
        return {
            "participant_status": participant.participant_status,
            "cancellation_type": participant.cancellation_type,
            "attendance_status": participant.attendance_status,
            "cancelled_at": participant.cancelled_at,
        }


def test_hidden_game_join_returns_404_without_creating_booking_participant_or_waitlist(
    client: TestClient,
):
    host = create_user(client)
    joining_user = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        host_user_id=host["id"],
        public_visibility_status="hidden",
    )
    before_counts = _count_user_booking_participant_and_waitlist_rows(
        game_id=game["id"],
        user_id=joining_user["id"],
    )
    assert before_counts == (0, 0, 0)

    authenticate_as(joining_user["id"])
    response = client.post(f"/games/{game['id']}/join", json={})

    assert response.status_code == 404, response.text
    after_counts = _count_user_booking_participant_and_waitlist_rows(
        game_id=game["id"],
        user_id=joining_user["id"],
    )
    assert after_counts == (0, 0, 0)


def test_hidden_game_active_participant_can_leave_and_persists_cancelled_state(
    client: TestClient,
):
    host = create_user(client)
    player = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        host_user_id=host["id"],
        public_visibility_status="hidden",
    )
    participant = create_game_participant(client, player["id"], game["id"])

    authenticate_as(player["id"])
    response = client.post(f"/games/{game['id']}/leave", json={})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "left_game"
    assert body["participant_id"] == participant["id"]
    persisted_fields = _get_participant_status_fields(participant["id"])
    assert persisted_fields["participant_status"] == "cancelled"
    assert persisted_fields["cancellation_type"] == "on_time"
    assert persisted_fields["attendance_status"] == "not_applicable"
    assert persisted_fields["cancelled_at"] is not None


def test_hidden_game_unrelated_user_cannot_leave_and_participant_stays_active(
    client: TestClient,
):
    host = create_user(client)
    player = create_user(client)
    unrelated_user = create_user(client)
    venue = create_venue(client, host["id"])
    game = create_game(
        client,
        host["id"],
        venue,
        public_visibility_status="hidden",
    )
    participant = create_game_participant(client, player["id"], game["id"])

    authenticate_as(unrelated_user["id"])
    response = client.post(f"/games/{game['id']}/leave", json={})

    assert response.status_code == 404, response.text
    persisted_fields = _get_participant_status_fields(participant["id"])
    assert persisted_fields["participant_status"] == "confirmed"
    assert persisted_fields["cancellation_type"] == "none"
    assert persisted_fields["attendance_status"] == "unknown"
    assert persisted_fields["cancelled_at"] is None
