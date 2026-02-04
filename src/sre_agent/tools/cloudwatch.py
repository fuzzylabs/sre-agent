"""CloudWatch implementation of the LoggingInterface."""

import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import boto3
from botocore.exceptions import ClientError
from pydantic_ai import FunctionToolset

from sre_agent.config import AgentConfig
from sre_agent.interfaces import LoggingInterface
from sre_agent.models import LogEntry, LogQueryResult

logger = logging.getLogger(__name__)

_TERMINAL_STATUSES = {"Complete", "Failed", "Cancelled", "Timeout", "Unknown"}


class CloudWatchLogging(LoggingInterface):
    """CloudWatch Logs implementation."""

    def __init__(self, region: str | None = None) -> None:
        """Initialise CloudWatch client."""
        self._client: Any = boto3.client("logs", region_name=region)

    async def query_errors(
        self,
        source: str,
        time_range_minutes: int = 10,
        service_name: str | None = None,
    ) -> LogQueryResult:
        """Query error logs from CloudWatch.

        Args:
            source: The CloudWatch log group name.
            time_range_minutes: How far back to search.
            service_name: Optional service name to filter log streams.

        Returns:
            LogQueryResult with matching error entries.
        """
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(minutes=time_range_minutes)

        query_parts = [
            "fields @timestamp, @message, @logStream",
            "filter @message like /(?i)error|exception|fatal|critical/",
        ]

        if service_name:
            query_parts.append(f"filter @logStream like /{service_name}/")

        query_parts.extend(["sort @timestamp desc", "limit 20"])
        query_string = " | ".join(query_parts)

        logger.info(f"CloudWatch Query: {query_string}")
        logger.info(f"Log Group: {source}")
        logger.info(f"Time Range: {start_time} to {end_time}")

        try:
            response = self._client.start_query(
                logGroupName=source,
                startTime=int(start_time.timestamp()),
                endTime=int(end_time.timestamp()),
                queryString=query_string,
            )
            query_id = response["queryId"]
            logger.info(f"Query ID: {query_id}")

            results = self._wait_for_results(query_id)
            entries = self._parse_results(results)

            logger.info(f"Found {len(entries)} log entries")

            return LogQueryResult(
                entries=entries,
                log_group=source,
                query=query_string,
            )
        except ClientError as e:
            logger.error(f"CloudWatch query failed: {e}")
            raise RuntimeError(f"Failed to query CloudWatch: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise RuntimeError(f"Unexpected error querying logs: {e}") from e

    def list_log_streams(
        self,
        log_group: str,
        prefix: str | None = None,
        limit: int = 20,
    ) -> list[str]:
        """List log streams in a log group."""
        try:
            kwargs: dict[str, Any] = {
                "logGroupName": log_group,
                "orderBy": "LastEventTime",
                "descending": True,
                "limit": limit,
            }
            if prefix:
                kwargs["logStreamNamePrefix"] = prefix

            response = self._client.describe_log_streams(**kwargs)
            streams = [stream["logStreamName"] for stream in response.get("logStreams", [])]
            logger.info(f"Found {len(streams)} log streams: {streams[:5]}...")
            return streams
        except ClientError as e:
            raise RuntimeError(f"Failed to list log streams: {e}") from e

    def _wait_for_results(self, query_id: str) -> list[list[dict[str, str]]]:
        """Wait for query to complete."""
        max_attempts = 30
        for attempt in range(max_attempts):
            time.sleep(1)
            response = self._client.get_query_results(queryId=query_id)
            status = response["status"]
            logger.debug(f"Query status (attempt {attempt + 1}): {status}")

            if status == "Complete":
                results: list[list[dict[str, str]]] = response.get("results", [])
                return results
            elif status in {"Failed", "Cancelled", "Timeout"}:
                raise RuntimeError(f"CloudWatch query {status.lower()}: {query_id}")

        raise RuntimeError(f"CloudWatch query timed out after {max_attempts} seconds")

    def _parse_results(self, results: list[list[dict[str, str]]]) -> list[LogEntry]:
        """Parse query results into LogEntry objects."""
        entries = []
        for result in results:
            data = {field["field"]: field["value"] for field in result}
            entries.append(
                LogEntry(
                    timestamp=data.get("@timestamp", ""),
                    message=data.get("@message", ""),
                    log_stream=data.get("@logStream"),
                )
            )
        return entries


def create_cloudwatch_toolset(config: AgentConfig) -> FunctionToolset:
    """Create a FunctionToolset with CloudWatch tools for pydantic-ai."""
    toolset = FunctionToolset()
    cw_logging = CloudWatchLogging(region=config.aws.region)

    @toolset.tool
    async def search_error_logs(
        log_group: str,
        service_name: str | None = None,
        time_range_minutes: int = 10,
    ) -> LogQueryResult:
        """Search CloudWatch logs for errors.

        Args:
            log_group: The CloudWatch log group name
            service_name: Optional service name to filter log streams (e.g., 'my-api')
            time_range_minutes: How far back to search (default: 10 minutes)

        Returns:
            LogQueryResult containing matching error log entries
        """
        return await cw_logging.query_errors(log_group, time_range_minutes, service_name)

    @toolset.tool
    def list_services(
        log_group: str,
        prefix: str | None = None,
    ) -> list[str]:
        """List available log streams (services) in a log group.

        Use this to discover what services are logging to a log group.

        Args:
            log_group: The CloudWatch log group name
            prefix: Optional prefix to filter (e.g., 'prod-')

        Returns:
            List of log stream names (often includes service/pod names)
        """
        return cw_logging.list_log_streams(log_group, prefix)

    return toolset
