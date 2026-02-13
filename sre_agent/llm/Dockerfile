FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && apt-get -y install curl

WORKDIR /app

COPY  ../../uv.lock ./

COPY sre_agent/shared ./shared

# Copy the application into the container.
COPY sre_agent/llm .

RUN uv sync --frozen

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "main:app", "--port", "8000", "--host", "0.0.0.0"]

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
