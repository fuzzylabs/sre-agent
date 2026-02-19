"""Tool call evaluation experiment."""

import asyncio
from typing import Any

import opik
from opik import Opik
from opik.evaluation import evaluate
from opik.evaluation.evaluation_result import EvaluationResult
from pydantic_ai import Agent

from sre_agent.core.models import ErrorDiagnosis
from sre_agent.core.prompts import SYSTEM_PROMPT
from sre_agent.eval.tool_call.config import (
    DEFAULT_EXPERIMENT_NAME,
    DEFAULT_MODEL,
)
from sre_agent.eval.tool_call.dataset.create_and_populate import (
    DEFAULT_DATASET_NAME,
    create_and_populate_dataset,
)
from sre_agent.eval.tool_call.dataset.schema import ToolCallEvalCase
from sre_agent.eval.tool_call.github_toolset import build_github_toolset
from sre_agent.eval.tool_call.metrics.expected_tool_select_order import (
    ExpectedToolSelectOrder,
)
from sre_agent.eval.tool_call.metrics.expected_tool_selection import ExpectedToolSelection
from sre_agent.eval.tool_call.mocks import MockToolRuntime, build_mock_toolset
from sre_agent.eval.tool_call.prompts import render_agent_prompt


def evaluation_task(dataset_item: dict[str, Any]) -> dict[str, Any]:
    """Run one tool call case through the agent loop.

    Args:
        dataset_item: The dataset item to run.

    Returns:
        The task output dictionary for Opik scoring.
    """
    payload = dict(dataset_item)
    payload.pop("id", None)
    case = ToolCallEvalCase.model_validate(payload)
    return asyncio.run(run_case(case))


def run_experiment(dataset_name: str = DEFAULT_DATASET_NAME) -> EvaluationResult:
    """Run the tool call evaluation in local mode.

    Args:
        dataset_name: The name of the dataset to run.

    Returns:
        The evaluation result.
    """
    opik.configure(use_local=True)
    client = Opik()
    dataset, _ = create_and_populate_dataset(client=client, dataset_name=dataset_name)

    return evaluate(
        dataset=dataset,
        task=evaluation_task,
        scoring_metrics=[ExpectedToolSelectOrder(), ExpectedToolSelection()],
        experiment_name=DEFAULT_EXPERIMENT_NAME,
        experiment_config={
            "suite": "tool_call",
            "dataset": dataset_name,
            "mode": "local",
            "model": DEFAULT_MODEL,
            "github_mode": "real_mcp",
            "cloudwatch_mode": "mock",
            "slack_mode": "mock",
        },
    )


async def run_case(case: ToolCallEvalCase) -> dict[str, Any]:
    """Execute one case using a real agent with hybrid toolsets.

    Args:
        case: The case to run.

    Returns:
        An empty dictionary, we will extract tool usage from the span tree.
    """
    runtime = MockToolRuntime(case)
    github_toolset = build_github_toolset()

    agent = Agent(
        DEFAULT_MODEL,
        system_prompt=SYSTEM_PROMPT,
        output_type=ErrorDiagnosis,
        toolsets=[build_mock_toolset(runtime), github_toolset],
    )

    await agent.run(render_agent_prompt(case))
    return {}  # Must return a dictionary for Opik
