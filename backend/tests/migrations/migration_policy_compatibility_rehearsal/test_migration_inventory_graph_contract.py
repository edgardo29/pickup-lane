from __future__ import annotations

from pathlib import Path

import pytest

from backend.tests.support.migration_inventory import (
    assert_linear_revision_chain,
    build_migration_operation_inventory,
    load_migration_revisions,
)
from backend.tests.support.migration_test_database import (
    alembic_head_revision,
    alembic_parent_revision,
    alembic_script_directory,
)

pytestmark = pytest.mark.no_db_cleanup

_REPO_ROOT = Path(__file__).resolve().parents[4]
_VERSIONS_DIR = _REPO_ROOT / "backend" / "alembic" / "versions"
_EXPECTED_CURRENT_REVISION_COUNT = 66
_EXPECTED_CURRENT_BASE = "0001_pg_trgm"
_EXPECTED_CURRENT_HEAD = "0066_review_case_resolution_refs"


@pytest.mark.requirement("WS04-03A-R2", "WS04-03A-R3", "WS04-03A-R8")
def test_current_alembic_revision_chain_is_linear_and_complete() -> None:
    revisions = load_migration_revisions(_VERSIONS_DIR)

    assert len(revisions) == _EXPECTED_CURRENT_REVISION_COUNT
    assert revisions[0].path.name == "0001_enable_pg_trgm_extension.py"
    assert revisions[-1].path.name == (
        "0066_create_admin_review_case_resolution_references_table.py"
    )

    assert_linear_revision_chain(revisions)

    assert [
        revision.revision for revision in revisions if revision.down_revision is None
    ] == [_EXPECTED_CURRENT_BASE]
    assert alembic_head_revision() == _EXPECTED_CURRENT_HEAD
    assert alembic_parent_revision(_EXPECTED_CURRENT_HEAD) == "0065_payment_method_ops"

    script = alembic_script_directory()
    assert script.get_heads() == [_EXPECTED_CURRENT_HEAD]
    assert script.get_bases() == [_EXPECTED_CURRENT_BASE]


@pytest.mark.requirement("WS04-03A-R2", "WS04-03A-R5", "WS04-03A-R6", "WS04-03A-R7")
def test_current_migration_operation_inventory_classifies_upgrade_side_operations() -> (
    None
):
    inventory = build_migration_operation_inventory(_VERSIONS_DIR)

    assert inventory.revision_count == _EXPECTED_CURRENT_REVISION_COUNT
    assert inventory.base_revisions == (_EXPECTED_CURRENT_BASE,)
    assert inventory.head_revisions == (_EXPECTED_CURRENT_HEAD,)
    assert inventory.risky_upgrade_findings == ()

    assert {
        "constraint_creation",
        "extension_setup",
        "ordinary_index_creation",
        "sequence_setup",
        "table_creation",
    } <= set(inventory.operation_categories)


@pytest.mark.requirement("WS04-03A-R2", "WS04-03A-R5", "WS04-03A-R6", "WS04-03A-R8")
def test_migration_inventory_fails_closed_for_unclassified_risky_patterns(
    tmp_path: Path,
) -> None:
    versions_dir = tmp_path / "versions"
    versions_dir.mkdir()
    (versions_dir / "0001_base.py").write_text(
        "revision = 'base'\n"
        "down_revision = None\n"
        "branch_labels = None\n"
        "depends_on = None\n\n"
        "from alembic import op\n\n"
        "def upgrade():\n"
        "    op.drop_column('users', 'email')\n\n"
        "def downgrade():\n"
        "    pass\n"
    )

    inventory = build_migration_operation_inventory(versions_dir)

    assert inventory.risky_upgrade_findings == (
        "0001_base.py: upgrade uses op.drop_column",
    )


@pytest.mark.requirement("WS04-03A-R2", "WS04-03A-R5", "WS04-03A-R6", "WS04-03A-R8")
def test_raw_sql_inventory_flags_mixed_reviewed_and_destructive_sql(
    tmp_path: Path,
) -> None:
    versions_dir = tmp_path / "versions"
    versions_dir.mkdir()
    (versions_dir / "0001_base.py").write_text(
        "revision = 'base'\n"
        "down_revision = None\n"
        "branch_labels = None\n"
        "depends_on = None\n\n"
        "from alembic import op\n\n"
        "def upgrade():\n"
        "    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm; DROP TABLE users')\n\n"
        "def downgrade():\n"
        "    pass\n"
    )

    inventory = build_migration_operation_inventory(versions_dir)

    assert inventory.risky_upgrade_findings == (
        "0001_base.py: op.execute contains DROP",
        "0001_base.py: op.execute uses unreviewed extension SQL",
    )


@pytest.mark.requirement("WS04-03A-R2", "WS04-03A-R5", "WS04-03A-R6", "WS04-03A-R8")
def test_raw_sql_inventory_requires_exact_reviewed_extension_forms(
    tmp_path: Path,
) -> None:
    versions_dir = tmp_path / "versions"
    versions_dir.mkdir()
    (versions_dir / "0001_base.py").write_text(
        "revision = 'base'\n"
        "down_revision = None\n"
        "branch_labels = None\n"
        "depends_on = None\n\n"
        "from alembic import op\n\n"
        "def upgrade():\n"
        "    op.execute('CREATE EXTENSION IF NOT EXISTS another_extension')\n\n"
        "def downgrade():\n"
        "    pass\n"
    )

    inventory = build_migration_operation_inventory(versions_dir)

    assert inventory.risky_upgrade_findings == (
        "0001_base.py: op.execute uses unreviewed extension SQL",
    )


@pytest.mark.requirement("WS04-03A-R2", "WS04-03A-R5", "WS04-03A-R6", "WS04-03A-R8")
def test_raw_sql_inventory_distinguishes_update_trigger_ddl_from_data_update(
    tmp_path: Path,
) -> None:
    versions_dir = tmp_path / "versions"
    versions_dir.mkdir()
    (versions_dir / "0001_base.py").write_text(
        "revision = 'base'\n"
        "down_revision = None\n"
        "branch_labels = None\n"
        "depends_on = None\n\n"
        "from alembic import op\n\n"
        "def upgrade():\n"
        '    op.execute("""CREATE TRIGGER trg_items_immutable '
        'BEFORE UPDATE ON items FOR EACH ROW EXECUTE FUNCTION reject_item_update()""")\n'
        "    op.execute(\"UPDATE items SET status = 'active'\")\n\n"
        "def downgrade():\n"
        "    pass\n"
    )

    inventory = build_migration_operation_inventory(versions_dir)

    assert inventory.risky_upgrade_findings == (
        "0001_base.py: op.execute contains UPDATE",
    )
