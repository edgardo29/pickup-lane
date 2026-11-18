"""F29 the location staff enter when creating an official game."""

from datetime import timedelta

import pytest
from sqlalchemy import func, select

from backend.models import Game, Venue
from backend.tests.conftest import database_now
from backend.tests.factories import make_user, make_venue


@pytest.mark.page("F29", 3)
def test_a_reused_facility_keeps_the_entered_neighborhood(db, client, firebase):
    admin = make_user(db, role="admin")
    existing = make_venue(
        db,
        name="Union Park",
        address_line_1="100 Shared Street",
        postal_code="60601",
        neighborhood="Bucktown",
    )
    starts_at = database_now(db) + timedelta(days=2)

    response = client.post(
        "/admin/official-games",
        headers=firebase.sign_in(admin),
        json={
            "starts_at": starts_at.isoformat(),
            "ends_at": (starts_at + timedelta(hours=1)).isoformat(),
            "format_label": "7v7",
            "environment_type": "outdoor",
            "total_spots": 14,
            "price_per_player_cents": 1000,
            "venue": {
                "name": "Union Park",
                "address_line_1": "100 Shared Street",
                "city": "Chicago",
                "state": "IL",
                "postal_code": "60601",
                "neighborhood": "Wicker Park",
            },
        },
    )

    assert response.status_code == 201, response.text
    game = db.get(Game, response.json()["game"]["id"])
    assert game.venue_id == existing.id
    assert game.neighborhood_snapshot == "Wicker Park"
    db.refresh(existing)
    assert existing.neighborhood == "Bucktown"


@pytest.mark.page("F29", 3)
def test_a_facility_awaiting_review_is_reused_without_changing_its_status(
    db, client, firebase
):
    admin = make_user(db, role="admin")
    existing = make_venue(
        db,
        name="Union Park",
        address_line_1="100 Shared Street",
        postal_code="60601",
        venue_status="pending_review",
    )
    venues_before = db.scalar(select(func.count(Venue.id)))
    starts_at = database_now(db) + timedelta(days=2)

    response = client.post(
        "/admin/official-games",
        headers=firebase.sign_in(admin),
        json={
            "starts_at": starts_at.isoformat(),
            "ends_at": (starts_at + timedelta(hours=1)).isoformat(),
            "format_label": "7v7",
            "environment_type": "outdoor",
            "total_spots": 14,
            "price_per_player_cents": 1000,
            "venue": {
                "name": "union park",
                "address_line_1": "100 Shared Street",
                "city": "Chicago",
                "state": "IL",
                "postal_code": "60601",
            },
        },
    )

    assert response.status_code == 201, response.text
    game = db.get(Game, response.json()["game"]["id"])
    assert game.venue_id == existing.id
    assert db.scalar(select(func.count(Venue.id))) == venues_before
    db.refresh(existing)
    assert existing.venue_status == "pending_review"
