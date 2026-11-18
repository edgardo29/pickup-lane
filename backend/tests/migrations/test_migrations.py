"""The standard pytest-alembic migration checks.

- test_single_head_revision: the migrations form one line, with no forks.
- test_upgrade: every migration applies, from empty to the latest.
- test_model_definitions_match_ddl: the migrated schema matches the models.
- test_up_down_consistency: every migration can be undone.
"""

from pytest_alembic.tests import (  # noqa: F401 - pytest collects these by name.
    test_model_definitions_match_ddl,
    test_single_head_revision,
    test_up_down_consistency,
    test_upgrade,
)
