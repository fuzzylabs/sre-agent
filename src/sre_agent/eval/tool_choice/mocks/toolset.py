"""Mock toolset builder for tool choice evaluation."""

from typing import Any

from pydantic_ai import FunctionToolset

from sre_agent.core.models import LogQueryResult
from sre_agent.eval.tool_choice.mocks import cloudwatch as cloudwatch_mocks
from sre_agent.eval.tool_choice.mocks import slack as slack_mocks
from sre_agent.eval.tool_choice.mocks.runtime import MockToolRuntime


def build_mock_toolset(runtime: MockToolRuntime) -> FunctionToolset:
    """Build mocked Slack and CloudWatch toolset."""
    toolset = FunctionToolset()

    @toolset.tool
    async def conversations_add_message(
        channel_id: str,
        payload: str,
        thread_ts: str | None = None,
    ) -> dict[str, Any]:
        """Mock Slack message posting."""
        return await slack_mocks.conversations_add_message(
            channel_id,
            payload,
            thread_ts,
        )

    @toolset.tool
    async def search_error_logs(
        log_group: str,
        service_name: str,
        time_range_minutes: int = 10,
    ) -> LogQueryResult:
        """Mock CloudWatch error search."""
        return await cloudwatch_mocks.search_error_logs(
            runtime,
            log_group,
            service_name,
            time_range_minutes,
        )

    return toolset
