"""F05 email checks use the database and Firebase without starting signup."""

import pytest

from backend.tests.factories import make_user
from backend.tests.pages.create_account.conftest import accounts


@pytest.mark.page("F05", 1)
def test_an_available_email_does_not_create_an_account(db, client, monkeypatch):
    monkeypatch.setattr(
        "backend.services.auth_account_service.firebase_email_exists",
        lambda email: False,
    )
    before = accounts(db)
    response = client.get(
        "/auth/email-availability", params={"email": "  New@Example.test  "}
    )
    assert response.status_code == 200
    assert response.json() == {"email": "new@example.test", "available": True}
    assert accounts(db) == before


@pytest.mark.page("F05", 6)
@pytest.mark.parametrize("account_status", ["active", "suspended"])
def test_an_existing_email_is_unavailable_without_changes(
    db, client, monkeypatch, account_status
):
    user = make_user(db, account_status=account_status)

    def unexpected(email):
        pytest.fail("An existing application email needs no Firebase lookup")

    monkeypatch.setattr(
        "backend.services.auth_account_service.firebase_email_exists", unexpected
    )
    before = accounts(db)
    response = client.get(
        "/auth/email-availability", params={"email": user.email.upper()}
    )
    assert response.status_code == 200
    assert response.json() == {"email": user.email, "available": False}
    assert accounts(db) == before


@pytest.mark.page("F05", 6)
def test_a_firebase_only_email_is_unavailable_without_creating_a_profile(
    db, client, monkeypatch
):
    monkeypatch.setattr(
        "backend.services.auth_account_service.firebase_email_exists",
        lambda email: True,
    )
    before = accounts(db)
    response = client.get(
        "/auth/email-availability", params={"email": "google@example.test"}
    )
    assert response.status_code == 200
    assert response.json() == {"email": "google@example.test", "available": False}
    assert accounts(db) == before


@pytest.mark.page("F05", 7)
def test_an_availability_failure_leaves_accounts_unchanged(db, client, monkeypatch):
    def unavailable(email):
        raise RuntimeError("Synthetic Firebase lookup failure")

    monkeypatch.setattr(
        "backend.services.auth_account_service.firebase_email_exists", unavailable
    )
    before = accounts(db)
    response = client.get(
        "/auth/email-availability", params={"email": "new@example.test"}
    )
    assert response.status_code == 503
    assert (
        response.json()["detail"]
        == "Could not check email availability. Please try again."
    )
    assert accounts(db) == before
