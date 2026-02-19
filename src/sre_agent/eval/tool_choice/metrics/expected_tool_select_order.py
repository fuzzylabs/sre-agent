"""Expected tool selection order metric."""

from typing import Any

from opik.evaluation.metrics import base_metric, score_result
from opik.message_processing.emulation.models import SpanModel

from sre_agent.eval.tool_choice.metrics.span_tools import extract_tool_names


class ExpectedToolSelectOrder(base_metric.BaseMetric):
    """Validate the expected tool selection order."""

    def __init__(self, name: str = "expected_tool_select_order"):
        """Initialise the metric.

        Args:
            name: The name of the metric.
        """
        super().__init__(name=name)

    def _fail(self, reason: str) -> score_result.ScoreResult:
        """Return a failing score result.

        Args:
            reason: The reason for failing the score result.

        Returns:
            A score result.
        """
        return score_result.ScoreResult(name=self.name, value=0.0, reason=reason)

    def score(
        self,
        expected_first_tool: str,
        expected_second_tool: str,
        expected_last_tool: str,
        possible_github_tools: list[str],
        task_span: SpanModel | None = None,
        **ignored_kwargs: Any,
    ) -> score_result.ScoreResult:
        """Score tool-call order for first, second, and last calls from spans.

        0 if the tool-call order is not as expected, 1 if it is.

        Args:
            expected_first_tool: The expected first tool.
            expected_second_tool: The expected second tool.
            expected_last_tool: The expected last tool.
            possible_github_tools: The possible GitHub tools.
            task_span: The root evaluation span for this case.
            **ignored_kwargs: Ignore other keyword arguments.

        Returns:
            A score result.
        """
        github_options = set(possible_github_tools or [])
        minimum_call_count = 4 if github_options else 3

        names = extract_tool_names(task_span)

        if len(names) < minimum_call_count:
            return self._fail(
                f"Too few tool calls: expected at least {minimum_call_count}, got {len(names)}."
            )

        checks = [
            (names[0], expected_first_tool, "First"),
            (names[1], expected_second_tool, "Second"),
            (names[-1], expected_last_tool, "Last"),
        ]

        for actual, expected, label in checks:
            if actual != expected:
                return self._fail(f"{label} tool mismatch. Expected '{expected}', got '{actual}'.")

        middle_tools = names[2:-1]
        if github_options:
            middle_github_tools = sorted(set(middle_tools) & github_options)
            if not middle_github_tools:
                return self._fail(
                    "No GitHub tool used in middle steps. "
                    f"Possible: {sorted(github_options)}. Got: {middle_tools}."
                )

        return score_result.ScoreResult(
            name=self.name,
            value=1.0,
            reason="All tool order checks passed.",
        )
