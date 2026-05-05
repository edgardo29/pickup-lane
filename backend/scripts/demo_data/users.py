from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from backend.models import User
from backend.scripts.demo_data.helpers import demo_uuid, now_utc, upsert_by_id

ADMIN_KEY = "admin"
CURRENT_USER_KEY = "current-user"
CURRENT_USER_AUTH_ID = "demo-current-user"
HOST_KEYS = ["host-marcus", "host-sofia", "host-jordan"]
PLAYER_KEYS = [f"player-{index:02d}" for index in range(1, 33)]

DEMO_USERS = [
    {
        "key": ADMIN_KEY,
        "role": "admin",
        "first_name": "Maya",
        "last_name": "Admin",
        "hosting_status": "eligible",
    },
    {
        "key": "host-marcus",
        "role": "player",
        "first_name": "Marcus",
        "last_name": "Reed",
        "hosting_status": "eligible",
    },
    {
        "key": "host-sofia",
        "role": "player",
        "first_name": "Sofia",
        "last_name": "Mendez",
        "hosting_status": "eligible",
    },
    {
        "key": "host-jordan",
        "role": "player",
        "first_name": "Jordan",
        "last_name": "Kim",
        "hosting_status": "eligible",
    },
]

DEMO_USERS.extend(
    {
        "key": player_key,
        "role": "player",
        "first_name": f"Player{index:02d}",
        "last_name": "Demo",
        "hosting_status": "not_eligible",
    }
    for index, player_key in enumerate(PLAYER_KEYS, start=1)
)

DEMO_USERS.append(
    {
        "key": CURRENT_USER_KEY,
        "auth_user_id": CURRENT_USER_AUTH_ID,
        "role": "player",
        "first_name": "Alex",
        "last_name": "Rivera",
        "hosting_status": "eligible",
    }
)


def seed_users(db: Session) -> dict[str, User]:
    seeded_users: dict[str, User] = {}
    timestamp = now_utc()

    for index, user_data in enumerate(DEMO_USERS, start=1):
        user_id = demo_uuid(f"user:{user_data['key']}")
        seeded_users[user_data["key"]] = upsert_by_id(
            db,
            User,
            user_id,
            {
                "auth_user_id": user_data.get("auth_user_id", f"demo-{user_data['key']}"),
                "role": user_data["role"],
                "email": f"{user_data['key']}@demo.pickuplane.local",
                "phone": f"+1555100{index:04d}",
                "first_name": user_data["first_name"],
                "last_name": user_data["last_name"],
                "date_of_birth": date(1995, 1, 1),
                "profile_photo_url": None,
                "home_city": "Chicago",
                "home_state": "IL",
                "account_status": "active",
                "hosting_status": user_data["hosting_status"],
                "hosting_suspended_until": None,
                "stripe_customer_id": None,
                "deleted_at": None,
                "updated_at": timestamp,
            },
        )

    return seeded_users
