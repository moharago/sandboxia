# =============================================================================
# FastAPI + LangGraph Server Dockerfile
# =============================================================================
# - Multi-stage build
# - Reproducible dependency install via uv + uv.lock
# - Slim runtime image
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /app

# (Optional but common) build deps only in builder stage
# If your dependencies include native extensions, this is typically required.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv (PIN the version for reproducible builds)
# Change 0.9.30 to the version you want to pin.
COPY --from=ghcr.io/astral-sh/uv:0.9.30 /uv /usr/local/bin/uv

# Copy dependency files first (better layer caching)
COPY pyproject.toml uv.lock ./

# Install dependencies into a local venv
# --frozen: fail if lock doesn't match
# --no-dev: exclude dev deps
# --no-install-project: install deps only (project itself is run from source)
RUN uv sync --frozen --no-dev --no-install-project

# -----------------------------------------------------------------------------
# Stage 2: Runtime
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY app ./app
COPY main.py ./

# Create data directory for ChromaDB (if using local persist)
RUN mkdir -p /app/data/chroma

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run uvicorn from the venv explicitly (avoids PATH surprises)
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
