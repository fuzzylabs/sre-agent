"""Suggested fixes quality metric for diagnosis quality evaluation."""

from typing import Any

from opik.evaluation.metrics import GEval, base_metric, score_result


class SuggestedFixesQuality(base_metric.BaseMetric):  # type: ignore[misc]
    """Judge whether suggested fixes are correct and actionable."""

    def __init__(
        self,
        judge_model: str,
        name: str = "suggested_fixes_quality",
    ) -> None:
        """Initialise the fix quality metric.

        Args:
            judge_model: The model used for LLM-as-a-judge scoring.
            name: The metric name.
        """
        super().__init__(name=name)
        self._judge = GEval(
            task_introduction=(
                "You are an SRE expert judge tasked with evaluating remediation "
                "suggestions for production incidents. You will be given the "
                "predicted fix suggestions, the diagnosis context, and the expected "
                "fix suggestion mentions. Assess whether the predicted fix "
                "suggestions align with the expected fix suggestions and determine "
                "whether they are correct and actionable."
            ),
            evaluation_criteria=(
                "Score the predicted fix suggestions against expected fix suggestion mentions. "
                "High scores require correct direction, concrete implementation guidance, "
                "and alignment with the stated root cause. "
                "Return an integer score from 0 to 10 only."
            ),
            model=judge_model,
            name=f"{name}_judge",
            track=False,
        )

    def score(
        self,
        root_cause: str,
        suggested_fixes_text: str,
        expected_fix_suggestion_mentions: list[str],
        **ignored_kwargs: Any,
    ) -> score_result.ScoreResult:
        """Score suggested fix quality.

        Args:
            root_cause: The predicted root cause.
            suggested_fixes_text: The flattened predicted fix suggestions text.
            expected_fix_suggestion_mentions: Expected mentions in fix suggestions.
            **ignored_kwargs: Ignore other keyword arguments.

        Returns:
            A score result.
        """
        if not suggested_fixes_text.strip():
            return score_result.ScoreResult(
                name=self.name,
                value=0.0,
                reason="No predicted fix suggestions in model output.",
            )

        expected_text = "\n".join(f"- {item}" for item in expected_fix_suggestion_mentions)

        comparison_text = (
            f"Predicted Root Cause:\n{root_cause}\n\n"
            f"Expected Fix Suggestions:\n{expected_text}\n\n"
            f"Predicted Fix Suggestions:\n{suggested_fixes_text}"
        )

        try:
            judged = self._judge.score(output=comparison_text)
        except Exception as exc:
            return score_result.ScoreResult(
                name=self.name,
                value=0.0,
                reason=f"Judge failed to score suggested fixes: {exc}",
            )

        return score_result.ScoreResult(
            name=self.name,
            value=float(judged.value),
            reason=judged.reason,
        )
