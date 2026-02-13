FROM python:3.12-slim

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY ../../pyproject.toml ../../uv.lock ./

COPY sre_agent/shared ./shared

COPY sre_agent/client .

RUN uv sync --frozen

EXPOSE 80

# Run the application.
CMD ["uv", "run", "uvicorn", "client:app", "--port", "80", "--host", "0.0.0.0"]
