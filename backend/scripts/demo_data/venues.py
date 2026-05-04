from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from backend.models import User, Venue
from backend.scripts.demo_data.helpers import demo_uuid, now_utc, upsert_by_id
from backend.scripts.demo_data.users import ADMIN_KEY

DEMO_VENUES = [
    {
        "key": "intentional-sports",
        "name": "Intentional Sports",
        "address_line_1": "1841 N Laramie Ave",
        "neighborhood": "Elmwood Park",
        "postal_code": "60707",
        "latitude": Decimal("41.914300"),
        "longitude": Decimal("-87.755200"),
    },
    {
        "key": "rauner-ymca-indoor",
        "name": "Rauner YMCA Indoor",
        "address_line_1": "2700 S Western Ave",
        "neighborhood": "Pilsen",
        "postal_code": "60608",
        "latitude": Decimal("41.843700"),
        "longitude": Decimal("-87.686900"),
    },
    {
        "key": "skinner-park",
        "name": "Skinner Park",
        "address_line_1": "1331 W Adams St",
        "neighborhood": "West Loop",
        "postal_code": "60607",
        "latitude": Decimal("41.879400"),
        "longitude": Decimal("-87.660900"),
    },
    {
        "key": "skyline-pitch",
        "name": "Skyline Pitch",
        "address_line_1": "3025 W Carroll Ave",
        "neighborhood": "Garfield Park",
        "postal_code": "60612",
        "latitude": Decimal("41.887600"),
        "longitude": Decimal("-87.702600"),
    },
    {
        "key": "harrison-park",
        "name": "Harrison Park",
        "address_line_1": "1824 S Wood St",
        "neighborhood": "Pilsen",
        "postal_code": "60608",
        "latitude": Decimal("41.856400"),
        "longitude": Decimal("-87.671700"),
    },
    {
        "key": "livingston-park",
        "name": "Livingston Park",
        "address_line_1": "5250 N Broadway",
        "neighborhood": "Uptown",
        "postal_code": "60640",
        "latitude": Decimal("41.977900"),
        "longitude": Decimal("-87.659300"),
    },
    {
        "key": "rauner-ymca-outdoor",
        "name": "Rauner YMCA Outdoor",
        "address_line_1": "2700 S Western Ave",
        "neighborhood": "Little Village",
        "postal_code": "60608",
        "latitude": Decimal("41.843200"),
        "longitude": Decimal("-87.687400"),
    },
    {
        "key": "british-international-school-of-chicago-south-loop",
        "name": "British International School South Loop",
        "address_line_1": "161 W 9th St",
        "neighborhood": "South Loop",
        "postal_code": "60605",
        "latitude": Decimal("41.870900"),
        "longitude": Decimal("-87.633600"),
    },
]


def seed_venues(db: Session, users: dict[str, User]) -> dict[str, Venue]:
    seeded_venues: dict[str, Venue] = {}
    timestamp = now_utc()
    admin = users[ADMIN_KEY]

    for venue_data in DEMO_VENUES:
        venue_id = demo_uuid(f"venue:{venue_data['key']}")
        seeded_venues[venue_data["key"]] = upsert_by_id(
            db,
            Venue,
            venue_id,
            {
                "name": venue_data["name"],
                "address_line_1": venue_data["address_line_1"],
                "city": "Chicago",
                "state": "IL",
                "postal_code": venue_data["postal_code"],
                "country_code": "US",
                "neighborhood": venue_data["neighborhood"],
                "latitude": venue_data["latitude"],
                "longitude": venue_data["longitude"],
                "external_place_id": f"demo-{venue_data['key']}",
                "venue_status": "approved",
                "created_by_user_id": admin.id,
                "approved_by_user_id": admin.id,
                "approved_at": timestamp,
                "is_active": True,
                "deleted_at": None,
                "updated_at": timestamp,
            },
        )

    return seeded_venues
