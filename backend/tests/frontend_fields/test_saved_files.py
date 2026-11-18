"""Each frontend page's backend_fields.json must match what the backend sends today."""

import pytest

from backend.main import app
from backend.tests.frontend_fields.save import (
    PAGE_ENDPOINTS,
    REPO_ROOT,
    build_fields_file,
    fields_file_path,
)

SAVE_COMMAND = "backend/.venv/bin/python -m backend.tests.frontend_fields.save"


@pytest.mark.parametrize("page", sorted(PAGE_ENDPOINTS))
def test_saved_fields_file_matches_the_backend(page):
    path = fields_file_path(page)
    saved = path.read_text() if path.exists() else None

    assert saved == build_fields_file(app.openapi(), PAGE_ENDPOINTS[page]), (
        f"{path.relative_to(REPO_ROOT)} is out of date. "
        f"Re-save it from the repository root with: {SAVE_COMMAND}"
    )
