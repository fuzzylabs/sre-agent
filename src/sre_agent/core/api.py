"""FastAPI HTTP service for the SRE Agent."""

import asyncio
import logging
import os
import signal
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from sre_agent.core.agent import diagnose_error
from sre_agent.core.config import get_config
from sre_agent.core.models import ErrorDiagnosis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_IDLE_MONITOR_INTERVAL_SECONDS = 5


@dataclass
class ApiActivityState:
    """Mutable API activity state for idle shutdown."""

    idle_timeout_seconds: int = 0
    last_activity_monotonic: float = field(default_factory=time.monotonic)
    inflight_diagnose_requests: int = 0


_activity_state = ApiActivityState()


def _load_idle_timeout_seconds() -> int:
    """Load API idle timeout seconds from environment."""
    raw_value = os.getenv("API_IDLE_TIMEOUT_SECONDS", "0").strip()
    if not raw_value:
        return 0
    try:
        value = int(raw_value)
    except ValueError:
        logger.warning(f"Invalid API_IDLE_TIMEOUT_SECONDS value '{raw_value}', disabling timeout.")
        return 0
    if value < 0:
        logger.warning("API_IDLE_TIMEOUT_SECONDS cannot be negative, disabling timeout.")
        return 0
    return value


def _mark_activity() -> None:
    """Record API activity timestamp."""
    _activity_state.last_activity_monotonic = time.monotonic()


async def _idle_shutdown_monitor() -> None:
    """Stop the process when API has been idle beyond configured timeout."""
    if _activity_state.idle_timeout_seconds <= 0:
        return

    while True:
        await asyncio.sleep(_IDLE_MONITOR_INTERVAL_SECONDS)
        idle_for = time.monotonic() - _activity_state.last_activity_monotonic
        if _activity_state.inflight_diagnose_requests > 0:
            continue
        if idle_for < _activity_state.idle_timeout_seconds:
            continue

        logger.info(
            "API idle timeout reached "
            f"({_activity_state.idle_timeout_seconds}s). Stopping the task process."
        )
        os.kill(os.getpid(), signal.SIGTERM)
        return


class DiagnoseRequest(BaseModel):
    """Request body for the diagnose endpoint."""

    log_group: str = Field(description="CloudWatch log group to analyse")
    service_name: str = Field(description="Service to that triggers the error")
    time_range_minutes: int = Field(default=10, ge=1, le=1440, description="Time range in minutes")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    version: str = "0.2.0"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler."""
    monitor_task: asyncio.Task[None] | None = None

    # Validate config on startup
    try:
        config = get_config()
        logger.info(f"SRE Agent starting with model: {config.model}")
        logger.info(f"AWS Region: {config.aws.region}")
        logger.info(f"Slack MCP URL: {config.slack.mcp_url}")
        logger.info(f"GitHub MCP URL: {config.github.mcp_url}")
    except Exception as e:
        logger.error(f"Configuration error: {e}")
        raise

    _activity_state.idle_timeout_seconds = _load_idle_timeout_seconds()
    _activity_state.inflight_diagnose_requests = 0
    _mark_activity()

    if _activity_state.idle_timeout_seconds > 0:
        logger.info(f"API idle timeout enabled: {_activity_state.idle_timeout_seconds}s")
        monitor_task = asyncio.create_task(_idle_shutdown_monitor())

    yield

    if monitor_task is not None:
        monitor_task.cancel()
        with suppress(asyncio.CancelledError):
            await monitor_task

    logger.info("SRE Agent shutting down")


app = FastAPI(
    title="SRE Agent API",
    description="AI-powered Site Reliability Engineering agent for error diagnosis",
    version="0.2.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def track_diagnose_activity(
    request: Request,
    call_next: Callable[[Request], Awaitable[object]],
) -> object:
    """Track diagnose request activity for idle shutdown."""
    if request.url.path != "/diagnose":
        return await call_next(request)

    _activity_state.inflight_diagnose_requests += 1
    _mark_activity()
    try:
        response = await call_next(request)
    finally:
        _activity_state.inflight_diagnose_requests = max(
            0,
            _activity_state.inflight_diagnose_requests - 1,
        )
        _mark_activity()
    return response


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint for liveness/readiness probes."""
    return HealthResponse()


@app.post("/diagnose", response_model=ErrorDiagnosis)
async def diagnose(request: DiagnoseRequest) -> ErrorDiagnosis:
    """Diagnose errors in a CloudWatch log group.

    The agent will:
    1. Create a Slack thread to report the investigation
    2. Query CloudWatch for error logs
    3. Search GitHub for relevant code (if errors found)
    4. Reply to the Slack thread with findings
    """
    logger.info(f"Diagnosing errors in {request.log_group}")

    try:
        result = await diagnose_error(
            log_group=request.log_group,
            service_name=request.service_name,
            time_range_minutes=request.time_range_minutes,
        )
        return result
    except Exception as e:
        logger.exception(f"Diagnosis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
