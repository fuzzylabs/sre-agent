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


### GitHub

> To interact with the Github MCP you will need to create a personal access token:
> 1. Go to Personal access tokens (in GitHub Settings > Developer settings)
> 2. Select which repositories you'd like this token to have access to (Public, All, or Select)
> 3. If working only with public repositories, select only the Public repositories scope
> 4. Add read only permissions for "Contents" in the "Repository permissions"
> 5. Generate and copy the generated token
>
> [Here is a notion page with additional details on how this is setup](https://www.notion.so/fuzzylabs/Github-MCP-1ceb6e71390f8004a106d17d61637c74)

<details>
<summary>Docker (Recommended)</summary>

1. Clone GitHub MCP server:

```bash
git clone git@github.com:modelcontextprotocol/servers.git
```

2. Build docker image:

```bash
docker build -t mcp/github -f src/github/Dockerfile .
```

3. Update `claude_desktop_config.json` with the following:

```json
{
  "mcpServers": {
    "github": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "GITHUB_PERSONAL_ACCESS_TOKEN",
        "mcp/github"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "<YOUR_TOKEN>"
      }
    }
  }
}
```

</details>

<details>
<summary>npx</summary>

1. Update `claude_desktop_config.json` with the following:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-github"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "<YOUR_TOKEN>"
      }
    }
  }
}
```

</details>

### Kubernetes

A Kubernetes agent using [mcp-server-kubernetes](https://github.com/Flux159/mcp-server-kubernetes).

<details>
<summary>Docker (Recommended)</summary>

1. Clone Kubernetes MCP server:

```bash
git clone git@github.com:Flux159/mcp-server-kubernetes.git
```

2. Build docker image:

```bash
docker build -t mcp/k8s .
```

3. Update `claude_desktop_config.json` with the following:

```json
{
  "mcpServers": {
    "kubernetes": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-v",
        "$HOME/.kube/config:/root/.kube/config",
        "mcp/k8s"
      ],
    }
  }
}
```

</details>

<details>
<summary>npx</summary>

1. Clone Kubernetes MCP server:

```bash
git clone git@github.com:Flux159/mcp-server-kubernetes.git
```

2. Update `claude_desktop_config.json` with the following:

```json
{
  "mcpServers": {
    "kubernetes": {
      "command": "npx",
      "args": ["mcp-server-kubernetes"]
    }
  }
}
```
</details>

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

* [Creating an IAM Role](docs/creating-an-iam-role.md)
* [Agent Architecture](docs/agent-architecture.md)
