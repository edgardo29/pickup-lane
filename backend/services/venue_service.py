"""Shared venue lookup helpers used outside the venue routes."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models import Venue


def normalize_venue_lookup_value(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def find_matching_active_venue(
    db: Session,
    *,
    name: str,
    address_line_1: str,
    city: str,
    state: str,
    postal_code: str,
    country_code: str = "US",
    neighborhood: str | None = None,
) -> Venue | None:
    name_key = normalize_venue_lookup_value(name)
    street_key = normalize_venue_lookup_value(address_line_1)
    city_key = normalize_venue_lookup_value(city)
    state_key = normalize_venue_lookup_value(state)
    postal_key = normalize_venue_lookup_value(postal_code)
    country_key = normalize_venue_lookup_value(country_code).upper()
    neighborhood_key = normalize_venue_lookup_value(neighborhood)

    if not all([name_key, street_key, city_key, state_key, postal_key, country_key]):
        return None

    statement = (
        select(Venue)
        .where(
            Venue.deleted_at.is_(None),
            Venue.is_active.is_(True),
            func.lower(func.trim(Venue.name)) == name_key,
            func.lower(func.trim(Venue.address_line_1)) == street_key,
            func.lower(func.trim(Venue.city)) == city_key,
            func.lower(func.trim(Venue.state)) == state_key,
            func.lower(func.trim(Venue.postal_code)) == postal_key,
            func.upper(func.trim(Venue.country_code)) == country_key,
            func.lower(func.trim(func.coalesce(Venue.neighborhood, "")))
            == neighborhood_key,
        )
        .order_by(Venue.created_at.asc())
        .limit(1)
    )
    return db.scalars(statement).first()
