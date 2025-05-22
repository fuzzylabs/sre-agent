FROM python:3.12-slim

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY ../../pyproject.toml ../../uv.lock ./

# Copy the application into the container.
COPY sre_agent/client .

RUN uv pip install --no-cache --system -r /app/pyproject.toml

EXPOSE 80

# Run the application.
CMD ["uvicorn", "client:app", "--port", "80", "--host", "0.0.0.0"]
