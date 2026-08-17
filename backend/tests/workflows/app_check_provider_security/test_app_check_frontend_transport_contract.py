from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.no_db_cleanup, pytest.mark.suite_type("ordinary")]

REPO_ROOT = Path(__file__).resolve().parents[4]
FRONTEND_ROOT = REPO_ROOT / "frontend"
API_CLIENT = FRONTEND_ROOT / "src/lib/apiClient.js"
APP_CHECK_HELPER = FRONTEND_ROOT / "src/lib/appCheck.js"
ADMIN_OFFICIAL_GAMES_API = (
    FRONTEND_ROOT / "src/pages/admin/official-games/shared/adminOfficialGamesApi.js"
)


def _source(path: Path) -> str:
    return path.read_text()


@pytest.mark.requirement("WS03-03B-R2", "WS03-03B-R6")
def test_api_client_centralizes_app_check_header_for_pickup_lane_api_requests() -> None:
    source = _source(API_CLIENT)

    assert "import { APP_CHECK_HEADER_NAME, getAppCheckToken } from './appCheck.js'" in source
    assert "headers[APP_CHECK_HEADER_NAME] = appCheckToken" in source
    assert "shouldAttachAppCheck(path)" in source
    assert "buildApiUrl(path)" in source
    assert "Authorization" not in _function_source(source, "apiRequest", "getApiErrorCode")


@pytest.mark.requirement("WS03-03B-R2", "WS03-03B-R5", "WS03-03B-R7")
def test_api_client_does_not_attach_app_check_to_arbitrary_absolute_urls() -> None:
    source = _source(API_CLIENT)
    should_attach_source = _function_source(source, "shouldAttachAppCheck", "buildApiUrl")

    assert "http" in should_attach_source
    assert "data:" in should_attach_source
    assert "getAppCheckToken()" not in _function_source(source, "buildMediaUrl", "formatApiErrorMessage")


@pytest.mark.requirement("WS03-03B-R2", "WS03-03B-R5", "WS03-03B-R6", "WS03-03B-R7")
def test_direct_signed_provider_upload_uses_raw_fetch_not_shared_api_client() -> None:
    source = _source(ADMIN_OFFICIAL_GAMES_API)
    upload_source = _function_source(
        source,
        "uploadVenueImageObject",
        "completeAdminVenueImageUpload",
    )

    assert "fetch(uploadUrl" in upload_source
    assert "apiRequest(" not in upload_source
    assert "X-Firebase-AppCheck" not in upload_source


@pytest.mark.requirement("WS03-03B-R2", "WS03-03B-R6", "WS03-03B-R7")
def test_frontend_app_check_helper_does_not_persist_or_log_tokens() -> None:
    combined_source = "\n".join([_source(APP_CHECK_HELPER), _source(API_CLIENT)])

    for forbidden in (
        "localStorage",
        "sessionStorage",
        "document.cookie",
        "console.",
        "analytics",
    ):
        assert forbidden not in combined_source
    assert "body: appCheckToken" not in combined_source
    assert "URLSearchParams({ appCheck" not in combined_source


@pytest.mark.requirement("WS03-03B-R2", "WS03-03B-R6", "WS03-03B-R7")
def test_low_level_api_client_has_no_global_retry_or_step_up_replay() -> None:
    source = _source(API_CLIENT)

    assert "AUTH.RECENT_AUTH_REQUIRED" not in source
    assert "runStepUpProtectedAction" not in source
    assert "retry" not in source.lower()
    assert source.count("fetch(") == 1


def _function_source(source: str, start_name: str, end_name: str) -> str:
    start = min(
        index
        for marker in (
            f"function {start_name}",
            f"export function {start_name}",
            f"export async function {start_name}",
        )
        if (index := source.find(marker)) != -1
    )
    end_marker = min(
        index
        for marker in (
            f"function {end_name}",
            f"export function {end_name}",
            f"export async function {end_name}",
        )
        if (index := source.find(marker, start + 1)) != -1
    )
    return source[start:end_marker]
