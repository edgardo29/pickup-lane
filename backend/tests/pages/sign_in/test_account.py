"""F07 account identity and profile completion through the real API."""

from datetime import date

import pytest
from sqlalchemy import select

from backend.models import User
from backend.tests.factories import make_user


@pytest.mark.page("F07", 1, 2, 3)
@pytest.mark.parametrize("complete", [False, True])
@pytest.mark.parametrize(
    "account_status", ["active", "suspended", "pending_deletion", "deleted"]
)
def test_current_account_belongs_to_authenticated_firebase_user(
    clock, db, client, firebase, complete, account_status
):
    other = make_user(db, date_of_birth=date(1990, 1, 1))
    user = make_user(
        db,
        date_of_birth=date(1991, 2, 3) if complete else None,
        account_status=account_status,
        deleted_at=clock.now if account_status == "deleted" else None,
    )
    response = client.get("/auth/me", headers=firebase.sign_in(user))
    if account_status in {"pending_deletion", "deleted"}:
        assert response.status_code == 404
        assert response.json()["detail"] == "User not found."
        assert db.get(User, user.id).account_status == account_status
        return
    assert response.status_code == 200, response.text
    assert response.json()["id"] == str(user.id)
    assert response.json()["id"] != str(other.id)
    assert response.json()["date_of_birth"] == ("1991-02-03" if complete else None)


@pytest.mark.page("F07", 2)
def test_existing_account_sync_does_not_create_a_second_profile(db, client, firebase):
    user = make_user(db, date_of_birth=date(1990, 1, 1))
    before = list(db.scalars(select(User.id)))
    response = client.post("/auth/sync-user", headers=firebase.sign_in(user))
    assert response.status_code == 200, response.text
    assert response.json()["id"] == str(user.id)
    assert list(db.scalars(select(User.id))) == before


@pytest.mark.page("F07", 3)
def test_profile_completion_updates_only_the_signed_in_account(db, client, firebase):
    other = make_user(db)
    before = (other.first_name, other.last_name, other.date_of_birth)
    user = make_user(db, first_name=None, last_name=None)
    response = client.patch(
        "/users/me",
        headers=firebase.sign_in(user),
        json={
            "first_name": "Jordan",
            "last_name": "Player",
            "date_of_birth": "1990-01-01",
        },
    )
    assert response.status_code == 200, response.text
    db.expire_all()
    assert (user.first_name, user.last_name, user.date_of_birth) == (
        "Jordan",
        "Player",
        date(1990, 1, 1),
    )
    assert (other.first_name, other.last_name, other.date_of_birth) == before
