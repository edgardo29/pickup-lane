from __future__ import annotations

import pytest
from sqlalchemy import CheckConstraint, inspect

from backend.models import VenueImage
from backend.tests.support.migration_test_database import (
    model_schema_drift,
    run_alembic_upgrade,
)

pytestmark = pytest.mark.migration_lifecycle


@pytest.mark.pass_provenance("WS06-01", "WS06-02")
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
    indexes = {index["name"]: index for index in inspector.get_indexes("venue_images")}

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
    assert {
        "publication_object_key",
        "publication_content_type",
        "publication_size_bytes",
        "publication_etag",
        "upload_completed_at",
    }.issubset(columns)
    assert {
        "ck_venue_images_publication_tuple_complete",
        "ck_venue_images_publication_status",
        "ck_venue_images_publication_content_type",
        "ck_venue_images_publication_size_bytes",
        "ck_venue_images_publication_object_key_not_empty",
        "ck_venue_images_publication_etag_not_empty",
    }.issubset(checks)
    publication_index = indexes["uq_venue_images_publication_object_key"]
    assert publication_index["unique"] is True
    assert publication_index["column_names"] == ["publication_object_key"]
    assert "publication_object_key IS NOT NULL" in str(
        publication_index["dialect_options"]["postgresql_where"]
    )
    assert model_schema_drift(migration_database.engine) == ()
