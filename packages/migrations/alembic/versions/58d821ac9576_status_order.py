"""status_order

Revision ID: 58d821ac9576
Revises: 32824efe6b6b
Create Date: 2026-07-22 21:43:39.247957

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "58d821ac9576"
down_revision: Union[str, Sequence[str], None] = "32824efe6b6b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "responder_status_events",
        sa.Column("status_order", sa.Integer(), nullable=True),
    )

    responder_status_events = sa.table(
        "responder_status_events",
        sa.column("status", sa.Text()),
        sa.column("status_order", sa.Integer()),
    )
    status_upper = sa.func.upper(responder_status_events.c.status)
    op.get_bind().execute(
        sa.update(responder_status_events).values(
            status_order=sa.case(
                (status_upper == "DISPATCHED", 1),
                (status_upper == "ENROUTE", 2),
                (status_upper == "ARRIVED", 3),
                else_=0,
            )
        )
    )

    op.alter_column(
        "responder_status_events",
        "status_order",
        existing_type=sa.Integer(),
        nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("responder_status_events", "status_order")
