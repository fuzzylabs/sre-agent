"""SRE Agent using pydantic-ai."""

from pydantic_ai import Agent

from sre_agent.config import AgentConfig, get_config
from sre_agent.models import ErrorDiagnosis
from sre_agent.prompts import SYSTEM_PROMPT, build_diagnosis_prompt
from sre_agent.tools import (
    create_cloudwatch_toolset,
    create_github_mcp_toolset,
    create_slack_mcp_toolset,
)


def create_sre_agent(config: AgentConfig | None = None) -> Agent[None, ErrorDiagnosis]:
    """Create the SRE Agent with all toolsets configured.

    Args:
        config: Optional AgentConfig. If not provided, loads from environment.

    Returns:
        Configured pydantic-ai Agent with structured output.
    """
    if config is None:
        config = get_config()

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
    time_range_minutes: int = 10,
    service_name: str | None = None,
    config: AgentConfig | None = None,
) -> ErrorDiagnosis:
    """Run a diagnosis for errors in a specific log group.

    Args:
        log_group: CloudWatch log group to analyse.
        time_range_minutes: How far back to look for errors.
        service_name: Optional service name to filter.
        config: Optional agent configuration.

    Returns:
        ErrorDiagnosis with findings and suggested fixes.
    """
    agent = create_sre_agent(config)
    prompt = build_diagnosis_prompt(log_group, time_range_minutes, service_name)

    result = await agent.run(prompt)
    return result.output
