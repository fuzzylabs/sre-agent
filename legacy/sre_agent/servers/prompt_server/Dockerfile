FROM python:3.12-slim

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY ../../../pyproject.toml ../../../uv.lock ./

# Copy the application into the container.
COPY sre_agent/servers/prompt_server .

# Install netcat
RUN apt-get update && apt-get -y install curl

# Install the application dependencies.
WORKDIR /app
RUN uv pip install --no-cache --system -r /app/pyproject.toml

CMD ["uvicorn", "server:app", "--port", "3001", "--host", "0.0.0.0"]

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:3001/health || exit 1
