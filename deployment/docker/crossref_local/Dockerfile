FROM python:3.11-slim

LABEL org.opencontainers.image.title="CrossRef Local API"
LABEL org.opencontainers.image.description="Fast local CrossRef database API server"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.authors="SciTeX Team"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server.py .
COPY database.py .
COPY models.py .
COPY config.py .

# Database will be mounted as volume
VOLUME ["/data"]

# Environment variables
ENV CROSSREF_DB_PATH=/data/crossref.db
ENV LOG_LEVEL=INFO
ENV WORKERS=4

# Expose port
EXPOSE 31291

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:31291/health || exit 1

# Run server
CMD uvicorn server:app \
    --host 0.0.0.0 \
    --port 31291 \
    --workers ${WORKERS} \
    --log-level ${LOG_LEVEL}
