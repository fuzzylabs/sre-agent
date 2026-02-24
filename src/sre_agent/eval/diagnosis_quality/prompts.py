"""Prompt rendering for diagnosis quality evaluation."""

from sre_agent.core.prompts import DIAGNOSIS_PROMPT_TEMPLATE
from sre_agent.eval.diagnosis_quality.config import (
    DEFAULT_SLACK_CHANNEL_ID,
    DEFAULT_TIME_RANGE_MINUTES,
)
from sre_agent.eval.diagnosis_quality.dataset.schema import DiagnosisQualityEvalCase


def render_agent_prompt(case: DiagnosisQualityEvalCase) -> str:
    """Render diagnosis prompt with fixed GitHub scope context.

    Args:
        case: The case to run.

    Returns:
        The diagnosis prompt.
    """
    prompt = DIAGNOSIS_PROMPT_TEMPLATE.format(
        log_group=case.log_group,
        time_range_minutes=DEFAULT_TIME_RANGE_MINUTES,
        service_display=case.service_name,
        owner=case.github_owner,
        repo=case.github_repo,
        ref=case.github_ref,
        channel_id=DEFAULT_SLACK_CHANNEL_ID,
    )

    return prompt
