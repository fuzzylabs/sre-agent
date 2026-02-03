"""System prompts for the SRE Agent."""

from pathlib import Path

PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(filename: str) -> str:
    """Load a prompt from a text file."""
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8").strip()


SYSTEM_PROMPT = _load_prompt("system_prompt.txt")
DIAGNOSIS_PROMPT_TEMPLATE = _load_prompt("diagnosis_prompt.txt")


def build_diagnosis_prompt(
    log_group: str,
    time_range_minutes: int = 10,
    service_name: str | None = None,
) -> str:
    """Build a diagnosis prompt for the agent."""
    service_display = service_name or "unknown service"

    return DIAGNOSIS_PROMPT_TEMPLATE.format(
        log_group=log_group,
        time_range_minutes=time_range_minutes,
        service_display=service_display,
    )
