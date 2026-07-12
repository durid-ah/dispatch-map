FROM postgres:16-alpine

ENV POSTGRES_USER=dispatch \
    POSTGRES_PASSWORD=dispatch \
    POSTGRES_DB=dispatch_map

COPY init/ /docker-entrypoint-initdb.d/

HEALTHCHECK --interval=5s --timeout=5s --retries=5 \
  CMD pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" || exit 1
