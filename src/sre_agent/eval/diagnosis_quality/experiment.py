"""Diagnosis quality evaluation experiment."""

import asyncio
from typing import Any

import opik
from opik import Opik
from opik.evaluation import evaluate
from opik.evaluation.evaluation_result import EvaluationResult
from pydantic_ai import Agent

from sre_agent.core.models import ErrorDiagnosis
from sre_agent.core.prompts import SYSTEM_PROMPT
from sre_agent.eval.diagnosis_quality.config import (
    DEFAULT_EXPERIMENT_NAME,
    DEFAULT_JUDGE_MODEL,
    DEFAULT_MODEL,
    DEFAULT_OPIK_PROJECT_NAME,
)
from sre_agent.eval.diagnosis_quality.dataset.create_and_populate import (
    DEFAULT_DATASET_NAME,
    create_and_populate_dataset,
)
from sre_agent.eval.diagnosis_quality.dataset.schema import DiagnosisQualityEvalCase
from sre_agent.eval.diagnosis_quality.github_toolset import build_github_toolset
from sre_agent.eval.diagnosis_quality.metrics import (
    AffectedServicesMatch,
    RootCauseCorrectness,
    SuggestedFixesQuality,
)
from sre_agent.eval.diagnosis_quality.mocks import MockToolRuntime, build_mock_toolset
from sre_agent.eval.diagnosis_quality.prompts import render_agent_prompt


def evaluation_task(dataset_item: dict[str, Any]) -> dict[str, Any]:
    """Run one diagnosis-quality case through the agent loop.

    Args:
        dataset_item: The dataset item to run.

    Returns:
        The task output dictionary for Opik scoring.
    """
    payload = dict(dataset_item)
    payload.pop("id", None)
    case = DiagnosisQualityEvalCase.model_validate(payload)
    return asyncio.run(run_case(case))


def run_experiment(dataset_name: str = DEFAULT_DATASET_NAME) -> EvaluationResult:
    """Run the diagnosis quality evaluation in local mode.

    Args:
        dataset_name: The name of the dataset to run.

    Returns:
        The evaluation result.
    """
    opik.config.update_session_config("project_name", DEFAULT_OPIK_PROJECT_NAME)
    opik.configure(use_local=True)
    client = Opik(project_name=DEFAULT_OPIK_PROJECT_NAME)
    dataset, _ = create_and_populate_dataset(client=client, dataset_name=dataset_name)

    return evaluate(
        dataset=dataset,
        task=evaluation_task,
        scoring_metrics=[
            RootCauseCorrectness(judge_model=DEFAULT_JUDGE_MODEL),
            SuggestedFixesQuality(judge_model=DEFAULT_JUDGE_MODEL),
            AffectedServicesMatch(),
        ],
        experiment_name=DEFAULT_EXPERIMENT_NAME,
        project_name=DEFAULT_OPIK_PROJECT_NAME,
        experiment_config={
            "suite": "diagnosis_quality",
            "dataset": dataset_name,
            "mode": "local",
            "model": DEFAULT_MODEL,
            "judge_model": DEFAULT_JUDGE_MODEL,
            "github_mode": "real_mcp",
            "cloudwatch_mode": "mock",
            "slack_mode": "mock",
        },
    )


async def run_case(case: DiagnosisQualityEvalCase) -> dict[str, Any]:
    """Execute one case and return fields required for diagnosis scoring.

    Args:
        case: The case to run.

    Returns:
        Task outputs for diagnosis metrics.
    """
    runtime = MockToolRuntime(case)
    github_toolset = build_github_toolset()
    agent = Agent(
        DEFAULT_MODEL,
        system_prompt=SYSTEM_PROMPT,
        output_type=ErrorDiagnosis,
        toolsets=[build_mock_toolset(runtime), github_toolset],
    )

    result = await agent.run(render_agent_prompt(case))
    return _to_task_output(result.output)


def _to_task_output(diagnosis: ErrorDiagnosis) -> dict[str, Any]:
    """Convert structured diagnosis to metric-friendly task output.

    Args:
        diagnosis: The diagnosis output from the agent.

    Returns:
        Task output dictionary for scoring metrics.
    """
    suggested_fixes_text = _flatten_suggested_fixes(diagnosis)
    diagnosis_text = (
        f"Summary: {diagnosis.summary}\n"
        f"Root Cause: {diagnosis.root_cause}\n"
        f"Affected Services: {', '.join(diagnosis.affected_services)}\n"
        f"Suggested Fixes:\n{suggested_fixes_text}\n"
        f"Related Logs:\n" + "\n".join(diagnosis.related_logs)
    )

    return {
        "summary": diagnosis.summary,
        "root_cause": diagnosis.root_cause,
        "affected_services": diagnosis.affected_services,
        "related_logs": diagnosis.related_logs,
        "suggested_fixes_text": suggested_fixes_text,
        "diagnosis_text": diagnosis_text,
    }


def _flatten_suggested_fixes(diagnosis: ErrorDiagnosis) -> str:
    """Flatten suggested fixes into one string.

    Args:
        diagnosis: The diagnosis output from the agent.

    Returns:
        Flattened suggested fixes text.
    """
    parts: list[str] = []
    for index, fix in enumerate(diagnosis.suggested_fixes, start=1):
        lines = [f"{index}. {fix.description.strip()}"]
        if fix.file_path:
            lines.append(f"File: {fix.file_path.strip()}")
        if fix.code_snippet:
            lines.append(f"Snippet: {fix.code_snippet.strip()}")
        parts.append("\n".join(lines))
    return "\n\n".join(parts)
