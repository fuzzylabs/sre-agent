"""Mock CloudWatch tools for tool choice evaluation."""

import opik

from sre_agent.core.models import LogEntry, LogQueryResult
from sre_agent.eval.tool_choice.mocks.runtime import MockToolRuntime

MOCK_TIMESTAMP = "2026-01-01T00:00:00+00:00"


async def search_error_logs(
    runtime: MockToolRuntime,
    log_group: str,
    service_name: str,
    time_range_minutes: int,
) -> LogQueryResult:
    """Mock CloudWatch log lookup using case fixtures."""
    with opik.start_as_current_span(
        name="search_error_logs",
        type="tool",
        input={
            "log_group": log_group,
            "service_name": service_name,
            "time_range_minutes": time_range_minutes,
        },
        metadata={"mocked": True, "provider": "cloudwatch"},
    ):
        entries = [
            LogEntry(
                timestamp=MOCK_TIMESTAMP,
                message=message,
                log_stream=None,
            )
            for message in _normalise_messages(runtime)
        ]
        return LogQueryResult(
            entries=entries,
            log_group=log_group,
            query=f"mock: search_error_logs service={service_name}",
        )


def _normalise_messages(runtime: MockToolRuntime) -> list[str]:
    """Convert multiline fixture entries into non-empty log messages."""
    messages: list[str] = []
    for entry in runtime.case.mock_cloudwatch_entries:
        message = "\n".join(line.rstrip("\n") for line in entry.message).strip()
        if message:
            messages.append(message)
    return messages
