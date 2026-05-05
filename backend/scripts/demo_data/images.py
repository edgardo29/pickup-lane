from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Game, GameImage
from backend.scripts.demo_data.games import DEMO_GAMES
from backend.scripts.demo_data.helpers import demo_uuid, upsert_by_id

STATIC_IMAGE_BY_VENUE_KEY = {
    "intentional-sports": "/static/seed/venues/intentional-sports/gallery-1.webp",
    "rauner-ymca-indoor": "/static/seed/venues/rauner-ymca-indoor/gallery-1.webp",
    "skinner-park": "/static/seed/venues/skinner-park/gallery-1.webp",
    "skyline-pitch": "/static/seed/venues/skyline-pitch/gallery-1.webp",
    "harrison-park": "/static/seed/venues/harrison-park/gallery-1.webp",
    "livingston-park": "/static/seed/venues/livingston-park/gallery-1.jpg",
    "rauner-ymca-outdoor": "/static/seed/venues/rauner-ymca-outdoor/gallery-1.jpeg",
    "british-international-school-of-chicago-south-loop": (
        "/static/seed/venues/british-international-school-of-chicago-south-loop/gallery-1.webp"
    ),
}

GALLERY_IMAGE_URLS = list(STATIC_IMAGE_BY_VENUE_KEY.values())


def seed_game_images(db: Session, games: dict[str, Game]) -> dict[str, GameImage]:
    seeded_images: dict[str, GameImage] = {}

    for game_data in DEMO_GAMES:
        game = games[game_data["key"]]
        image_url = STATIC_IMAGE_BY_VENUE_KEY[game_data["venue_key"]]
        image_id = demo_uuid(f"game-image:{game_data['key']}:primary")

        existing_primary = db.scalars(
            select(GameImage).where(
                GameImage.game_id == game.id,
                GameImage.is_primary.is_(True),
                GameImage.image_status == "active",
                GameImage.deleted_at.is_(None),
            )
        ).first()

        if existing_primary is not None and existing_primary.id != image_id:
            existing_primary.image_url = image_url
            existing_primary.image_role = "card"
            existing_primary.image_status = "active"
            existing_primary.is_primary = True
            existing_primary.sort_order = 0
            existing_primary.deleted_at = None
            seeded_images[game_data["key"]] = existing_primary
        else:
            seeded_images[game_data["key"]] = upsert_by_id(
                db,
                GameImage,
                image_id,
                {
                    "game_id": game.id,
                    "uploaded_by_user_id": None,
                    "image_url": image_url,
                    "image_role": "card",
                    "image_status": "active",
                    "is_primary": True,
                    "sort_order": 0,
                    "deleted_at": None,
                },
            )

        gallery_urls = build_gallery_urls(game_data["venue_key"])

        for index, gallery_url in enumerate(gallery_urls, start=1):
            seeded_images[f"{game_data['key']}:gallery:{index}"] = upsert_by_id(
                db,
                GameImage,
                demo_uuid(f"game-image:{game_data['key']}:gallery:{index}"),
                {
                    "game_id": game.id,
                    "uploaded_by_user_id": None,
                    "image_url": gallery_url,
                    "image_role": "gallery",
                    "image_status": "active",
                    "is_primary": False,
                    "sort_order": index,
                    "deleted_at": None,
                },
            )

    return seeded_images


def build_gallery_urls(venue_key: str) -> list[str]:
    primary_url = STATIC_IMAGE_BY_VENUE_KEY[venue_key]
    alternate_urls = [url for url in GALLERY_IMAGE_URLS if url != primary_url]

    return alternate_urls[:3]
