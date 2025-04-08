<h1 align="center">
    SRE Agent
</h1>

An SRE agent that can monitor application and infrastructure logs, diagnose issues, and report on diagnostics

## MCP Server Development Setup

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [npx](https://docs.npmjs.com/cli/v8/commands/npx)

### Slack

A slack agent for interacting with the [sre-agent](https://api.slack.com/apps/A08LP03CXF1) using the [Slack MCP server](https://github.com/modelcontextprotocol/servers/tree/main/src/slack).

<details>
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

```json
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
```

</details>

<details>
<summary>npx</summary>

```json
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
```

</details>

> [!NOTE]
> Contact Scott Clare for how to obtain bot token and team ID.


# &#127939; How do I get started (Development)?

## Prerequisites

- [pre-commit](https://pre-commit.com/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

1. Project setup

```bash
make project-setup
```

## Documentation

Documentation for this project can be found in the [docs](docs) folder. The following documentation is available:

* [agent-architecture](docs/agent-architecture.md)
