"""Expected tool selection metric."""

from typing import Any

from opik.evaluation.metrics import base_metric, score_result


class ExpectedToolSelection(base_metric.BaseMetric):
    """Validate the expected tool selection."""

    def __init__(self, name: str = "expected_tool_selection"):
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
        tool_calls: list[dict[str, Any]] | None = None,
        **ignored_kwargs: Any,
    ) -> score_result.ScoreResult:
        """Score required tool usage coverage.

        0 if the required tools are not used, 1 if they are.

        Args:
            expected_first_tool: The expected first tool.
            expected_second_tool: The expected second tool.
            expected_last_tool: The expected last tool.
            possible_github_tools: The possible GitHub tools.
            tool_calls: The tool calls.
            **ignored_kwargs: Ignore other keyword arguments.

        Returns:
            A score result.
        """
        required_tools = {
            expected_first_tool.strip(),
            expected_second_tool.strip(),
            expected_last_tool.strip(),
        }
        required_tools.discard("")

        used = {
            str(call.get("function_name", "")).strip()
            for call in (tool_calls or [])
            if str(call.get("function_name", "")).strip()
        }

        missing_required = sorted(required_tools - used)
        if missing_required:
            return self._fail(f"Missing required tools: {missing_required}.")

        github_options = set(possible_github_tools or [])
        if github_options:
            github_used = (
                used & github_options
            )  # Intersection of used tools and possible GitHub tools.
            if not github_used:
                return self._fail(
                    f"No GitHub tool used. Possible: {sorted(possible_github_tools)}."
                )

        return score_result.ScoreResult(
            name=self.name,
            value=1.0,
            reason="Required tool usage coverage satisfied.",
        )
