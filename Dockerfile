# SRE Agent Container
# Multi-stage build for smaller image size

FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock README.md ./

# Install dependencies (without the project itself)
RUN uv sync --frozen --no-install-project

# Copy source code
COPY src/ src/

# Install the project
RUN uv sync --frozen


FROM python:3.13-slim-bookworm AS runtime

WORKDIR /app

# Copy the virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy source code (needed for prompt files)
COPY --from=builder /app/src /app/src

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Run one diagnosis job and then exit
CMD ["python", "-m", "sre_agent.run"]
