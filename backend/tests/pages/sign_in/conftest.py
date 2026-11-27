"""F07 accounts, real staff suspension, and unchanged commitment snapshots."""

from datetime import date, timedelta

import pytest
from sqlalchemy import select

from backend.models import (
    Booking,
    CommunityGameDetail,
    CommunityPublishAttempt,
    Game,
    GameParticipant,
    HostPublishEntitlement,
    HostPublishFee,
    Payment,
    SubPost,
    SubPostPosition,
    SubPostRequest,
    SubPostStatusHistory,
    Venue,
    WaitlistEntry,
)
from backend.tests.factories import (
    make_booking,
    make_game,
    make_participant,
    make_sub_post,
    make_sub_post_request,
    make_user,
)


def commitments(db):
    return {
        model.__name__: db.execute(select(model.__table__).order_by(model.id)).all()
        for model in (
            Booking,
            CommunityGameDetail,
            CommunityPublishAttempt,
            HostPublishEntitlement,
            HostPublishFee,
            Payment,
            SubPostStatusHistory,
            Venue,
            WaitlistEntry,
            Game,
            GameParticipant,
            SubPost,
            SubPostPosition,
            SubPostRequest,
        )
    }


def suspend(db, user):
    # Load service configuration only after pytest installs synthetic settings.
    from backend.schemas.admin_user_schema import AdminUserSuspendCreate
    from backend.services.admin_user_account_service import (
        preview_admin_user_suspension,
        suspend_admin_user,
    )

    admin = make_user(
        db,
        role="admin",
        email_verified_at=user.created_at,
        date_of_birth=date(1990, 1, 1),
    )
    preview = preview_admin_user_suspension(db, user_id=user.id)
    return suspend_admin_user(
        db,
        admin_user=admin,
        user_id=user.id,
        payload=AdminUserSuspendCreate(
            preview_token=preview.preview_token,
            reason="Private synthetic staff reason",
            idempotency_key=f"f07-suspend-{user.id}",
        ),
    )


@pytest.fixture
def suspended_commitments(clock, db):
    user = make_user(db, date_of_birth=date(1990, 1, 1))
    game = make_game(
        db, starts_at=clock.now + timedelta(days=2), price_per_player_cents=0
    )
    booking = make_booking(db, game=game, buyer=user)
    participant = make_participant(db, game=game, booking=booking, user=user)
    post = make_sub_post(
        db, owner=make_user(db), starts_at=clock.now + timedelta(days=2)
    )
    request = make_sub_post_request(db, post=post, requester=user)
    result = suspend(db, user)
    return user, game, post, result, participant, request
