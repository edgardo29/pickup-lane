import pytest

from backend.tests.factories import make_user


@pytest.fixture
def inbox_user(db):
    return make_user(db)


@pytest.fixture
def inbox_headers(firebase, inbox_user):
    return firebase.sign_in(inbox_user)
