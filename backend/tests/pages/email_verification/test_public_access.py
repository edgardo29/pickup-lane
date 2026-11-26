from datetime import timedelta

import pytest

from backend.tests.factories import make_game, make_sub_post, make_user


@pytest.mark.page("F11", 8)
@pytest.mark.parametrize("signed_in", [False, True])
def test_public_games_do_not_require_verification(
    clock, db, client, firebase, signed_in
):
    user = make_user(db)
    game = make_game(db, starts_at=clock.now + timedelta(hours=1))
    headers = firebase.sign_in(user, email_verified=False) if signed_in else {}
    response = client.get(
        "/games/browse",
        params={"starts_on": game.starts_on_local.isoformat()},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert [item["id"] for item in response.json()["games"]] == [str(game.id)]
    db.refresh(user)
    assert user.email_verified_at is None


@pytest.mark.page("F11", 8)
@pytest.mark.parametrize("signed_in", [False, True])
def test_public_sub_posts_do_not_require_verification(
    clock, db, client, firebase, signed_in
):
    user = make_user(db)
    post = make_sub_post(
        db, owner=make_user(db), starts_at=clock.now + timedelta(hours=1)
    )
    headers = firebase.sign_in(user, email_verified=False) if signed_in else {}
    response = client.get(
        "/need-a-sub/posts/cards",
        params={"starts_on": post.starts_on_local.isoformat()},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert [item["id"] for item in response.json()["posts"]] == [str(post.id)]
    db.refresh(user)
    assert user.email_verified_at is None
