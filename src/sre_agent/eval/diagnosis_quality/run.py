"""Run diagnosis quality evaluation."""

from pydantic_ai.exceptions import UserError

from sre_agent.eval.diagnosis_quality.config import DEFAULT_EXPERIMENT_NAME
from sre_agent.eval.diagnosis_quality.dataset.create_and_populate import DEFAULT_DATASET_NAME
from sre_agent.eval.diagnosis_quality.experiment import run_experiment


def main() -> None:
    """Run diagnosis quality evaluation with default configuration."""
    try:
        result = run_experiment()
    except UserError as exc:
        print("Model configuration error for eval run.")
        print("Set the provider API key for the configured model before running the eval.")
        raise SystemExit(1) from exc
    except RuntimeError as exc:
        print(str(exc))
        raise SystemExit(1) from exc

    test_results = getattr(result, "test_results", None) or getattr(result, "testResults", [])
    print(f"Experiment: {DEFAULT_EXPERIMENT_NAME}")
    print(f"Dataset: {DEFAULT_DATASET_NAME}")
    print(f"Cases evaluated: {len(test_results)}")


if __name__ == "__main__":
    main()
