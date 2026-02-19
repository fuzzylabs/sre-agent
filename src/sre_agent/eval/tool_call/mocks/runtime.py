"""Runtime state for tool call mocked tools."""

from dataclasses import dataclass

from sre_agent.eval.tool_call.dataset.schema import ToolCallEvalCase


@dataclass
class MockToolRuntime:
    """Runtime state for one eval case."""

    case: ToolCallEvalCase
