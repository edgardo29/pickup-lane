"""F05's connected profile submission follows the approved birthday rule."""

from datetime import date, datetime

import pytest

from backend.models import User
from backend.tests.factories import make_user
from backend.tests.pages.create_account.conftest import accounts


@pytest.mark.page("F05", 1, 10)
@pytest.mark.parametrize(
    "moment,birthday",
    [
        ("2026-06-16T04:59:59+00:00", "2008-06-16"),
        ("2026-03-01T05:59:59+00:00", "2008-02-29"),
        ("2026-06-15T17:00:00+00:00", "2027-01-01"),
        ("2026-06-15T17:00:00+00:00", "2020-01-01"),
        ("2026-06-15T17:00:00+00:00", "2000-02-31"),
    ],
)
def test_an_ineligible_birthday_is_rejected_without_profile_changes(
    clock, db, client, firebase, moment, birthday
):
    clock.move_to(datetime.fromisoformat(moment))
    user = make_user(db, first_name=None, last_name=None)
    headers = firebase.sign_in(user)
    before = accounts(db)
    response = client.patch(
        "/users/me",
        headers=headers,
        json={"first_name": "Jordan", "last_name": "Player", "date_of_birth": birthday},
    )
    assert response.status_code == 422, response.text
    assert response.json()["detail"]
    db.expire_all()
    assert accounts(db) == before


@pytest.mark.page("F05", 10)
@pytest.mark.parametrize(
    "moment,birthday",
    [
        ("2026-06-16T05:00:00+00:00", "2008-06-16"),
        ("2026-03-01T06:00:00+00:00", "2008-02-29"),
        ("2026-06-15T17:00:00+00:00", "1990-01-01"),
    ],
)
def test_an_eligible_birthday_saves_only_to_the_authenticated_profile(
    clock, db, client, firebase, moment, birthday
):
    clock.move_to(datetime.fromisoformat(moment))
    other = make_user(db, date_of_birth=date(1991, 1, 2))
    other_before = (other.first_name, other.last_name, other.date_of_birth)
    user = make_user(db, first_name=None, last_name=None)
    response = client.patch(
        "/users/me",
        headers=firebase.sign_in(user),
        json={"first_name": "Jordan", "last_name": "Player", "date_of_birth": birthday},
    )
    assert response.status_code == 200, response.text
    assert response.json()["id"] == str(user.id)
    assert response.json()["date_of_birth"] == birthday
    db.expire_all()
    saved = db.get(User, user.id)
    assert (saved.first_name, saved.last_name, saved.date_of_birth) == (
        "Jordan",
        "Player",
        date.fromisoformat(birthday),
    )
    assert (other.first_name, other.last_name, other.date_of_birth) == other_before
