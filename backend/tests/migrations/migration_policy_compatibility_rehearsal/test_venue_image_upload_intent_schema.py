from __future__ import annotations

import pytest
from sqlalchemy import CheckConstraint, inspect

from backend.models import VenueImage
from backend.tests.support.migration_test_database import (
    model_schema_drift,
    run_alembic_upgrade,
)

pytestmark = pytest.mark.migration_lifecycle


def test_venue_image_upload_intent_schema_matches_model(migration_database) -> None:
    run_alembic_upgrade("head")
    inspector = inspect(migration_database.engine)
    columns = {
        column["name"]: column for column in inspector.get_columns("venue_images")
    }
    checks = {
        constraint["name"]: constraint["sqltext"]
        for constraint in inspector.get_check_constraints("venue_images")
    }
    model_checks = {
        constraint.name: str(constraint.sqltext)
        for constraint in VenueImage.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert columns["upload_expires_at"]["nullable"] is True
    assert columns["upload_expires_at"]["type"].timezone is True
    assert checks["ck_venue_images_pending_upload_intent"] == (
        "image_status::text <> 'pending_upload'::text OR "
        "upload_expires_at IS NOT NULL AND upload_completed_at IS NULL"
    )
    assert model_checks["ck_venue_images_pending_upload_intent"] == (
        "image_status <> 'pending_upload' OR "
        "(upload_expires_at IS NOT NULL AND upload_completed_at IS NULL)"
    )
    assert model_schema_drift(migration_database.engine) == ()
