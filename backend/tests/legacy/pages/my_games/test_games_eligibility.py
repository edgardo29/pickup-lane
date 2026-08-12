from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
import pytest

from backend.models import Game, GameParticipant, ParticipantStatusHistory
from backend.tests.compliance.runtime import assert_time_boundary
from backend.tests.support.constraints import constraint_values
from backend.tests.support.auth import authenticate_as
from backend.tests.support.factories import create_user


def _game_items_by_id(response: dict) -> dict[str, dict]:
    return {item["game"]["id"]: item for item in response["items"]}


def _create_cancelled_confirmed_game(
    my_games_factory,
    *,
    user_id: str,
    starts_at: datetime,
    ends_at: datetime | None = None,
    old_status: str = "confirmed",
    change_source: str = "host",
    cancellation_type: str = "host_cancelled",
    history_created_at_delta: timedelta = timedelta(),
    request_is_still_confirmed: bool = False,
    add_newer_history: bool = False,
) -> Game:
    owner = create_user(None)
    cancelled_at = datetime.now(UTC).replace(microsecond=0)
    game = my_games_factory.create_game(
        user_id=owner["id"],
        host_user_id=owner["id"],
        starts_at=starts_at,
        ends_at=ends_at,
        game_status="cancelled",
        cancelled_at=cancelled_at,
        cancellation_source="host",
    )
    if request_is_still_confirmed:
        my_games_factory.create_participant(
            game_id=game.id,
            user_id=user_id,
            participant_status="confirmed",
        )
        return game

    participant = my_games_factory.create_participant(
        game_id=game.id,
        user_id=user_id,
        participant_status="cancelled",
        cancellation_type=cancellation_type,
        cancelled_at=cancelled_at,
    )
    my_games_factory.create_participant_history(
        participant_id=participant.id,
        old_status=old_status,
        new_status="cancelled",
        change_source=change_source,
        created_at=cancelled_at + history_created_at_delta,
    )
    if add_newer_history:
        my_games_factory.create_participant_history(
            participant_id=participant.id,
            old_status="pending_payment",
            new_status="cancelled",
            change_source="host",
            created_at=cancelled_at + timedelta(minutes=1),
        )

    return game


def test_games_status_matrices_cover_authoritative_model_values():
    all_participant_statuses = constraint_values(
        GameParticipant,
        "ck_game_participants_participant_status",
    )
    qualifying_participant_statuses = {"confirmed"}
    stale_or_excluded_participant_statuses = {
        "pending_payment",
        "waitlisted",
        "cancelled",
        "late_cancelled",
        "removed",
        "refunded",
    }
    assert qualifying_participant_statuses.isdisjoint(
        stale_or_excluded_participant_statuses
    )
    assert (
        qualifying_participant_statuses | stale_or_excluded_participant_statuses
    ) == all_participant_statuses

    all_cancellation_types = constraint_values(
        GameParticipant,
        "ck_game_participants_cancellation_type",
    )
    qualifying_cancellation_types = {"host_cancelled", "admin_cancelled"}
    rejected_cancellation_types = {
        "none",
        "on_time",
        "late",
        "payment_failed",
    }
    assert qualifying_cancellation_types.isdisjoint(rejected_cancellation_types)
    assert qualifying_cancellation_types | rejected_cancellation_types == (
        all_cancellation_types
    )

    all_history_change_sources = constraint_values(
        ParticipantStatusHistory,
        "ck_participant_status_history_change_source",
    )
    qualifying_change_sources = {"host", "admin"}
    rejected_change_sources = {
        "user",
        "system",
        "payment_webhook",
        "scheduled_job",
    }
    assert qualifying_change_sources.isdisjoint(rejected_change_sources)
    assert qualifying_change_sources | rejected_change_sources == (
        all_history_change_sources
    )


def test_games_upcoming_includes_host_and_confirmed_only(
    client: TestClient,
    my_games_factory,
):
    user = create_user(client)
    other_host = create_user(client)
    now = datetime.now(UTC).replace(microsecond=0)
    future = now + timedelta(days=7)
    hosted = my_games_factory.create_game(
        user_id=user["id"],
        starts_at=future,
        title="Hosted Upcoming",
    )
    confirmed = my_games_factory.create_game(
        user_id=other_host["id"],
        host_user_id=other_host["id"],
        starts_at=future + timedelta(days=1),
        title="Confirmed Upcoming",
    )
    my_games_factory.create_participant(
        game_id=confirmed.id,
        user_id=user["id"],
        participant_status="confirmed",
    )
    admin_added = my_games_factory.create_game(
        user_id=other_host["id"],
        host_user_id=other_host["id"],
        starts_at=future + timedelta(days=2),
        title="Admin Added Upcoming",
    )
    my_games_factory.create_participant(
        game_id=admin_added.id,
        user_id=user["id"],
        participant_status="confirmed",
        participant_type="admin_added",
        roster_order=2,
    )
    excluded_games: list[Game] = []
    for index, status in enumerate(("waitlisted", "pending_payment"), start=3):
        game = my_games_factory.create_game(
            user_id=other_host["id"],
            host_user_id=other_host["id"],
            starts_at=future + timedelta(days=index),
            title=f"Excluded {status}",
        )
        my_games_factory.create_participant(
            game_id=game.id,
            user_id=user["id"],
            participant_status=status,
        )
        excluded_games.append(game)
    created_only = my_games_factory.create_game(
        user_id=user["id"],
        host_user_id=other_host["id"],
        created_by_user_id=user["id"],
        starts_at=future + timedelta(days=6),
        title="Created Only",
    )
    guest_only = my_games_factory.create_game(
        user_id=other_host["id"],
        host_user_id=other_host["id"],
        starts_at=future + timedelta(days=7),
        title="Guest Only",
    )
    my_games_factory.create_participant(
        game_id=guest_only.id,
        user_id=None,
        participant_type="guest",
        guest_of_user_id=user["id"],
        participant_status="confirmed",
    )
    excluded_games.extend([created_only, guest_only])

    authenticate_as(user["id"])
    response = client.get("/my-games", params={"view": "upcoming"})

    assert response.status_code == 200, response.text
    items_by_id = _game_items_by_id(response.json())
    assert set(items_by_id) == {str(hosted.id), str(confirmed.id), str(admin_added.id)}
    assert items_by_id[str(hosted.id)]["status_label"] == "Hosting"
    assert items_by_id[str(hosted.id)]["status_tone"] == "hosting"
    assert items_by_id[str(confirmed.id)]["status_label"] == "Confirmed"
    assert items_by_id[str(confirmed.id)]["status_tone"] == "confirmed"
    assert items_by_id[str(admin_added.id)]["participant_status"] == "confirmed"
    assert not {str(game.id) for game in excluded_games} & set(items_by_id)


@pytest.mark.parametrize(
    ("field", "value", "should_appear"),
    [
        ("game_status", "completed", False),
        ("game_status", "expired", False),
        ("game_status", "removed", False),
        ("public_visibility_status", "hidden", True),
        ("join_enforcement_status", "paused", True),
        ("deleted_at", datetime(2026, 1, 1, tzinfo=UTC), False),
    ],
)
def test_games_upcoming_lifecycle_and_visibility_filters(
    client: TestClient,
    my_games_factory,
    field: str,
    value: object,
    should_appear: bool,
):
    user = create_user(client)
    now = datetime.now(UTC).replace(microsecond=0)
    future = now + timedelta(days=7)
    overrides = {field: value}
    if field == "game_status" and value == "completed":
        overrides["completed_at"] = now
    game = my_games_factory.create_game(
        user_id=user["id"],
        starts_at=future,
        **overrides,
    )

    authenticate_as(user["id"])
    response = client.get("/my-games", params={"view": "upcoming"})

    assert response.status_code == 200, response.text
    item_ids = {item["game"]["id"] for item in response.json()["items"]}
    assert (str(game.id) in item_ids) is should_appear


def test_games_upcoming_confirmed_hidden_and_paused_relationships_appear(
    client: TestClient,
    my_games_factory,
):
    user = create_user(client)
    other_host = create_user(client)
    now = datetime.now(UTC).replace(microsecond=0)
    future = now + timedelta(days=7)
    hidden = my_games_factory.create_game(
        user_id=other_host["id"],
        host_user_id=other_host["id"],
        starts_at=future,
        public_visibility_status="hidden",
    )
    paused = my_games_factory.create_game(
        user_id=other_host["id"],
        host_user_id=other_host["id"],
        starts_at=future + timedelta(days=1),
        join_enforcement_status="paused",
    )
    for game in (hidden, paused):
        my_games_factory.create_participant(
            game_id=game.id,
            user_id=user["id"],
            participant_status="confirmed",
        )

    authenticate_as(user["id"])
    response = client.get("/my-games", params={"view": "upcoming"})

    assert response.status_code == 200, response.text
    items_by_id = _game_items_by_id(response.json())
    assert set(items_by_id) == {str(hidden.id), str(paused.id)}
    assert items_by_id[str(hidden.id)]["status_label"] == "Confirmed"
    assert items_by_id[str(paused.id)]["status_label"] == "Confirmed"


def test_games_in_progress_stays_upcoming_until_ends_at(
    client: TestClient,
    my_games_factory,
):
    user = create_user(client)
    now = datetime.now(UTC).replace(microsecond=0)
    game = my_games_factory.create_game(
        user_id=user["id"],
        starts_at=now - timedelta(minutes=30),
        ends_at=now + timedelta(minutes=30),
    )

    authenticate_as(user["id"])
    response = client.get("/my-games", params={"view": "upcoming"})

    assert response.status_code == 200, response.text
    [item] = response.json()["items"]
    assert item["game"]["id"] == str(game.id)
    assert item["status_label"] == "Hosting"


def test_games_history_includes_recent_ended_host_and_confirmed_relationships(
    client: TestClient,
    my_games_factory,
):
    user = create_user(client)
    other_host = create_user(client)
    now = datetime.now(UTC).replace(microsecond=0)
    hosted_statuses = ["active", "completed", "expired"]
    hosted_games = [
        my_games_factory.create_game(
            user_id=user["id"],
            starts_at=now - timedelta(days=index + 3, hours=2),
            ends_at=now - timedelta(days=index + 3),
            game_status=game_status,
            title=f"Hosted History {game_status}",
        )
        for index, game_status in enumerate(hosted_statuses)
    ]
    confirmed = my_games_factory.create_game(
        user_id=other_host["id"],
        host_user_id=other_host["id"],
        starts_at=now - timedelta(days=8, hours=2),
        ends_at=now - timedelta(days=8),
        game_status="completed",
        title="Confirmed History",
    )
    my_games_factory.create_participant(
        game_id=confirmed.id,
        user_id=user["id"],
        participant_status="confirmed",
    )

    authenticate_as(user["id"])
    response = client.get("/my-games", params={"view": "history"})

    assert response.status_code == 200, response.text
    items_by_id = _game_items_by_id(response.json())
    assert {str(game.id) for game in hosted_games} | {str(confirmed.id)} == set(
        items_by_id
    )
    for game in hosted_games:
        assert items_by_id[str(game.id)]["status_label"] == "Hosted"
        assert items_by_id[str(game.id)]["status_tone"] == "hosted"
    assert items_by_id[str(confirmed.id)]["status_label"] == "Completed"
    assert items_by_id[str(confirmed.id)]["status_tone"] == "completed"


@pytest.mark.parametrize(
    "participant_status",
    [
        "waitlisted",
        "pending_payment",
        "late_cancelled",
        "removed",
        "refunded",
        "cancelled",
    ],
)
def test_games_history_excludes_non_confirmed_past_relationships(
    client: TestClient,
    my_games_factory,
    participant_status: str,
):
    user = create_user(client)
    other_host = create_user(client)
    now = datetime.now(UTC).replace(microsecond=0)
    game = my_games_factory.create_game(
        user_id=other_host["id"],
        host_user_id=other_host["id"],
        starts_at=now - timedelta(days=5, hours=2),
        ends_at=now - timedelta(days=5),
        game_status="completed",
    )
    my_games_factory.create_participant(
        game_id=game.id,
        user_id=user["id"],
        participant_status=participant_status,
        cancellation_type="on_time" if participant_status == "cancelled" else "none",
    )

    authenticate_as(user["id"])
    response = client.get("/my-games", params={"view": "history"})

    assert response.status_code == 200, response.text
    assert response.json()["items"] == []


def test_games_history_excludes_past_guest_only_relationship(
    client: TestClient,
    my_games_factory,
):
    user = create_user(client)
    other_host = create_user(client)
    now = datetime.now(UTC).replace(microsecond=0)
    game = my_games_factory.create_game(
        user_id=other_host["id"],
        host_user_id=other_host["id"],
        starts_at=now - timedelta(days=5, hours=2),
        ends_at=now - timedelta(days=5),
        game_status="completed",
    )
    my_games_factory.create_participant(
        game_id=game.id,
        user_id=None,
        participant_type="guest",
        guest_of_user_id=user["id"],
        participant_status="confirmed",
    )

    authenticate_as(user["id"])
    response = client.get("/my-games", params={"view": "history"})

    assert response.status_code == 200, response.text
    assert response.json()["items"] == []


def test_games_history_uses_host_priority_and_returns_one_card(
    client: TestClient,
    my_games_factory,
):
    user = create_user(client)
    now = datetime.now(UTC).replace(microsecond=0)
    game = my_games_factory.create_game(
        user_id=user["id"],
        starts_at=now - timedelta(days=4, hours=2),
        ends_at=now - timedelta(days=4),
        game_status="completed",
    )
    my_games_factory.create_participant(
        game_id=game.id,
        user_id=user["id"],
        participant_status="confirmed",
    )
    my_games_factory.create_participant(
        game_id=game.id,
        user_id=user["id"],
        participant_status="cancelled",
        cancellation_type="host_cancelled",
    )

    authenticate_as(user["id"])
    response = client.get("/my-games", params={"view": "history"})

    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert [item["game"]["id"] for item in items] == [str(game.id)]
    assert items[0]["is_host"] is True
    assert items[0]["status_label"] == "Hosted"


def test_games_cancelled_history_includes_host_and_confirmed_proof_only(
    client: TestClient,
    my_games_factory,
):
    user = create_user(client)
    now = datetime.now(UTC).replace(microsecond=0)
    cancelled_at = now
    hosted = my_games_factory.create_game(
        user_id=user["id"],
        starts_at=now + timedelta(days=2),
        game_status="cancelled",
        cancelled_at=cancelled_at,
    )
    confirmed = _create_cancelled_confirmed_game(
        my_games_factory,
        user_id=user["id"],
        starts_at=now + timedelta(days=3),
    )
    stale_confirmed = _create_cancelled_confirmed_game(
        my_games_factory,
        user_id=user["id"],
        starts_at=now - timedelta(days=3, hours=2),
        ends_at=now - timedelta(days=3),
        request_is_still_confirmed=True,
    )
    bad_old_status = _create_cancelled_confirmed_game(
        my_games_factory,
        user_id=user["id"],
        starts_at=now + timedelta(days=4),
        old_status="waitlisted",
    )
    bad_source = _create_cancelled_confirmed_game(
        my_games_factory,
        user_id=user["id"],
        starts_at=now + timedelta(days=5),
        change_source="user",
    )
    bad_timestamp = _create_cancelled_confirmed_game(
        my_games_factory,
        user_id=user["id"],
        starts_at=now + timedelta(days=6),
        history_created_at_delta=timedelta(minutes=1),
    )
    bad_newer_history = _create_cancelled_confirmed_game(
        my_games_factory,
        user_id=user["id"],
        starts_at=now + timedelta(days=7),
        add_newer_history=True,
    )
    bad_cancellation_type = _create_cancelled_confirmed_game(
        my_games_factory,
        user_id=user["id"],
        starts_at=now + timedelta(days=8),
        cancellation_type="payment_failed",
    )

    authenticate_as(user["id"])
    response = client.get("/my-games", params={"view": "history"})

    assert response.status_code == 200, response.text
    items_by_id = _game_items_by_id(response.json())
    assert set(items_by_id) == {str(hosted.id), str(confirmed.id)}
    assert items_by_id[str(hosted.id)]["status_label"] == "Cancelled"
    assert items_by_id[str(confirmed.id)]["status_label"] == "Cancelled"
    assert not {
        str(game.id)
        for game in (
            stale_confirmed,
            bad_old_status,
            bad_source,
            bad_timestamp,
            bad_newer_history,
            bad_cancellation_type,
        )
    } & set(items_by_id)


def test_games_exact_boundary_and_sixty_day_scheduled_history_window(
    client: TestClient,
    my_games_factory,
    freeze_my_games_now,
    backend_test_evidence,
):
    user = create_user(client)
    frozen_now = datetime(2026, 8, 10, 18, 0, tzinfo=UTC)
    freeze_my_games_now(frozen_now)
    boundary = my_games_factory.create_game(
        user_id=user["id"],
        starts_at=frozen_now - timedelta(hours=2),
        ends_at=frozen_now,
        game_status="active",
    )
    old_game = my_games_factory.create_game(
        user_id=user["id"],
        starts_at=frozen_now - timedelta(days=61, hours=2),
        ends_at=frozen_now - timedelta(days=61),
        game_status="completed",
    )
    future_cancelled = my_games_factory.create_game(
        user_id=user["id"],
        starts_at=frozen_now + timedelta(days=3),
        ends_at=frozen_now + timedelta(days=3, hours=2),
        game_status="cancelled",
        cancelled_at=frozen_now,
    )
    old_cancelled = my_games_factory.create_game(
        user_id=user["id"],
        starts_at=frozen_now - timedelta(days=61, hours=2),
        ends_at=frozen_now - timedelta(days=61),
        game_status="cancelled",
        cancelled_at=frozen_now,
    )

    authenticate_as(user["id"])
    upcoming_response = client.get("/my-games", params={"view": "upcoming"})
    history_response = client.get("/my-games", params={"view": "history"})

    assert upcoming_response.status_code == 200, upcoming_response.text
    assert history_response.status_code == 200, history_response.text
    upcoming_ids = {item["game"]["id"] for item in upcoming_response.json()["items"]}
    history_ids = {item["game"]["id"] for item in history_response.json()["items"]}
    assert_time_boundary(
        backend_test_evidence,
        time_id="TIME-GAMES-EXACT-AND-WINDOW",
        baseline=frozen_now.isoformat(),
        boundary="at_ends_at",
        actual=str(boundary.id) not in upcoming_ids and str(boundary.id) in history_ids,
        expected=True,
    )
    assert_time_boundary(
        backend_test_evidence,
        time_id="TIME-GAMES-EXACT-AND-WINDOW",
        baseline=frozen_now.isoformat(),
        boundary="sixty_day_window",
        actual=str(boundary.id) in history_ids,
        expected=True,
    )
    assert_time_boundary(
        backend_test_evidence,
        time_id="TIME-GAMES-EXACT-AND-WINDOW",
        baseline=frozen_now.isoformat(),
        boundary="older_than_sixty_days",
        actual=str(old_game.id) not in history_ids and str(old_cancelled.id) not in history_ids,
        expected=True,
    )
    assert_time_boundary(
        backend_test_evidence,
        time_id="TIME-GAMES-EXACT-AND-WINDOW",
        baseline=frozen_now.isoformat(),
        boundary="future_cancelled_immediate",
        actual=str(future_cancelled.id) in history_ids,
        expected=True,
    )
