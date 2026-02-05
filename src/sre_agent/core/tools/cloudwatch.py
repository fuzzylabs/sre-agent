"""CloudWatch implementation of the LoggingInterface."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import boto3
from botocore.exceptions import ClientError
from pydantic_ai import FunctionToolset

from sre_agent.core.config import AgentConfig
from sre_agent.core.interfaces import LoggingInterface
from sre_agent.core.models import LogEntry, LogQueryResult

logger = logging.getLogger(__name__)


class CloudWatchLogging(LoggingInterface):
    """CloudWatch Logs implementation."""

    def __init__(self, region: str | None = None) -> None:
        """Initialise CloudWatch client."""
        self._client: Any = boto3.client("logs", region_name=region)

    async def query_errors(
        self,
        source: str,
        service_name: str,
        time_range_minutes: int = 10,
    ) -> LogQueryResult:
        """Query error logs from CloudWatch.

        Args:
            source: The CloudWatch log group name.
            service_name: Service name to filter log entries.
            time_range_minutes: How far back to search.

        Returns:
            LogQueryResult with matching error entries.
        """
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(minutes=time_range_minutes)

        service_filter = service_name.replace('"', '\\"')
        filter_pattern = (
            "{ "
            '$.log_processed.severity = "error" '
            f'&& $.log_processed.service = "{service_filter}" '
            "}"
        )

        logger.info(f"CloudWatch filter pattern: {filter_pattern}")
        logger.info(f"Log Group: {source}")
        logger.info(f"Time Range: {start_time} to {end_time}")

        try:
            response = self._client.filter_log_events(
                logGroupName=source,
                startTime=int(start_time.timestamp() * 1000),
                endTime=int(end_time.timestamp() * 1000),
                filterPattern=filter_pattern,
                limit=20,
            )
            entries = self._parse_events(response.get("events", []))
            logger.info(f"Found {len(entries)} log entries")

            return LogQueryResult(
                entries=entries,
                log_group=source,
                query=filter_pattern,
            )
        except ClientError as e:
            logger.error(f"CloudWatch query failed: {e}")
            raise RuntimeError(f"Failed to query CloudWatch: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise RuntimeError(f"Unexpected error querying logs: {e}") from e

    def _parse_events(self, events: list[dict[str, Any]]) -> list[LogEntry]:
        """Parse filter_log_events entries into LogEntry objects."""
        entries = []
        for event in events:
            timestamp_ms = event.get("timestamp")
            if timestamp_ms is None:
                timestamp = ""
            else:
                timestamp = datetime.fromtimestamp(timestamp_ms / 1000, UTC).isoformat()
            entries.append(
                LogEntry(
                    timestamp=timestamp,
                    message=event.get("message", ""),
                    log_stream=event.get("logStreamName"),
                )
            )
        entries.sort(key=lambda entry: entry.timestamp, reverse=True)
        return entries


def create_cloudwatch_toolset(config: AgentConfig) -> FunctionToolset:
    """Create a FunctionToolset with CloudWatch tools for pydantic-ai."""
    toolset = FunctionToolset()
    cw_logging = CloudWatchLogging(region=config.aws.region)

    @toolset.tool
    async def search_error_logs(
        log_group: str,
        service_name: str,
        time_range_minutes: int = 10,
    ) -> LogQueryResult:
        """Search CloudWatch logs for errors.

        Args:
            log_group: The CloudWatch log group name
            service_name: Service name to filter log entries (e.g., 'cartservice')
            time_range_minutes: How far back to search (default: 10 minutes)

        Returns:
            LogQueryResult containing matching error log entries
        """
        return await cw_logging.query_errors(log_group, service_name, time_range_minutes)

    return toolset
