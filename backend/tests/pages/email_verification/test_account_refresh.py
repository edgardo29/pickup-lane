import pytest

from backend.tests.factories import make_user

from .conftest import ACCOUNT_PATHS, publishing_state, refresh_account


@pytest.mark.page("F11", 1)
@pytest.mark.parametrize("path", ACCOUNT_PATHS)
def test_refresh_persists_current_firebase_verification(
    clock, db, client, firebase, path
):
    user = make_user(db)
    headers = firebase.sign_in(user, email_verified=False)
    firebase.accounts[user.auth_user_id].email_verified = True
    response = refresh_account(client, path, headers)
    assert response.status_code == 200, response.text
    assert response.json()["id"] == str(user.id)
    assert response.json()["email_verified_at"] is not None
    db.refresh(user)
    assert user.email_verified_at == clock.now
    assert user.hosting_status == "eligible"


@pytest.mark.page("F11", 3)
@pytest.mark.parametrize("path", ACCOUNT_PATHS)
def test_current_unverified_record_clears_stale_verification(
    clock, db, client, firebase, path
):
    user = make_user(db, email_verified_at=clock.now)
    headers = firebase.sign_in(user, email_verified=True)
    firebase.accounts[user.auth_user_id].email_verified = False
    response = refresh_account(client, path, headers)
    assert response.status_code == 200, response.text
    assert response.json()["email_verified_at"] is None
    db.refresh(user)
    assert user.email_verified_at is None


@pytest.mark.page("F11", 3)
@pytest.mark.parametrize("path", ACCOUNT_PATHS)
def test_client_verification_assertion_cannot_verify_account(
    clock, db, client, firebase, path
):
    user = make_user(db)
    headers = firebase.sign_in(user, email_verified=False)
    before = publishing_state(db)
    response = refresh_account(
        client,
        path,
        headers,
        params={"email_verified": "true"},
        json={"email_verified": True, "email_verified_at": clock.now.isoformat()},
    )
    assert response.status_code == 200, response.text
    assert response.json()["email_verified_at"] is None
    db.refresh(user)
    assert user.email_verified_at is None
    assert publishing_state(db) == before


@pytest.mark.page("F11", 1)
@pytest.mark.parametrize("path", ACCOUNT_PATHS)
def test_verification_refresh_never_publishes(clock, db, client, firebase, path):
    user = make_user(db)
    headers = firebase.sign_in(user)
    before = publishing_state(db)
    response = refresh_account(client, path, headers)
    assert response.status_code == 200, response.text
    db.refresh(user)
    assert user.email_verified_at == clock.now
    assert publishing_state(db) == before
