FROM python:3.12-slim

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY ../../../pyproject.toml ../../../uv.lock ./

# Copy the application into the container.
COPY sre_agent/servers/prompt_server .

# Install the application dependencies.
WORKDIR /app
RUN uv pip install --no-cache --system -r /app/pyproject.toml

# Run the application.
CMD ["mcp", "run", "server.py", "--transport", "sse"]
