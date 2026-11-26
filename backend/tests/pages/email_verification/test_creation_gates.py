import uuid

import pytest
from sqlalchemy import select

from backend.models import Game, GameParticipant, SubPost, SubPostPosition
from backend.tests.factories import make_user

from .conftest import ACCOUNT_PATHS, CREATION_PATHS, publishing_state, refresh_account


@pytest.mark.page("F11", 8)
@pytest.mark.parametrize("path", CREATION_PATHS)
def test_unverified_accounts_cannot_create(
    clock, db, client, firebase, creation_payloads, path
):
    user = make_user(db, email_verified_at=clock.now, hosting_status="eligible")
    headers = firebase.sign_in(user, email_verified=False)
    before = publishing_state(db)
    response = client.post(path, json=creation_payloads[path], headers=headers)
    assert response.status_code == 403, response.text
    assert response.json()["message"] == "Verified email required."
    assert publishing_state(db) == before
    db.refresh(user)
    assert user.email_verified_at is None


@pytest.mark.page("F11", 6)
def test_one_verification_unlocks_both_creation_actions(
    clock, db, client, firebase, creation_payloads
):
    user = make_user(db)
    headers = firebase.sign_in(user, email_verified=False)
    firebase.accounts[user.auth_user_id].email_verified = True
    refreshed = refresh_account(client, "/auth/me", headers)
    assert refreshed.status_code == 200, refreshed.text
    for path in CREATION_PATHS:
        response = client.post(path, json=creation_payloads[path], headers=headers)
        assert response.status_code == 201, response.text
        body = response.json()
        if path == "/community-games/publish":
            assert body["status"] == "published"
            game = db.get(Game, uuid.UUID(body["game"]["id"]))
            assert game.host_user_id == user.id
            assert game.publish_status == "published"
            assert db.scalar(
                select(GameParticipant).where(
                    GameParticipant.game_id == game.id,
                    GameParticipant.user_id == user.id,
                )
            )
        else:
            post = db.get(SubPost, uuid.UUID(body["id"]))
            assert post.owner_user_id == user.id
            assert post.post_status == "active"
            assert db.scalar(
                select(SubPostPosition).where(SubPostPosition.sub_post_id == post.id)
            )


@pytest.mark.page("F11", 5)
@pytest.mark.parametrize("path", [*ACCOUNT_PATHS, *CREATION_PATHS])
def test_unavailable_firebase_cannot_grant_access(
    clock, db, client, firebase, creation_payloads, path
):
    user = make_user(db)
    headers = firebase.sign_in(user)
    firebase.unavailable = True
    before = publishing_state(db)
    if path in ACCOUNT_PATHS:
        response = refresh_account(client, path, headers)
    else:
        response = client.post(path, json=creation_payloads[path], headers=headers)
    assert response.status_code == 503, response.text
    db.refresh(user)
    assert user.email_verified_at is None
    assert publishing_state(db) == before


@pytest.mark.page("F11", 2)
@pytest.mark.parametrize("path", CREATION_PATHS)
@pytest.mark.parametrize(
    "account_status, expected_status",
    [("suspended", 403), ("pending_deletion", 404), ("deleted", 404)],
)
def test_verification_does_not_override_account_status(
    clock,
    db,
    client,
    firebase,
    creation_payloads,
    path,
    account_status,
    expected_status,
):
    user = make_user(
        db,
        account_status=account_status,
        deleted_at=clock.now if account_status == "deleted" else None,
        hosting_status="eligible",
        email_verified_at=clock.now,
    )
    headers = firebase.sign_in(user)
    before = publishing_state(db)
    response = client.post(path, json=creation_payloads[path], headers=headers)
    assert response.status_code == expected_status, response.text
    assert publishing_state(db) == before


@pytest.mark.page("F11", 2)
def test_verification_preserves_hosting_restriction(
    clock, db, client, firebase, creation_payloads
):
    user = make_user(db, hosting_status="restricted")
    headers = firebase.sign_in(user)
    before = publishing_state(db)
    refresh = refresh_account(client, "/auth/me", headers)
    assert refresh.status_code == 200, refresh.text
    response = client.post(
        "/community-games/publish",
        headers=headers,
        json=creation_payloads["/community-games/publish"],
    )
    assert response.status_code == 403, response.text
    assert response.json()["message"] == "Your hosting access is restricted."
    db.refresh(user)
    assert user.email_verified_at == clock.now
    assert user.hosting_status == "restricted"
    assert publishing_state(db) == before


@pytest.mark.page("F11", 2)
@pytest.mark.parametrize("path", CREATION_PATHS)
def test_verification_does_not_bypass_form_validation(
    clock, db, client, firebase, creation_payloads, path
):
    user = make_user(db)
    headers = firebase.sign_in(user)
    payload = {
        **creation_payloads[path],
        ("total_spots" if path == "/community-games/publish" else "subs_needed"): 0,
    }
    before = publishing_state(db)
    response = client.post(path, headers=headers, json=payload)
    assert response.status_code == 422, response.text
    assert publishing_state(db) == before
