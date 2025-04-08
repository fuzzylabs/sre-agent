<h1 align="center">
    sre_agent &#128679;
</h1>

An SRE agent that can monitor application and infrastructure logs, diagnose issues, and report on diagnostics

# &#127939; How do I get started?
If you haven't already done so, please read [DEVELOPMENT.md](DEVELOPMENT.md) for instructions on how to set up your virtual environment using Poetry.

## MCP Server Development Setup

### Slack

etails>
<summary>Docker (Recommended)</summary>

1. Clone Slack MCP server:

```bash
git clone git@github.com:modelcontextprotocol/servers.git
```

2. Build docker image:

```bash
docker build -t mcp/slack -f src/slack/Dockerfile .
```

3. Update `claude_desktop_config.json` with the following:

{
  "mcpServers": {
    "slack": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "SLACK_BOT_TOKEN",
        "-e",
        "SLACK_TEAM_ID",
        "mcp/slack"
      ],
      "env": {
        "SLACK_BOT_TOKEN": "xoxb-your-bot-token",
        "SLACK_TEAM_ID": "T01234567"
      }
    }
  }
}

> [!NOTE]
> Contact Scott Clare for how to obtain bot token and team ID.

</details>

<details>
<summary>npx</summary>

{
  "mcpServers": {
    "slack": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-slack"
      ],
      "env": {
        "SLACK_BOT_TOKEN": "xoxb-your-bot-token",
        "SLACK_TEAM_ID": "T01234567"
      }
    }
  }
}

> [!NOTE]
> Contact Scott Clare for how to obtain bot token and team ID.

</details>
