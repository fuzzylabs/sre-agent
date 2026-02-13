FROM python:3.12-slim

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY ../../pyproject.toml ../../uv.lock ./

# Copy the application into the container.
COPY sre_agent/firewall .

RUN uv pip install --no-cache --system -r /app/pyproject.toml

RUN apt-get -y update; apt-get -y install curl

EXPOSE 8000

# Run the application.
CMD ["uvicorn",  "firewall:app", "--port", "8000", "--host", "0.0.0.0", "--lifespan=on"]

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
