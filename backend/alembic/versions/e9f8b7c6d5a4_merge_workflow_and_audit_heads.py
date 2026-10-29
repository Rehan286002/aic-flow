"""Merge the workflow and extracted-field-review migration heads."""

from collections.abc import Sequence

revision: str = "e9f8b7c6d5a4"
down_revision: str | Sequence[str] | None = ("a3b4c5d6e7f8", "7ac1f92d4b60")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
