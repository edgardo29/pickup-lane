from datetime import date

import pytest

from backend.tests.factories import make_sub_post, make_user


@pytest.fixture
def new_post(db):
    """Create an active post, each by its own owner unless one is given.

    An owner can have only one active post per Chicago date.
    """

    def create(starts_at, *, owner=None, **overrides):
        owner = owner or make_user(db, date_of_birth=date(1990, 1, 1))
        return make_sub_post(db, owner=owner, starts_at=starts_at, **overrides)

    return create


@pytest.fixture
def cards(client):
    """Call GET /need-a-sub/posts/cards and return the JSON body after a 200."""

    def call(starts_on, *, headers=None, **params):
        response = client.get(
            "/need-a-sub/posts/cards",
            params={"starts_on": starts_on.isoformat(), **params},
            headers=headers or {},
        )
        assert response.status_code == 200, response.text
        return response.json()

    return call
