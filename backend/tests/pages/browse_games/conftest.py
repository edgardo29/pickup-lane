import pytest


@pytest.fixture
def browse(client):
    """Call GET /games/browse and return the JSON body after checking for 200."""

    def call(**params):
        response = client.get("/games/browse", params=params)
        assert response.status_code == 200, response.text
        return response.json()

    return call
