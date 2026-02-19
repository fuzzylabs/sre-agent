"""Run tool call evaluation."""

from pydantic_ai.exceptions import UserError

from sre_agent.eval.tool_call.config import DEFAULT_EXPERIMENT_NAME
from sre_agent.eval.tool_call.dataset.create_and_populate import DEFAULT_DATASET_NAME
from sre_agent.eval.tool_call.experiment import run_experiment


def main() -> None:
    """Run tool call evaluation with default configuration."""
    try:
        result = run_experiment()
    except UserError as exc:
        print("Model configuration error for eval run.")
        print("Set MODEL and the matching provider API key before running the eval.")
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
