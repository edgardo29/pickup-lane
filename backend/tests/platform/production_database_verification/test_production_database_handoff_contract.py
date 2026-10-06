from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]
_GOVERNANCE_CONTRACT = (
    "docs/production-readiness/governance/"
    "production-database-verification-contract.md"
)
_CONTRACT_PATH = (
    "docs/production-readiness/governance/"
    "production-database-verification-contract.json"
)


def _read(relative_path: str) -> str:
    return (_REPO_ROOT / relative_path).read_text()


@pytest.mark.pass_provenance('WS04-01C')
def test_current_authority_preserves_provider_independent_template_and_mandatory_finalization() -> None:
    governance = _read(_GOVERNANCE_CONTRACT)

    assert "complete verification template without inventing production values" in governance
    assert "Final production verification is mandatory before production closeout" in governance
    assert "Temporary development or demo infrastructure is not final production evidence" in governance
    assert "No production value may be inferred" in governance


@pytest.mark.pass_provenance('WS04-01C')
def test_evidence_template_scope_does_not_introduce_production_source_config_or_migrations() -> None:
    governance = _read(_GOVERNANCE_CONTRACT)
    settings = _read("backend/settings.py")
    env_example = _read("backend/.env.example")
    migration_paths = sorted((_REPO_ROOT / "backend/alembic/versions").glob("*.py"))

    assert "does not itself authorize production application source" in governance
    assert "database migrations or schema changes" in governance
    assert "deployment settings" in governance
    assert "credentials" in governance
    assert "production_database_verification" not in settings
    assert "PRODUCTION_DATABASE_VERIFICATION" not in env_example
    assert not [
        path
        for path in migration_paths
        if "production_database_verification" in path.name.lower()
    ]


@pytest.mark.pass_provenance('WS04-01C')
def test_contract_handoff_names_all_final_verification_facts_without_values() -> None:
    contract = json.loads((_REPO_ROOT / _CONTRACT_PATH).read_text())

    assert (
        contract["handoff"]["final_verification_owner"]
        == "final_production_database_verification"
    )
    assert contract["handoff"]["required_before"] == ["CLOSE-01", "CLOSE-02"]
    assert {
        "actual provider usable connection capacity",
        "pooler/proxy/direct mode",
        "actual API instance/process/autoscaling/rolling-overlap topology",
        "deployed application pool values and connection wait behavior",
        "final deployment-wide peak and headroom",
        "real grants, ownership, search path, default privileges, and operational database access",
    } <= set(contract["handoff"]["final_verification_owned_facts"])

    for calculation in contract["budget_model"]["reported_calculations"].values():
        assert calculation is None
