import sys
from pathlib import Path

# Ensure backend root is in sys.path for pytest discovery
BACKEND_DIR = str(Path(__file__).resolve().parents[1])
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy.orm import configure_mappers

from app.models import (
    ApplicationFieldDefinition,
    ApplicationFieldValue,
    ApplicationRevision,
)


def test_field_values_relationship_cascade_no_delete():
    """Verify that ApplicationRevision.field_values does NOT cascade delete or delete-orphan.

    PostgreSQL's ON DELETE RESTRICT constraint must govern foreign-key integrity,
    preserving historical revision self-disclosure values.
    """
    configure_mappers()
    rel = ApplicationRevision.__mapper__.relationships["field_values"]

    assert not rel.cascade.delete, (
        "ApplicationRevision.field_values must not include delete cascade"
    )
    assert not rel.cascade.delete_orphan, (
        "ApplicationRevision.field_values must not include delete-orphan"
    )
    assert rel.cascade.save_update, (
        "ApplicationRevision.field_values must support save-update"
    )
    assert rel.cascade.merge, "ApplicationRevision.field_values must support merge"
    assert rel.passive_deletes == "all", (
        "ApplicationRevision.field_values must set passive_deletes='all' "
        "to allow PostgreSQL ON DELETE RESTRICT to reject parent deletion"
    )


def test_field_definition_relationship_cascade_no_delete():
    """Verify that ApplicationFieldDefinition.field_values does NOT cascade delete or delete-orphan."""
    configure_mappers()
    rel = ApplicationFieldDefinition.__mapper__.relationships["field_values"]

    assert not rel.cascade.delete
    assert not rel.cascade.delete_orphan
    assert rel.passive_deletes == "all"


def test_application_field_value_fk_ondelete_restrict():
    """Verify that application_field_values foreign key to application_revisions specifies ON DELETE RESTRICT."""
    table = ApplicationFieldValue.__table__
    fk = next(
        fk
        for fk in table.foreign_keys
        if fk.column.table.name == "application_revisions"
    )
    assert fk.ondelete == "RESTRICT", (
        "ForeignKey to application_revisions must specify ondelete='RESTRICT'"
    )


def test_application_field_definition_check_constraint():
    """Verify the data_type check constraint matches Schema v4 exact values."""
    table = ApplicationFieldDefinition.__table__
    check_constraints = [
        c.sqltext.text
        for c in table.constraints
        if hasattr(c, "sqltext") and "chk_field_data_type" in c.name
    ]
    assert len(check_constraints) == 1
    constraint_sql = check_constraints[0]
    for expected_type in [
        "TEXT",
        "NUMBER",
        "DATE",
        "BOOLEAN",
        "JSON",
        "IDENTIFIER",
    ]:
        assert expected_type in constraint_sql


def test_application_field_value_uniqueness():
    """Verify uniqueness constraint on (application_revision_id, field_definition_id)."""
    table = ApplicationFieldValue.__table__
    unique_constraints = [
        [col.name for col in c.columns]
        for c in table.constraints
        if hasattr(c, "columns")
        and c.name == "uq_application_field_value_revision_field"
    ]
    assert len(unique_constraints) == 1
    assert sorted(unique_constraints[0]) == [
        "application_revision_id",
        "field_definition_id",
    ]
