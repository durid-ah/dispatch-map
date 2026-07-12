CREATE TABLE locations (
    id          bigserial PRIMARY KEY,
    raw_text    text NOT NULL UNIQUE,
    latitude    double precision,
    longitude   double precision,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE events (
    id            bigserial PRIMARY KEY,
    external_id   char(64) NOT NULL UNIQUE,
    time_received timestamptz NOT NULL,
    call_type     text NOT NULL,
    location      text NOT NULL,
    location_id   bigint REFERENCES locations (id),
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE responders (
    id             bigserial PRIMARY KEY,
    event_id       bigint NOT NULL REFERENCES events (id),
    unit           text NOT NULL,
    dispatch_area  text NOT NULL,
    agency         text NOT NULL,
    created_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE responder_status_events (
    id           bigserial PRIMARY KEY,
    responder_id bigint NOT NULL REFERENCES responders (id),
    status       text NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_events_external_id ON events (external_id);
CREATE INDEX idx_events_time_received ON events (time_received DESC);
CREATE INDEX idx_responders_event_id ON responders (event_id);
CREATE INDEX idx_responder_status_events_responder_id ON responder_status_events (responder_id, created_at DESC);
