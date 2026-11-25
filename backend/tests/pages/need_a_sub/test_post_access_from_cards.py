"""F20 what a card's post shows a guest, and that an unavailable post stays hidden."""

from datetime import UTC, date, datetime, timedelta

import pytest

from backend.tests.factories import make_user

TOMORROW = date(2026, 6, 16)
SEVEN_PM_TOMORROW = datetime(2026, 6, 16, 19, 0, tzinfo=UTC) + timedelta(hours=5)

PUBLIC_SUMMARY_FIELDS = {
    "id",
    "post_status",
    "public_visibility_status",
    "sport_type",
    "format_label",
    "environment_type",
    "skill_level",
    "game_player_group",
    "starts_at",
    "ends_at",
    "timezone",
    "location_name",
    "city",
    "state",
    "neighborhood",
    "subs_needed",
    "price_due_at_venue_cents",
    "currency",
    "expires_at",
    "created_at",
    "updated_at",
    "positions",
    "pending_count",
    "confirmed_count",
    "sub_waitlist_count",
}

# Ways a post that was on a card can become unavailable before the visitor opens it.
UNAVAILABLE = {
    "cancelled": lambda now: {"post_status": "cancelled", "canceled_at": now},
    "removed": lambda now: {"post_status": "removed", "removed_at": now},
    "expired": lambda now: {"post_status": "expired"},
    "completed": lambda now: {"post_status": "completed", "filled_at": now},
    "hidden": lambda now: {"public_visibility_status": "hidden"},
}


@pytest.mark.page("F20", 14)
def test_a_guest_gets_only_the_public_summary_of_a_post(clock, db, client, new_post):
    post = new_post(SEVEN_PM_TOMORROW, notes="Bring a white and a dark shirt.")

    response = client.get(f"/need-a-sub/posts/{post.id}")

    assert response.status_code == 200, response.text
    assert set(response.json()) == PUBLIC_SUMMARY_FIELDS


@pytest.mark.page("F20", 14)
def test_a_signed_in_visitor_gets_the_full_post(clock, db, client, firebase, new_post):
    post = new_post(SEVEN_PM_TOMORROW, notes="Bring a white and a dark shirt.")
    viewer = make_user(db, date_of_birth=date(1990, 1, 1))

    response = client.get(
        f"/need-a-sub/posts/{post.id}", headers=firebase.sign_in(viewer)
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert (body.get("address_line_1"), body.get("postal_code"), body.get("notes")) == (
        "200 Test Avenue",
        "60601",
        "Bring a white and a dark shirt.",
    )


@pytest.mark.page("F20", 15)
@pytest.mark.parametrize("change", list(UNAVAILABLE))
def test_a_post_that_became_unavailable_is_not_shown(
    clock, db, client, firebase, new_post, change
):
    post = new_post(SEVEN_PM_TOMORROW, **UNAVAILABLE[change](clock.now))
    viewer = make_user(db, date_of_birth=date(1990, 1, 1))

    response = client.get(
        f"/need-a-sub/posts/{post.id}", headers=firebase.sign_in(viewer)
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Need a Sub post not found."


@pytest.mark.page("F20", 15)
def test_a_post_that_started_is_not_shown_to_an_unconnected_visitor(
    clock, db, client, firebase, new_post
):
    post = new_post(clock.now - timedelta(minutes=1))
    viewer = make_user(db, date_of_birth=date(1990, 1, 1))

    response = client.get(
        f"/need-a-sub/posts/{post.id}", headers=firebase.sign_in(viewer)
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Need a Sub post not found."
