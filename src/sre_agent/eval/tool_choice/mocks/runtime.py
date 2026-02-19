"""Runtime state for tool choice mocked tools."""

from dataclasses import dataclass

from sre_agent.eval.tool_choice.dataset.schema import ToolChoiceEvalCase


@dataclass
class MockToolRuntime:
    """Runtime state for one eval case."""

    case: ToolChoiceEvalCase
