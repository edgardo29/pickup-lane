from fastapi.testclient import TestClient


def test_core_routes_are_registered(client: TestClient):
    registered_routes = {
        (method, route.path)
        for route in client.app.routes
        for method in route.methods
        if method not in {"HEAD", "OPTIONS"}
    }
    expected_routes = {
        ("GET", "/"),
        ("GET", "/db-health"),
        ("POST", "/users"),
        ("GET", "/users"),
        ("GET", "/users/{user_id}"),
        ("PATCH", "/users/{user_id}"),
        ("DELETE", "/users/{user_id}"),
        ("POST", "/user-settings"),
        ("GET", "/user-settings/{user_id}"),
        ("PATCH", "/user-settings/{user_id}"),
        ("POST", "/user-payment-methods"),
        ("GET", "/user-payment-methods"),
        ("GET", "/user-payment-methods/{payment_method_id}"),
        ("PATCH", "/user-payment-methods/{payment_method_id}"),
        ("POST", "/venues"),
        ("GET", "/venues"),
        ("GET", "/venues/{venue_id}"),
        ("PATCH", "/venues/{venue_id}"),
        ("DELETE", "/venues/{venue_id}"),
        ("POST", "/games"),
        ("GET", "/games"),
        ("GET", "/games/{game_id}"),
        ("PATCH", "/games/{game_id}"),
        ("DELETE", "/games/{game_id}"),
        ("POST", "/bookings"),
        ("GET", "/bookings"),
        ("GET", "/bookings/{booking_id}"),
        ("PATCH", "/bookings/{booking_id}"),
        ("POST", "/game-participants"),
        ("GET", "/game-participants"),
        ("GET", "/game-participants/{participant_id}"),
        ("PATCH", "/game-participants/{participant_id}"),
        ("POST", "/waitlist-entries"),
        ("GET", "/waitlist-entries"),
        ("GET", "/waitlist-entries/{waitlist_entry_id}"),
        ("PATCH", "/waitlist-entries/{waitlist_entry_id}"),
    }

    assert expected_routes <= registered_routes
