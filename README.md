<h1 align="center">
    SRE Agent
</h1>

An SRE agent that can monitor application and infrastructure logs, diagnose issues, and report on diagnostics

## Deploy Agent locally using Docker Compose

- [Docker](https://docs.docker.com/get-docker/)
- A `.env` file sitting at root containing the following:
    - `SLACK_BOT_TOKEN`: The token for the `sre-agent` Slack bot.
    - `SLACK_TEAM_ID`: The ID of the team to send responses to.
    - `CHANNEL_ID`: The Slack channel ID to send responses to.
    - `GITHUB_PERSONAL_ACCESS_TOKEN`: A personal access token for reading files from Github.
    - `ANTHROPIC_API_KEY`: An Anthropic API key for making tool requests.
    - `DEV_BEARER_TOKEN`: A password for developers to directly invoke the agent through the `/diagnose` endpoint.
    - `SLACK_SIGNING_SECRET`: The signing secret for the Slack `sre-agent`.
    - `TOOLS`: '["list_pods", "get_logs", "get_file_contents", "slack_post_requests"]'
    - `AWS_ACCOUNT_ID` (Optional): The AWS account ID that stores the images. Only required if pulling images from ECR.

### Prerequisites

<details>
<summary>Deploy with ECR images</summary>

See [ECR Setup](#ecr-set-up) for details on how to enable pulling images from ECR.

```
docker compose -f compose.ecr.yaml up
```

</details>


<details>
<summary>Deploy by building images locally</summary>

See [ECR Setup](#ecr-set-up) for details on how to enable pulling images from ECR.

```
docker compose up
```

</details>

## MCP Server Claude Desktop Setup

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [npx](https://docs.npmjs.com/cli/v8/commands/npx)

### [Slack](sre_agent/servers/slack/README.md)

A slack agent for interacting with the [sre-agent](https://api.slack.com/apps/A08LP03CXF1) using the [Slack MCP server](https://github.com/modelcontextprotocol/servers/tree/main/src/slack).

<details>
<summary>Docker (Recommended)</summary>

1. Build docker image:

```bash
cd sre_agent
docker build -t mcp/slack -f servers/slack/Dockerfile .
```

2. Update `claude_desktop_config.json` with the following:

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
        "SLACK_TEAM_ID": "<team-id>"
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
        "SLACK_TEAM_ID": "<team-id>"
      }
    }
  }
}
```
</details>

> [!NOTE]
> Contact Scott Clare for how to obtain bot token and team ID.


### [GitHub](sre_agent/servers/github/README.md)

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

1. Build docker image:

```bash
cd sre_agent
docker build -t mcp/github -f servers/github/Dockerfile .
```

2. Update `claude_desktop_config.json` with the following:

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

### [Kubernetes](sre_agent/servers/mcp-server-kubernetes/README.md)

A Kubernetes agent using [mcp-server-kubernetes](https://github.com/Flux159/mcp-server-kubernetes).

> To interact with the Kubernetes MCP you will need to access the K8s cluster locally first. To do this you will need to update your kubeconfig:
> ```
> aws eks update-kubeconfig --region eu-west-2 --name clustername
> ```

<details>
<summary>Docker (Recommended)</summary>

1. Build docker image:

```bash
cd sre_agent/server/mcp-server-kubernetes
docker build -t mcp/k8s .
```

2. Update `claude_desktop_config.json` with the following:

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
        "<absolute path to root>/.kube:/home/appuser/.kube",
        "-v",
        "<absolute path to root>/.aws:/home/appuser/.aws",
        "mcp/k8s"
      ],
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
    "kubernetes": {
      "command": "npx",
      "args": ["mcp-server-kubernetes"]
    }
  }
}
```
</details>

## ECR set-up

Instead of accessing Docker images locally, you can retrieve them from ECR (Elastic Container Registry) on AWS. To set this up you will need:

1. An ECR in your AWS account
2. Private/public ECR repositories for each MCP Server, for example, for a `github` MCP server create a repo named `mcp/github` either through the UI, CLI, or Terraform. This repo currently requires:
```
`mcp/github`
`mcp/kubernetes`
`mcp/slack`
```
3. Set the following AWS environment variables and ensure you have your AWS credentials set to access the ECR:

```
export AWS_ACCOUNT_ID=<YOUR AWS ACCOUNT ID>
export AWS_REGION=<region>
```

Then run the `build_push_docker.sh` script to build and push the Docker images for each of the MCP servers:
```
bash build_push_docker.sh
```

Once this is done, you can access and pull the images from the following location:
```
${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/mcp/${mcp_server_name}:latest
```
For example, the Slack MCP server image location could look like:
```
12345678.dkr.ecr.eu-west-2.amazonaws.com/mcp/slack:latest
```

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
