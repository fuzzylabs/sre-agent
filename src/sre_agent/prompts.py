"""System prompts for the SRE Agent."""

from pathlib import Path

from sre_agent.config import AgentConfig

PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(filename: str) -> str:
    """Load a prompt from a text file."""
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8").strip()


SYSTEM_PROMPT = _load_prompt("system_prompt.txt")
DIAGNOSIS_PROMPT_TEMPLATE = _load_prompt("diagnosis_prompt.txt")


def build_diagnosis_prompt(
    config: AgentConfig,
    log_group: str,
    time_range_minutes: int = 10,
    service_name: str | None = None,
) -> str:
    """Build a diagnosis prompt for the agent."""
    service_display = service_name or "unknown service"

    prompt = DIAGNOSIS_PROMPT_TEMPLATE.format(
        log_group=log_group,
        time_range_minutes=time_range_minutes,
        service_display=service_display,
    )

    # Add Slack context
    prompt += f"\n\nSlack Context:\n- Channel ID: {config.slack.channel_id}"

    return prompt
