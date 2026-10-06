from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]


def _read(relative_path: str) -> str:
    return (_REPO_ROOT / relative_path).read_text()


@pytest.mark.pass_provenance('WS02-04C3B')
def test_timeout_retry_chat_limit_and_input_boundaries_remain_distinct_from_provider_rate_control() -> None:
    register = _read("docs/production-readiness/governance/limits-and-thresholds-register.md")

    assert "Operation timeouts do not authorize action-frequency limits" in register
    assert "Retry-safety classifications do not authorize action-frequency limits" in register
    assert "Product collection and pagination limits are not rate-limit authority" in register
    assert "Request-schema and client-input bounds are not rate-limit authority" in register


@pytest.mark.pass_provenance('WS02-04C3B')
def test_external_runtime_provider_edge_and_api_m11_gaps_remain_open() -> None:
    register = _read("docs/production-readiness/governance/limits-and-thresholds-register.md")

    for phrase in (
        "service dashboards",
        "service quotas and costs",
        "production request volume",
        "trusted client IP",
        "edge/WAF/CAPTCHA",
        "runtime/load behavior",
        "monitoring/alert thresholds",
    ):
        assert phrase in register

    assert "remain TBD pending owner decision and evidence" in register
