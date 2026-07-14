FROM python:3.11-slim

LABEL org.opencontainers.image.title="OpenAlex Local API"
LABEL org.opencontainers.image.description="Local OpenAlex database HTTP relay (FTS5 over 284M+ works)"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.authors="SciTeX Team"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# openalex-local ships the `relay` FastAPI server in its [server] extra.
# The fastapi/starlette pins are belt-and-suspenders: without an explicit
# starlette bound a build can resolve fastapi 0.128 + starlette 1.2, an
# incompatible pair that crashes relay at import with
#   TypeError: Router.__init__() got an unexpected keyword argument 'on_startup'
# (openalex-local's own pyproject is also being bounded; this pin makes the
# image self-protecting even against an older openalex-local.)
RUN pip install --no-cache-dir \
    "openalex-local[server]>=0.7.9" \
    "fastapi>=0.115,<0.128" \
    "starlette>=0.40,<0.48"

# The database is mounted read-only as a volume. Point the package at it
# explicitly: openalex_local get_db_path() honors OPENALEX_LOCAL_DB first,
# before any auto-detect (mirrors crossref's CROSSREF_DB_PATH).
VOLUME ["/data"]
ENV OPENALEX_LOCAL_DB=/data/openalex.db
ENV OPENALEX_LOCAL_PORT=31292
ENV OPENALEX_LOCAL_HOST=0.0.0.0

EXPOSE 31292

# Health check hits the relay's /health, which reports database_connected.
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:31292/health || exit 1

CMD ["openalex-local", "relay", "--host", "0.0.0.0", "--port", "31292"]
