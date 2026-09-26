# Production Dockerfile for NYAYA-SATYA
# Security-hardened, non-root, multi-stage minimal build

FROM python:3.12-slim AS builder

WORKDIR /app

# Install build prerequisites
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast, reliable dependency resolution
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /bin/uv

# Copy dependency definition
COPY pyproject.toml .

# Install dependencies into virtual environment
RUN uv venv /opt/venv --python 3.12 && \
    uv pip install --python /opt/venv/bin/python --no-cache .

# ============================================================================
# Final Production Runtime Stage
# ============================================================================
FROM python:3.12-slim AS runner

WORKDIR /app

# Create unprivileged user and group
RUN groupadd -g 10001 nyaya && \
    useradd -u 10001 -g nyaya -s /bin/bash -m nyaya

# Install minimal runtime libraries (curl for container healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application source tree
COPY . /app

# Setup writable quarantine and scratch directories owned by unprivileged user
RUN mkdir -p /app/.quarantine /app/scratch /tmp/quarantine && \
    chown -R nyaya:nyaya /app /tmp/quarantine

# Run as non-root user
USER nyaya

# Environment variables for production safety
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    UNWIND_ENV=production

EXPOSE 8080

# Healthcheck probing the liveness endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Production entrypoint
CMD ["uvicorn", "services.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
