"""SRE Agent using pydantic-ai."""

from pydantic_ai import Agent

from sre_agent.core.models import ErrorDiagnosis
from sre_agent.core.prompts import SYSTEM_PROMPT, build_diagnosis_prompt
from sre_agent.core.settings import AgentSettings, get_settings
from sre_agent.core.tools import (
    create_cloudwatch_toolset,
    create_github_mcp_toolset,
    create_slack_mcp_toolset,
)


def create_sre_agent(config: AgentSettings | None = None) -> Agent[None, ErrorDiagnosis]:
    """Create the SRE Agent with all toolsets configured.

    Args:
        config: Optional AgentSettings. If not provided, loads from environment.

    Returns:
        Configured pydantic-ai Agent with structured output.
    """
    if config is None:
        config = get_settings()

    toolsets = [
        create_cloudwatch_toolset(config),
        create_github_mcp_toolset(config),
        create_slack_mcp_toolset(config),
    ]

    return Agent(
        config.model,
        system_prompt=SYSTEM_PROMPT,
        output_type=ErrorDiagnosis,
        toolsets=toolsets,
    )


async def diagnose_error(
    log_group: str,
    service_name: str,
    time_range_minutes: int = 10,
    config: AgentSettings | None = None,
) -> ErrorDiagnosis:
    """Run a diagnosis for errors in a specific log group.

    Args:
        log_group: CloudWatch log group to analyse.
        service_name: Service name to filter.
        time_range_minutes: How far back to look for errors.
        config: Optional agent configuration.

    Returns:
        ErrorDiagnosis with findings and suggested fixes.
    """
    if config is None:
        config = get_settings()

    agent = create_sre_agent(config)
    prompt = build_diagnosis_prompt(config, log_group, service_name, time_range_minutes)

    result = await agent.run(prompt)
    return result.output
