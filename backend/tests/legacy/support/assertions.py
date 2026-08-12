def assert_private_no_store(response) -> None:
    assert response.headers["Cache-Control"] == "private, no-store"
