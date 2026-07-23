"""init

Revision ID: 32824efe6b6b
Revises: 
Create Date: 2026-07-22 21:36:50.839161

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '32824efe6b6b'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS locations (
            id          bigserial PRIMARY KEY,
            raw_text    text NOT NULL UNIQUE,
            latitude    double precision,
            longitude   double precision,
            created_at  timestamptz NOT NULL DEFAULT now(),
            updated_at  timestamptz NOT NULL DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS events (
            id            bigserial PRIMARY KEY,
            external_id   char(64) NOT NULL UNIQUE,
            time_received timestamptz NOT NULL,
            call_type     text NOT NULL,
            location      text NOT NULL,
            location_id   bigint REFERENCES locations (id),
            created_at    timestamptz NOT NULL DEFAULT now(),
            updated_at    timestamptz NOT NULL DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS responders (
            id             bigserial PRIMARY KEY,
            event_id       bigint NOT NULL REFERENCES events (id),
            unit           text NOT NULL,
            dispatch_area  text NOT NULL,
            agency         text NOT NULL,
            created_at     timestamptz NOT NULL DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS responder_status_events (
            id           bigserial PRIMARY KEY,
            responder_id bigint NOT NULL REFERENCES responders (id),
            status       text NOT NULL,
            created_at   timestamptz NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_events_external_id ON events (external_id);
        CREATE INDEX IF NOT EXISTS idx_events_time_received ON events (time_received DESC);
        CREATE INDEX IF NOT EXISTS idx_responders_event_id ON responders (event_id);
        CREATE INDEX IF NOT EXISTS idx_responder_status_events_responder_id
            ON responder_status_events (responder_id, created_at DESC);
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        """
        DROP INDEX IF EXISTS idx_responder_status_events_responder_id;
        DROP INDEX IF EXISTS idx_responders_event_id;
        DROP INDEX IF EXISTS idx_events_time_received;
        DROP INDEX IF EXISTS idx_events_external_id;

        DROP TABLE IF EXISTS responder_status_events;
        DROP TABLE IF EXISTS responders;
        DROP TABLE IF EXISTS events;
        DROP TABLE IF EXISTS locations;
        """
    )
