"""Authentication and verification for Slack events."""

import hashlib
import hmac
import os
import time
from dataclasses import dataclass, fields
from functools import lru_cache

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request
from fastapi.logger import logger as fastapi_logger
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

load_dotenv()


@dataclass(frozen=True)
class AuthConfig:
    """A config class containing authorisation environment variables."""

    slack_signing_secret: str = os.getenv("SLACK_SIGNING_SECRET", "")
    dev_bearer_token: str = os.getenv("DEV_BEARER_TOKEN", "")

    def __post_init__(self) -> None:
        """A post-constructor method for the dataclass."""
        for field in fields(self):
            attr = getattr(self, field.name)

            if not attr:
                msg = f"Environment variable {field.name} is not set."
                fastapi_logger.error(msg)
                raise ValueError(msg)


@lru_cache
def _get_auth_tokens() -> AuthConfig:
    return AuthConfig()


BEARER = HTTPBearer(auto_error=False)


async def verify_slack_signature(request: Request) -> bool:
    """A function for verifying that a request is coming from Slack."""
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
            _get_auth_tokens().slack_signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256,
        ).hexdigest()
    )

    return hmac.compare_digest(computed_signature, slack_signature)


async def is_request_valid(
    request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(BEARER)
) -> None:
    """A function for verifying that a request is valid."""
    if credentials and credentials.credentials == _get_auth_tokens().dev_bearer_token:
        fastapi_logger.debug("Request is authenticated with bearer token.")
    elif await verify_slack_signature(request):
        fastapi_logger.debug("Request is verified as coming from Slack.")
    else:
        fastapi_logger.error(f"Failed to authenticate request: {request.headers}.")
        raise HTTPException(status_code=401, detail="Unauthorised.")

    fastapi_logger.info("Request authentication successful.")
