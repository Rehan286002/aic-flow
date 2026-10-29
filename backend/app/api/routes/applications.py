import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import (
    RoleAssignmentContext,
    get_current_user,
    get_db,
    require_institution_access,
    verify_csrf,
)
from app.models.user import User
from app.schemas.application import (
    ApplicationCreateRequest,
    ApplicationDetailResponse,
    ApplicationListItemResponse,
    ApplicationUpdateRequest,
)
from app.services.application_service import (
    create_application_draft,
    get_application_detail,
    list_institution_applications,
    update_application_draft,
)

router = APIRouter(
    prefix="/institutions/{institution_id}/applications",
    tags=["applications"],
)


@router.post(
    "",
    response_model=ApplicationDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a draft EoA application",
    description="Creates an initial draft application for the institution with Revision #1, status history, and service-derived checklist requirements.",
)
def create_application_endpoint(
    institution_id: uuid.UUID,
    payload: ApplicationCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    scope_context: Annotated[
        RoleAssignmentContext, Depends(require_institution_access)
    ],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> ApplicationDetailResponse:
    """Create draft application with RBAC verification and CSRF protection."""
    return create_application_draft(
        db=db,
        institution_id=institution_id,
        current_user_id=current_user.user_id,
        payload=payload,
    )


@router.get(
    "",
    response_model=list[ApplicationListItemResponse],
    status_code=status.HTTP_200_OK,
    summary="List institution applications",
    description="Returns all applications submitted or drafted by the authorized institution.",
)
def list_applications_endpoint(
    institution_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    scope_context: Annotated[
        RoleAssignmentContext, Depends(require_institution_access)
    ],
    db: Annotated[Session, Depends(get_db)],
) -> list[ApplicationListItemResponse]:
    """List applications within authorized institution scope."""
    return list_institution_applications(db=db, institution_id=institution_id)


@router.get(
    "/{application_id}",
    response_model=ApplicationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get application details",
    description="Returns detailed application information, active revision declarations, status history, and checklist requirements.",
)
def get_application_endpoint(
    institution_id: uuid.UUID,
    application_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    scope_context: Annotated[
        RoleAssignmentContext, Depends(require_institution_access)
    ],
    db: Annotated[Session, Depends(get_db)],
) -> ApplicationDetailResponse:
    """Retrieve full application details within authorized institution scope."""
    return get_application_detail(
        db=db,
        institution_id=institution_id,
        application_id=application_id,
    )


@router.patch(
    "/{application_id}",
    response_model=ApplicationDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Update draft self-disclosure declarations",
    description="Updates editable draft declarations (completion certificate date, payment applicability, remarks) and recalculates requirement applicability.",
)
def update_application_endpoint(
    institution_id: uuid.UUID,
    application_id: uuid.UUID,
    payload: ApplicationUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    scope_context: Annotated[
        RoleAssignmentContext, Depends(require_institution_access)
    ],
    _csrf: Annotated[str, Depends(verify_csrf)],
    db: Annotated[Session, Depends(get_db)],
) -> ApplicationDetailResponse:
    """Update draft application declarations with RBAC verification and CSRF protection."""
    return update_application_draft(
        db=db,
        institution_id=institution_id,
        application_id=application_id,
        current_user_id=current_user.user_id,
        payload=payload,
    )
