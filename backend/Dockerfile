# Multi-stage production Dockerfile for AIC-Flow Backend
# Python 3.13-slim with uv package manager and unprivileged execution

FROM ghcr.io/astral-sh/uv:0.10.0 AS uv-bin
FROM python:3.13-slim AS builder

WORKDIR /app

# Install uv from official image
COPY --from=uv-bin /uv /uvx /bin/

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency specifications
COPY pyproject.toml uv.lock* ./

# Install python dependencies without development packages
RUN uv sync --frozen --no-dev --no-install-project

# Final runtime image
FROM python:3.13-slim AS runner

WORKDIR /app

# Create non-root system user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

# Install runtime system libraries required by OCR & image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy backend source tree
COPY . /app

# Change ownership to unprivileged user
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

