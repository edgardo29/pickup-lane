"""Save the fields the backend sends for each frontend page's endpoints.

Frontend page tests use made-up backend answers. Each page's
``frontend/tests/pages/<page>/backend_fields.json`` holds the fields the
backend really sends for the endpoints that page uses, taken from the
backend's own OpenAPI description. The page tests check every made-up answer
against it.

Re-save after changing what an endpoint sends, from the repository root:

    backend/.venv/bin/python -m backend.tests.frontend_fields.save
"""

import json
from pathlib import Path

from backend.main import app

REPO_ROOT = Path(__file__).resolve().parents[3]
OPENAPI_REF_PREFIX = "#/components/schemas/"
FILE_REF_PREFIX = "#/$defs/"

# The backend endpoints each frontend page's tests fake.
PAGE_ENDPOINTS = {
    "browse_games": ["GET /games/browse"],
    "game_details": [
        "GET /games/{game_id}",
        "GET /games/{game_id}/participants",
        "GET /game-images",
        "GET /venue-images",
        "GET /venues/{venue_id}",
        "GET /community-game-details",
        "POST /games/{game_id}/leave",
        "POST /games/{game_id}/guests/add",
        "POST /games/{game_id}/guests/remove",
        "POST /games/{game_id}/cancel",
        "GET /games/{game_id}/change-review",
        "POST /games/{game_id}/change-removal-requests",
        "POST /game-chats/for-game/{game_id}",
        "GET /game-chats/{game_chat_id}/read-state",
        "POST /game-chats/{game_chat_id}/read",
        "GET /chat-messages",
        "POST /chat-messages",
    ],
    "game_checkout": [
        "GET /games/{game_id}",
        "GET /games/{game_id}/participants",
        "GET /game-images",
        "GET /venue-images",
        "GET /venues/{venue_id}",
        "GET /user-payment-methods",
        "POST /user-payment-methods/setup-intent",
        "GET /checkout/games/{game_id}/quote",
        "POST /checkout/games/{game_id}/payment-intent",
        "POST /checkout/games/{game_id}/guest-payment-intent",
        "GET /checkout/bookings/{booking_id}/status",
        "POST /games/{game_id}/join",
        "POST /games/{game_id}/booking-guests/add",
    ],
    "edit_game": [
        "GET /games/{game_id}",
        "GET /venues/{venue_id}",
        "GET /community-game-details/games/{game_id}/host-edit",
        "PATCH /games/{game_id}/host-edit",
        "PUT /community-game-details/games/{game_id}/host-edit",
    ],
}


def fields_file_path(page: str) -> Path:
    return REPO_ROOT / "frontend" / "tests" / "pages" / page / "backend_fields.json"


def build_fields_file(openapi: dict, endpoints: list[str]) -> str:
    """Return the file text: each endpoint's success answer and the shapes it uses."""
    shapes = openapi["components"]["schemas"]
    answers = {endpoint: _success_answer(openapi, endpoint) for endpoint in endpoints}

    used_names: set[str] = set()
    pending = _ref_names(answers)
    while pending:
        name = pending.pop()
        if name not in used_names:
            used_names.add(name)
            pending |= _ref_names(shapes[name])

    fields = {
        "endpoints": answers,
        "$defs": {name: shapes[name] for name in sorted(used_names)},
    }
    return json.dumps(_point_refs_at_file(fields), indent=2, sort_keys=True) + "\n"


def _success_answer(openapi: dict, endpoint: str) -> dict:
    method, path = endpoint.split(" ", 1)
    operation = openapi["paths"].get(path, {}).get(method.lower())
    if operation is None:
        raise ValueError(f"{endpoint} is not a backend endpoint.")

    answers = [
        response["content"]["application/json"]["schema"]
        for status, response in operation["responses"].items()
        if status.startswith("2") and "application/json" in response.get("content", {})
    ]
    if len(answers) != 1:
        raise ValueError(
            f"{endpoint} must have exactly one JSON success answer; found {len(answers)}."
        )
    return answers[0]


def _ref_names(value: object) -> set[str]:
    names: set[str] = set()
    if isinstance(value, dict):
        ref = value.get("$ref")
        if isinstance(ref, str):
            if not ref.startswith(OPENAPI_REF_PREFIX):
                raise ValueError(f"Unexpected reference {ref!r}.")
            names.add(ref.removeprefix(OPENAPI_REF_PREFIX))
        for item in value.values():
            names |= _ref_names(item)
    elif isinstance(value, list):
        for item in value:
            names |= _ref_names(item)
    return names


def _point_refs_at_file(value: object) -> object:
    """Point each reference at the shape's copy in this file's ``$defs``."""
    if isinstance(value, dict):
        return {
            key: (
                FILE_REF_PREFIX + item.removeprefix(OPENAPI_REF_PREFIX)
                if key == "$ref" and isinstance(item, str)
                else _point_refs_at_file(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_point_refs_at_file(item) for item in value]
    return value


def main() -> None:
    openapi = app.openapi()
    for page, endpoints in PAGE_ENDPOINTS.items():
        path = fields_file_path(page)
        path.write_text(build_fields_file(openapi, endpoints))
        print(f"Saved {path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
