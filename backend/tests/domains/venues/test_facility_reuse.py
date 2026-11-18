"""Venue reuse: one facility record per facility, shared by every game there."""

from datetime import timedelta

from backend.models import Game
from backend.tests.conftest import database_now
from backend.tests.factories import make_user, make_venue


def test_publishing_at_a_reused_facility_keeps_the_hosts_neighborhood(
    db, client, firebase
):
    """Database architecture §3.6: a facility is matched on its name and full
    address, not its neighborhood, so reusing it keeps the neighborhood the
    host entered for the game and leaves the facility's own unchanged."""
    host = make_user(db, hosting_status="eligible")
    existing = make_venue(
        db,
        name="Union Park",
        address_line_1="100 Shared Street",
        postal_code="60601",
        neighborhood="Bucktown",
    )
    starts_at = database_now(db) + timedelta(days=2)

    response = client.post(
        "/community-games/publish",
        headers=firebase.sign_in(host),
        json={
            "starts_at": starts_at.isoformat(),
            "ends_at": (starts_at + timedelta(hours=1)).isoformat(),
            "format_label": "7v7",
            "environment_type": "outdoor",
            "total_spots": 14,
            "price_per_player_cents": 0,
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
