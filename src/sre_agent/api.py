"""FastAPI HTTP service for the SRE Agent."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from sre_agent import diagnose_error, get_config
from sre_agent.models import ErrorDiagnosis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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

    yield

    logger.info("SRE Agent shutting down")


app = FastAPI(
    title="SRE Agent API",
    description="AI-powered Site Reliability Engineering agent for error diagnosis",
    version="0.2.0",
    lifespan=lifespan,
)


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
