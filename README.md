<h1 align="center"> <!-- spellchecker:disable-line -->
    🚀 Site Reliability Engineer (SRE) Agent :detective:
</h1>

WIP.

To run the agent locally, use the CLI and follow the prompts: `uv run sre-agent`.

For direct local diagnostics without the CLI, start the Slack MCP container with `docker compose up -d slack`, then run the module with a log group, service name, and time window in minutes, for example: `uv run python -m sre_agent.run /aws/containerinsights/no-loafers-for-you/application currencyservice 10`.
