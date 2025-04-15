FROM python:3.12-slim

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy the application into the container.
COPY sre_agent/client /app
COPY pyproject.toml /app
COPY uv.lock /app
COPY README.md /app

# Install the application dependencies.
WORKDIR /app
RUN uv sync --frozen --no-cache --no-dev

# Run the application.
CMD ["/app/.venv/bin/fastapi", "run", "client.py", "--port", "80", "--host", "0.0.0.0"]
