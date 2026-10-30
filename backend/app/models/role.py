from sqlalchemy import CheckConstraint, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Role(Base):
    __tablename__ = "roles"

    __table_args__ = (
        CheckConstraint(
            "role_code IN ('INSTITUTION_USER', 'INTAKE_OFFICER', 'SCRUTINY_OFFICER', "
            "'REGIONAL_OFFICER', 'EVC_COORDINATOR', 'EVC_MEMBER', 'COMMITTEE_SECRETARIAT', 'SAC_SECRETARIAT', 'COUNCIL_SECRETARIAT', "
            "'BUREAU_SUPERVISOR', 'COMPETENT_AUTHORITY', 'REGULATORY_POLICY_PUBLISHER', "
            "'AUDITOR', 'LEAD_AUDITOR', 'ADMIN')",
            name="chk_role_code",
        ),
    )

    role_id: Mapped[int] = mapped_column(
        SmallInteger,
        primary_key=True,
        autoincrement=True,
    )

    role_code: Mapped[str] = mapped_column(
        String(40),
        unique=True,
        nullable=False,
    )

    role_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
