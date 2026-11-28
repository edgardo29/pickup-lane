"""F12's caller check for the birthday validation introduced by F05."""

from datetime import date

import pytest

from backend.tests.factories import make_user


@pytest.mark.page("F12", 3)
def test_an_ordinary_profile_update_keeps_the_existing_birthday(db, client, firebase):
    user = make_user(db, date_of_birth=date(1990, 1, 1))
    other = make_user(db, date_of_birth=date(1991, 2, 3))
    other_before = (other.first_name, other.last_name, other.date_of_birth)
    response = client.patch(
        "/users/me", headers=firebase.sign_in(user), json={"first_name": "Updated"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["first_name"] == "Updated"
    db.expire_all()
    assert user.first_name == "Updated"
    assert user.date_of_birth == date(1990, 1, 1)
    assert (other.first_name, other.last_name, other.date_of_birth) == other_before
