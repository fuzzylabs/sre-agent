"""Dataset loading helpers for tool call evaluation."""

from pathlib import Path
from typing import Any

from opik import Opik

from sre_agent.eval.common.case_loader import load_json_case_models
from sre_agent.eval.tool_call.dataset.schema import ToolCallEvalCase

DEFAULT_DATASET_NAME = "sre-agent-tool-call"


def build_from_cases_files() -> list[ToolCallEvalCase]:
    """Load and validate local tool call cases.

    Returns:
        A list of ToolCallEvalCase instances.
    """
    return load_json_case_models(Path(__file__).parent / "test_cases", ToolCallEvalCase)


def create_and_populate_dataset(
    client: Opik,
    dataset_name: str = DEFAULT_DATASET_NAME,
) -> tuple[Any, int]:
    """Create or replace dataset rows from local case files.

    Args:
        client: The Opik client.
        dataset_name: The name of the dataset to create or replace.

    Returns:
        A tuple of (dataset, inserted_case_count).
    """
    dataset = client.get_or_create_dataset(name=dataset_name)
    cases = build_from_cases_files()

    dataset.clear()
    dataset.insert([case.model_dump(mode="json") for case in cases])
    return dataset, len(cases)
