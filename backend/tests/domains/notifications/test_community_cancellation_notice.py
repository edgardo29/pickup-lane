"""Community-game cancellation notices sent to registered players."""

from datetime import date, timedelta

from sqlalchemy import select

from backend.models import Notification
from backend.tests.factories import make_booking, make_game, make_participant, make_user


def ready_player(db, **overrides):
    return make_user(db, date_of_birth=date(1990, 1, 1), **overrides)


def test_staff_cancellation_of_suspended_host_game_uses_community_notice(
    clock, db, client, firebase
):
    """Game Details §4.5: a community-game cancellation notice states that
    payment disputes and refunds stay with the original organizer, including
    when staff cancel a suspended host's game."""
    host = ready_player(db, hosting_status="eligible", account_status="suspended")
    admin = ready_player(db, role="admin")
    game = make_game(
        db, game_type="community", host=host, starts_at=clock.now + timedelta(days=2)
    )
    make_participant(db, game=game, user=host, participant_type="host")
    player = ready_player(db)
    make_booking(db, game=game, buyer=player)
    make_participant(db, game=game, user=player)

    response = client.post(
        f"/admin/community-games/{game.id}/cancel",
        headers=firebase.sign_in(admin),
        json={"reason": "Host safety removal", "idempotency_key": "f16-host-removal"},
    )

    assert response.status_code == 200, response.text
    db.refresh(game)
    assert game.game_status == "cancelled"
    notice = db.scalar(
        select(Notification).where(
            Notification.user_id == player.id,
            Notification.notification_type == "game_cancelled",
        )
    )
    assert notice is not None
    assert "original organizer" in notice.body
    assert "does not process or guarantee refunds" in notice.body
