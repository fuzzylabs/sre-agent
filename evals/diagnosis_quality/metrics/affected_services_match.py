"""Affected services match metric for diagnosis quality evaluation."""

from typing import Any

from opik.evaluation.metrics import base_metric, score_result


class AffectedServicesMatch(base_metric.BaseMetric):  # type: ignore[misc]
    """Score overlap between predicted and expected affected services."""

    def __init__(self, name: str = "affected_services_match") -> None:
        """Initialise the affected services match metric.

        Args:
            name: The metric name.
        """
        super().__init__(name=name)

    def score(
        self,
        affected_services: list[str],
        expected_affected_services: list[str],
        **ignored_kwargs: Any,
    ) -> score_result.ScoreResult:
        """Score affected services overlap using Jaccard similarity.

        Args:
            affected_services: Predicted affected services.
            expected_affected_services: Expected affected services.
            **ignored_kwargs: Ignore other keyword arguments.

        Returns:
            A score result.
        """
        predicted = {service.strip().lower() for service in affected_services if service.strip()}
        expected = {
            service.strip().lower() for service in expected_affected_services if service.strip()
        }

        union = predicted | expected
        if not union:
            # Both sets are empty: no services were expected and none were predicted.
            return score_result.ScoreResult(
                name=self.name,
                value=1.0,
                reason="No affected services expected and none predicted.",
            )

        # Jaccard
        intersection = predicted & expected
        value = len(intersection) / len(union)
        missing = sorted(expected - predicted)
        unexpected = sorted(predicted - expected)
        reason = (
            f"Overlap={len(intersection)}/{len(union)}. Missing={missing}. Unexpected={unexpected}."
        )
        return score_result.ScoreResult(
            name=self.name,
            value=value,
            reason=reason,
        )
