"""Root cause correctness metric for diagnosis quality evaluation."""

from typing import Any

from opik.evaluation.metrics import GEval, base_metric, score_result


class RootCauseCorrectness(base_metric.BaseMetric):  # type: ignore[misc]
    """Judge whether the root cause matches the expected issue."""

    def __init__(
        self,
        judge_model: str,
        name: str = "root_cause_correctness",
    ) -> None:
        """Initialise the root cause correctness metric.

        Args:
            judge_model: The model used for LLM-as-a-judge scoring.
            name: The metric name.
        """
        super().__init__(name=name)
        self._judge = GEval(
            task_introduction=(
                "You are an SRE expert judge tasked with evaluating root-cause "
                "statements for production incidents. You will be given both the "
                "submitted diagnosis and the expected root cause, and your job is "
                "to assess whether the diagnosis is accurate."
            ),
            evaluation_criteria=(
                "Compare the predicted root cause against the expected root cause. "
                "Score high when they refer to the same underlying failure mechanism. "
                "Penalise incorrect, unrelated, or vague diagnoses. "
                "Return an integer score from 0 to 10 only."
            ),
            model=judge_model,
            name=f"{name}_judge",
            track=False,  # No need tracing
        )

    def score(
        self,
        root_cause: str,
        expected_root_cause: str,
        service_name: str,
        **ignored_kwargs: Any,
    ) -> score_result.ScoreResult:
        """Score root-cause correctness.

        Args:
            root_cause: The predicted root cause.
            expected_root_cause: The expected root cause.
            service_name: The service under evaluation.
            **ignored_kwargs: Ignore other keyword arguments.

        Returns:
            A score result.
        """
        if not root_cause.strip():
            return score_result.ScoreResult(
                name=self.name,
                value=0.0,
                reason="Missing root cause in model output.",
            )

        # https://www.comet.com/docs/opik/evaluation/metrics/g_eval
        # Everything in one payload suggested by the docs.
        comparison_text = (
            f"Service: {service_name}\n"
            f"Expected Root Cause:\n{expected_root_cause}\n\n"
            f"Predicted Root Cause:\n{root_cause}"
        )

        judged = self._judge.score(output=comparison_text)
        return score_result.ScoreResult(
            name=self.name,
            value=float(judged.value),
            reason=judged.reason,
        )
