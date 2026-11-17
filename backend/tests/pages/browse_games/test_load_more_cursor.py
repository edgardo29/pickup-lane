"""The Load More cursor cannot be edited or reused for another date.

Required by docs/coding-standards/backend-structure.md (Collections): a cursor
is protected against modification and bound to the query that created it.
"""

import json
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import UTC, date, datetime, timedelta

import pytest

from backend.settings import SettingsError, build_settings
from backend.tests.factories import (
    PRODUCTION_CURSOR_SIGNING_SECRET,
    PRODUCTION_DATABASE_URL,
    make_game,
    production_settings_env,
)


def chicago(hour: int, *, days: int = 0) -> datetime:
    """A time on 2026-06-15 (plus ``days``) in America/Chicago (UTC-5 in June)."""
    return datetime(2026, 6, 15 + days, hour, tzinfo=UTC) + timedelta(hours=5)


def first_page_cursor(db, browse, *, days: int = 0) -> str:
    for hour in (13, 14, 15):
        make_game(db, starts_at=chicago(hour, days=days))
    starts_on = (date(2026, 6, 15) + timedelta(days=days)).isoformat()
    body = browse(starts_on=starts_on, limit=2)
    assert body["has_more"] is True
    return body["next_cursor"]


def b64decode(value: str) -> bytes:
    return urlsafe_b64decode(value + "=" * (-len(value) % 4))


def b64encode(value: bytes) -> str:
    return urlsafe_b64encode(value).decode("ascii").rstrip("=")


@pytest.mark.page("F15", 18)
def test_edited_cursor_is_rejected(clock, db, client, browse):
    cursor = first_page_cursor(db, browse)
    encoded_body, signature = cursor.split(".")
    body = json.loads(b64decode(encoded_body))
    body["payload"]["starts_at"] = chicago(10).isoformat()
    edited = f"{b64encode(json.dumps(body).encode())}.{signature}"

    response = client.get("/games/browse", params={"limit": 2, "cursor": edited})

    assert response.status_code == 400
    assert response.json()["detail"] == "cursor is invalid."


@pytest.mark.page("F15", 18)
@pytest.mark.parametrize("cursor", ["not-a-cursor", "abc.def", "...", "e30."])
def test_made_up_cursor_is_rejected(clock, client, cursor):
    response = client.get("/games/browse", params={"cursor": cursor})

    assert response.status_code == 400
    assert response.json()["detail"] == "cursor is invalid."


@pytest.mark.page("F15", 18)
def test_cursor_from_another_date_is_rejected(clock, db, client, browse):
    tomorrow_cursor = first_page_cursor(db, browse, days=1)

    response = client.get(
        "/games/browse",
        params={"starts_on": "2026-06-15", "limit": 2, "cursor": tomorrow_cursor},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "cursor does not match the current query."


def build(env: dict[str, str]):
    return build_settings(env, load_dotenv_file=False, validate_full=True)


@pytest.mark.page("F15", 18)
def test_production_accepts_an_independent_signing_secret():
    settings = build(production_settings_env())

    assert settings.cursor_signing_secret_value == PRODUCTION_CURSOR_SIGNING_SECRET


@pytest.mark.page("F15", 18)
@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"CURSOR_SIGNING_SECRET": None}, "is required"),
        (
            {"CURSOR_SIGNING_SECRET": "replace-with-cursor-signing-secret"},
            "placeholder",
        ),
        (
            {"CURSOR_SIGNING_SECRET": PRODUCTION_DATABASE_URL},
            "must be independent from DATABASE_URL",
        ),
        (
            {"CURSOR_SIGNING_SECRET": "synthetic-r2-secret-access-key"},
            "must be independent from R2_SECRET_ACCESS_KEY",
        ),
    ],
    ids=["missing", "placeholder", "same-as-database-url", "same-as-r2-secret"],
)
def test_production_rejects_a_missing_or_reused_signing_secret(overrides, message):
    with pytest.raises(SettingsError) as exc_info:
        build(production_settings_env(**overrides))

    assert "CURSOR_SIGNING_SECRET" in str(exc_info.value)
    assert message in str(exc_info.value)
