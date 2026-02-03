"""CloudWatch implementation of the LoggingInterface."""

import time
from datetime import UTC, datetime, timedelta
from typing import Any

import boto3
from botocore.exceptions import ClientError
from pydantic_ai import FunctionToolset

from sre_agent.config import AgentConfig
from sre_agent.interfaces import LoggingInterface
from sre_agent.models import LogEntry, LogQueryResult

_TERMINAL_STATUSES = {"Complete", "Failed", "Cancelled", "Timeout", "Unknown"}


class CloudWatchLogging(LoggingInterface):
    """CloudWatch Logs implementation."""

    def __init__(self, region: str | None = None) -> None:
        """Initialise CloudWatch client.

        Args:
            region: AWS region (uses default if not specified).
        """
        self._client: Any = boto3.client("logs", region_name=region)

    async def query_errors(
        self,
        source: str,
        time_range_minutes: int = 10,
    ) -> LogQueryResult:
        """Query error logs from CloudWatch.

        Args:
            source: The CloudWatch log group name.
            time_range_minutes: How far back to search.

        Returns:
            LogQueryResult with matching error entries.
        """
        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(minutes=time_range_minutes)

        query_string = " | ".join(
            [
                "fields @timestamp, @message, @logStream",
                "filter @message like /(?i)error|exception|fatal|critical/",
                "sort @timestamp desc",
                "limit 10",
            ]
        )

        try:
            response = self._client.start_query(
                logGroupName=source,
                startTime=int(start_time.timestamp()),
                endTime=int(end_time.timestamp()),
                queryString=query_string,
            )
            results = self._wait_for_results(response["queryId"])

            return LogQueryResult(
                entries=self._parse_results(results),
                log_group=source,
                query=query_string,
            )
        except ClientError as e:
            return LogQueryResult(
                entries=[],
                log_group=source,
                query=f"Error: {e}",
            )

    def _wait_for_results(self, query_id: str) -> list[list[dict[str, str]]]:
        """Wait for query to complete."""
        while True:
            time.sleep(1)
            response = self._client.get_query_results(queryId=query_id)
            if response["status"] in _TERMINAL_STATUSES:
                results: list[list[dict[str, str]]] = response.get("results", [])
                return results

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
    logging = CloudWatchLogging(region=config.aws.region)

    @toolset.tool
    async def search_error_logs(
        log_group: str,
        time_range_minutes: int = 10,
    ) -> LogQueryResult:
        """Search CloudWatch logs for errors.

        Args:
            log_group: The CloudWatch log group name
            time_range_minutes: How far back to search (default: 10 minutes)

        Returns:
            LogQueryResult containing matching error log entries
        """
        return await logging.query_errors(log_group, time_range_minutes)

    return toolset
