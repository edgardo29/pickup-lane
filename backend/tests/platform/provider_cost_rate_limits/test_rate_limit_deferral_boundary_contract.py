from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]
_MASTER = (
    "docs/production-readiness/planning/program/"
    "pickup-lane-master-production-readiness-blueprint.md"
)
_ARCHITECTURE = (
    "docs/production-readiness/planning/program/"
    "PRODUCTION-ARCHITECTURE-AND-ENVIRONMENTS.md"
)


def _read(relative_path: str) -> str:
    return (_REPO_ROOT / relative_path).read_text()


@pytest.mark.pass_provenance('WS02-04C3B')
def test_timeout_retry_chat_limit_and_input_boundaries_remain_distinct_from_provider_rate_control() -> None:
    master = _read(_MASTER)
    settings = _read("backend/settings.py")
    chat_limiter = _read("backend/services/chat_rate_limit_service.py")
    request_body_limits = _read("backend/observability/request_body_limits.py")

    assert "- a blanket rate limiter;" in master
    assert "A control that counts requests must also identify what distinguishes the caller or protected resource" in master
    assert "A control based on authentication, a unique database record, an idempotency key, or current business state" in master
    assert "STRIPE_READ_TIMEOUT_SECONDS" in settings
    assert "DB_POOL_WAIT_TIMEOUT_SECONDS" in settings
    assert "DEFAULT_ORDINARY_JSON_REQUEST_BODY_LIMIT_BYTES" in request_body_limits
    assert "enforce_visible_text_chat_rate_limit" in chat_limiter
    assert "PROVIDER_COST_RATE" not in settings


@pytest.mark.pass_provenance('WS02-04C3B')
def test_selected_services_do_not_establish_unverified_rate_or_capacity_settings() -> None:
    master = _read(_MASTER)
    architecture = _read(_ARCHITECTURE)
    settings = _read("backend/settings.py")

    assert "Production signoff is blocked when a setting covered by this section is missing" in master
    assert "Each Firebase, Stripe, Cloudflare R2, PostgreSQL-hosting, application-hosting" in master
    assert "expected peak use, numeric warning threshold, enforced hard limit" in master
    assert "Details requiring measured workload, purchased service capacity" in architecture
    assert "provider settings, capacity, and recovery performance not yet verified" in architecture
    assert "PROVIDER_COST_RATE" not in settings
