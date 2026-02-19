"""Dataset loading helpers for tool choice evaluation."""

from pathlib import Path
from typing import Any

from opik import Opik

from sre_agent.eval.common.case_loader import load_json_case_models
from sre_agent.eval.tool_choice.dataset.schema import ToolChoiceEvalCase

DEFAULT_DATASET_NAME = "sre-agent-tool-choice"


def build_from_cases_files() -> list[ToolChoiceEvalCase]:
    """Load and validate local tool choice cases.

    Returns:
        A list of ToolChoiceEvalCase instances.
    """
    return load_json_case_models(Path(__file__).parent / "test_cases", ToolChoiceEvalCase)


def create_and_populate_dataset(
    client: Opik,
    dataset_name: str = DEFAULT_DATASET_NAME,
) -> tuple[Any, int]:
    """Create or replace dataset rows from local case files.

    Returns:
        A tuple of (dataset, inserted_case_count).
    """
    dataset = client.get_or_create_dataset(name=dataset_name)
    cases = build_from_cases_files()

    dataset.clear()
    dataset.insert([case.model_dump(mode="json") for case in cases])
    return dataset, len(cases)
