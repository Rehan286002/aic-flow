from types import SimpleNamespace
from uuid import uuid4

from app.services.document_upload_service import has_document_scope_access


def context(role_code: str, institution_id=None, review_team_id=None):
    return SimpleNamespace(
        role_code=role_code,
        institution_id=institution_id,
        review_team_id=review_team_id,
    )


def test_institution_user_can_access_documents_only_for_their_institution():
    institution_id = uuid4()
    other_institution_id = uuid4()

    assert has_document_scope_access(
        institution_id, None, [context("INSTITUTION_USER", institution_id=institution_id)]
    )
    assert not has_document_scope_access(
        other_institution_id, None, [context("INSTITUTION_USER", institution_id=institution_id)]
    )


def test_processing_roles_are_limited_to_the_application_review_team():
    review_team_id = uuid4()
    other_team_id = uuid4()

    assert has_document_scope_access(
        uuid4(), review_team_id, [context("SCRUTINY_OFFICER", review_team_id=review_team_id)]
    )
    assert has_document_scope_access(
        uuid4(), review_team_id, [context("SAC_SECRETARIAT", review_team_id=review_team_id)]
    )
    assert not has_document_scope_access(
        uuid4(), review_team_id, [context("SCRUTINY_OFFICER", review_team_id=other_team_id)]
    )


def test_intake_officer_can_access_unassigned_intake_case_documents():
    assert has_document_scope_access(
        uuid4(), None, [context("INTAKE_OFFICER", review_team_id=uuid4())]
    )


def test_platform_administrator_has_global_document_access():
    assert has_document_scope_access(
        uuid4(), uuid4(), [context("ADMIN")]
    )


def test_unrelated_review_roles_do_not_gain_document_access():
    assert not has_document_scope_access(
        uuid4(), uuid4(), [context("EVC_MEMBER", review_team_id=uuid4())]
    )
