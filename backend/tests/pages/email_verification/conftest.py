"""Inputs and state snapshots for F11's two creation gates."""

from datetime import timedelta

import pytest
from sqlalchemy import select

from backend.models import (
    CommunityGameDetail,
    CommunityPublishAttempt,
    Game,
    GameParticipant,
    HostPublishEntitlement,
    HostPublishFee,
    Payment,
    SubPost,
    SubPostPosition,
    SubPostStatusHistory,
    Venue,
)

CREATION_PATHS = ["/community-games/publish", "/need-a-sub/posts"]
ACCOUNT_PATHS = ["/auth/me", "/auth/sync-user"]


def publishing_state(db):
    return {
        model.__name__: db.execute(select(model.__table__).order_by(model.id)).all()
        for model in (
            Game,
            CommunityGameDetail,
            GameParticipant,
            HostPublishFee,
            HostPublishEntitlement,
            CommunityPublishAttempt,
            Payment,
            SubPost,
            SubPostPosition,
            SubPostStatusHistory,
            Venue,
        )
    }


def refresh_account(client, path, headers, **kwargs):
    return client.request(
        "GET" if path == "/auth/me" else "POST", path, headers=headers, **kwargs
    )


@pytest.fixture
def creation_payloads(clock):
    schedule = {
        "starts_at": (clock.now + timedelta(days=3)).isoformat(),
        "ends_at": (clock.now + timedelta(days=3, hours=1)).isoformat(),
        "timezone": "America/Chicago",
        "format_label": "7v7",
        "game_player_group": "coed",
        "skill_level": "any",
        "environment_type": "outdoor",
    }
    return {
        "/community-games/publish": {
            **schedule,
            "total_spots": 14,
            "price_per_player_cents": 0,
            "venue": {
                "name": "Verification Test Park",
                "address_line_1": "100 Test Street",
                "city": "Chicago",
                "state": "IL",
                "postal_code": "60601",
            },
        },
        "/need-a-sub/posts": {
            **schedule,
            "location_name": "Verification Test Park",
            "address_line_1": "100 Test Street",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60601",
            "subs_needed": 1,
            "positions": [
                {
                    "position_label": "field_player",
                    "player_group": "open",
                    "spots_needed": 1,
                    "sort_order": 0,
                }
            ],
        },
    }
