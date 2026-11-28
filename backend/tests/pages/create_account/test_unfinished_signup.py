"""F05's Google abandonment uses the real unfinished-account workflow."""

import pytest

from backend.models import User, UserSettings, UserStats
from backend.tests.factories import make_user
from backend.tests.pages.create_account.conftest import accounts


def unfinished(db, client, firebase):
    user = make_user(db, first_name=None, last_name=None)
    headers = firebase.sign_in(user)
    response = client.post("/auth/sync-user", headers=headers)
    assert response.status_code == 200
    assert db.get(UserSettings, user.id) is not None
    assert db.get(UserStats, user.id) is not None
    return user, headers


@pytest.mark.page("F05", 3)
def test_successful_cleanup_removes_the_unfinished_account_and_firebase_identity(
    db, client, firebase
):
    user, headers = unfinished(db, client, firebase)
    user_id, uid = user.id, user.auth_user_id
    response = client.delete("/auth/unfinished-account", headers=headers)
    assert response.status_code == 204
    assert response.content == b""
    db.expire_all()
    assert db.get(User, user_id) is None
    assert db.get(UserSettings, user_id) is None
    assert db.get(UserStats, user_id) is None
    assert uid not in firebase.accounts


@pytest.mark.page("F05", 7)
def test_failed_cleanup_preserves_the_unfinished_account_for_recovery(
    db, client, firebase, monkeypatch
):
    user, headers = unfinished(db, client, firebase)
    before = accounts(db)

    def unavailable(uid):
        raise RuntimeError("Synthetic Firebase cleanup failure")

    monkeypatch.setattr(
        "backend.services.auth_account_service.delete_firebase_user", unavailable
    )
    response = client.delete("/auth/unfinished-account", headers=headers)
    assert response.status_code == 502
    assert (
        response.json()["detail"]
        == "Firebase could not clean up this sign-up. Please try again."
    )
    db.expire_all()
    assert accounts(db) == before
    assert user.auth_user_id in firebase.accounts
