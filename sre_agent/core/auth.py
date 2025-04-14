"""Authentication and verification for Slack events."""

import hashlib
import hmac
import logging
import os
import time

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request
from fastapi.logger import logger as fastapi_logger
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

load_dotenv()

gunicorn_error_logger = logging.getLogger("gunicorn.error")
gunicorn_logger = logging.getLogger("gunicorn")
uvicorn_access_logger = logging.getLogger("uvicorn.access")
uvicorn_access_logger.handlers = gunicorn_error_logger.handlers

fastapi_logger.handlers = gunicorn_error_logger.handlers
fastapi_logger.setLevel(logging.DEBUG)

SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
DEV_BEARER_TOKEN = os.getenv("DEV_BEARER_TOKEN")

BEARER = HTTPBearer(auto_error=False)


async def verify_slack_signature(request: Request) -> bool:
    """A function for verifying that a request is coming from Slack."""
    if SLACK_SIGNING_SECRET is None:
        fastapi_logger.error("SLACK_SIGNING_SECRET is not set.")
        raise ValueError("Environment variable SLACK_SIGNING_SECRET is not set.")

    body = await request.body()

    timestamp = request.headers.get("X-Slack-Request-Timestamp")
    slack_signature = request.headers.get("X-Slack-Signature")

    if not timestamp or not slack_signature:
        return False

    if abs(time.time() - int(timestamp)) > 60 * 5:
        return False

    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    computed_signature = (
        "v0="
        + hmac.new(
            SLACK_SIGNING_SECRET.encode(), sig_basestring.encode(), hashlib.sha256
        ).hexdigest()
    )

    return hmac.compare_digest(computed_signature, slack_signature)


async def is_request_valid(
    request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(BEARER)
) -> None:
    """A function for verifying that a request is valid."""
    if DEV_BEARER_TOKEN is None:
        fastapi_logger.error("DEV_BEARER_TOKEN is not set.")
        raise ValueError("Environment variable DEV_BEARER_TOKEN is not set.")

    if credentials and credentials.credentials == DEV_BEARER_TOKEN:
        fastapi_logger.debug("Request is authenticated with bearer token.")
    elif await verify_slack_signature(request):
        fastapi_logger.debug("Request is verified as coming from Slack.")
    else:
        fastapi_logger.error(f"Failed to authenticate request: {request.headers}.")
        raise HTTPException(status_code=401, detail="Unauthorised.")

    fastapi_logger.info("Request authentication successful.")
