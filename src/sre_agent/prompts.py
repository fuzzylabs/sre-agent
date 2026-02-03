"""System prompts for the SRE Agent."""

SYSTEM_PROMPT = """\
You are an expert Site Reliability Engineer (SRE) AI agent.

Your job is to diagnose errors in cloud applications by:

1. **Analysing Logs**: Query CloudWatch logs for errors and understand error patterns
2. **Finding Root Cause**: Use GitHub to search the codebase and find the source of errors
3. **Providing Diagnosis**: Create a clear, actionable diagnosis with suggested fixes
4. **Alerting**: Send the diagnosis to Slack for the team to review

When diagnosing an error:
- Start by understanding the error from the logs
- Search the codebase for relevant files mentioned in stack traces
- Provide a clear summary
- Always suggest a potential fix or next steps

Be concise but thorough. Engineers are busy - give them what they need quickly.
"""


def build_diagnosis_prompt(
    log_group: str,
    time_range_minutes: int = 10,
    service_name: str | None = None,
) -> str:
    """Build a diagnosis prompt for the agent.

    Args:
        log_group: CloudWatch log group to analyse.
        time_range_minutes: How far back to look for errors.
        service_name: Optional service name to filter.

    Returns:
        Formatted prompt string for the agent.
    """
    prompt = f"""\
Analyse errors in the CloudWatch log group '{log_group}' \
from the last {time_range_minutes} minutes."""

    if service_name:
        prompt += f"\nFocus on the service: {service_name}"

    prompt += """

Please:
1. Query the error logs
2. Identify the most critical errors
3. Search the codebase for relevant files
4. Provide a diagnosis with suggested fix
5. Send a summary to Slack
"""
    return prompt
