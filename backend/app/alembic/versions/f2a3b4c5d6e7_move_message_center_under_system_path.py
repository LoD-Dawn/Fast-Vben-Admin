"""move message center to system path

Revision ID: f2a3b4c5d6e7
Revises: f1a2b3c4d5e6
Create Date: 2026-07-11 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2a3b4c5d6e7"
down_revision: str | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE menu
        SET route_path = '/system/message-center',
            updated_at = CURRENT_TIMESTAMP
        WHERE route_name = 'MessageCenter'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE menu
        SET route_path = '/message-center',
            updated_at = CURRENT_TIMESTAMP
        WHERE route_name = 'MessageCenter'
        """
    )
