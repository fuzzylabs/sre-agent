<h1 align="center">
    Site Reliability Engineer (SRE) Agent :detective:
</h1>

<h3 align="center">
    <p>Open-source implementation for an Site Reliability Engineer (SRE) AI Agent.</p>
</h3>

# What does it do?

SRE agent is an AI agent that can monitor application and infrastructure logs, diagnose issues, and report on diagnostics following an error in an application. Hook up your Kubernetes cluster, GitHub repository and Slack and let the agent summarise and diagnose issues to your team.

## Features
- Debugging issues - finds the root cause of application and system errors
- Kubernetes logs - queries Kubernetes cluster for information and application logs
- GitHub server - search your application GitHub repository to find respective bugs in code
- Slack integration - report and update your team in Slack
- Triggerable from anywhere with a diagnose endpoint

We use the Model Context Protocol (MCP) created by Anthropic to connect the LLM to the provided tools.

![ezgif com-speed](https://github.com/user-attachments/assets/42d4abc0-7df4-4062-a971-c5b0ddf112c9)

## Why are we making it?

To gain a better understanding of best practices, costs, security and performance of AI agents in production systems, we wanted to create and share an example through open-source development. See our [Production Journey Page](/docs/production-journey.md) to see how we took the deployment of the agent and MCP servers from local to Kubernetes and our [Agent Architecture Page](/docs/agent-architecture.md) for more information on how our client and services are connected and used.

Please feel free to follow along and contribute to this repository!

# Deployment

We currently support two deployment methods for the MCP servers and client, one locally, and one on AWS.

## Deploy Agent on Amazon Elastic Kubernetes Services (EKS)

See the [kubernetes-deployment.md](/docs/kubernetes-deployment.md) page for instructions on how to deploy the Agent to EKS.

## Deploy Agent Locally Using Docker Compose

The fully orchestrated SRE Agent can be deployed with Docker Compose which spins up all of the required servers (Slack, Github, and K8s MCP servers) and an orchestration service which is a proxy between the LLM and the servers, this is the client in the context of MCP. Once the agent has been spun up you can trigger the SRE agent with the following request:

```
curl -X POST http://localhost:8003/diagnose \
  -H "accept: application/json" \
  -H "Authorization: Bearer <token>" \
  -d "text=<service>"
```

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- A configured `.env` file in the project root directory. See the [Environment Variables](#environment-variables) section below for details.
- An application deployed in AWS on Kubernetes for the agent to interact with.
- A Slackbot created inside of your Slack account. See [Create Slackbot](https://docs.slack.dev/quickstart) to see how to create a Slackbot.

### Environment Variables

This project requires several environment variables for configuration. A template file, `.env.example` [link here](/.env.example), is provided in the root directory as a reference.

Create a file named `.env` in the project root and add the following variables:


*   `SLACK_BOT_TOKEN`: The token for the `sre-agent` Slack bot.
*   `SLACK_TEAM_ID`: The ID of the Slack team where the agent operates. See [here](https://help.socialintents.com/article/148-how-to-find-your-slack-team-id-and-slack-channel-id) for guide on how to find this.
*   `CHANNEL_ID`: The specific Slack channel ID for the agent's responses. See [here](https://help.socialintents.com/article/148-how-to-find-your-slack-team-id-and-slack-channel-id) for guide on how to find this.
*   `SLACK_SIGNING_SECRET`: The signing secret associated with the Slack `sre-agent` application.
*   `GITHUB_PERSONAL_ACCESS_TOKEN`: A GitHub personal access token with permissions to read relevant files.
*   `ANTHROPIC_API_KEY`: An API key for Anthropic, used for processing tool requests.
*   `DEV_BEARER_TOKEN`: A bearer token (password) for developers to create to directly invoke the agent via the `/diagnose` endpoint.
*   `TOOLS`: A JSON string array listing the enabled tools. Example: `'["list_pods", "get_logs", "get_file_contents", "slack_post_message"]'`
*   `QUERY_TIMEOUT`: The maximum time (in seconds) allowed for the agent to diagnose an issue. (Default: `300`)
*   `TARGET_EKS_CLUSTER_NAME`: The name of the target AWS EKS cluster the agent will interact with.
*   `AWS_REGION`: The AWS region where the target EKS cluster is located.
*   `AWS_ACCOUNT_ID` (Optional): The AWS account ID where container images are stored. Required only if pulling images from AWS ECR.

<details>
<summary>Deploy with ECR images</summary>

See [ECR Setup](docs/ecr-setup.md) for details on how to enable pulling images from ECR.

```
docker compose -f compose.ecr.yaml up
```

</details>


<details>
<summary>Deploy by building images locally</summary>

```
docker compose up
```

</details>

> [!NOTE]
> AWS credentials must be stored in your `~/.aws/credentials` file.

## MCP Server Claude Desktop Setup

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [npx](https://docs.npmjs.com/cli/v8/commands/npx)

### [Slack](sre_agent/servers/slack/README.md)

A slack agent for acting on behalf of an `sre-agent` Slack bot using the [Slack MCP server](https://github.com/modelcontextprotocol/servers/tree/main/src/slack).

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

# &#127939; How Do I get Started (Development)?

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
* [ECR Setup Steps](docs/ecr-setup.md)
* [Agent Architecture](docs/agent-architecture.md)
* [Production Journey](docs/production-journey.md)

# Acknowledgements + attribution

We would like to thank:

[Suyog Sonwalkar](https://github.com/Flux159) for creating the [Kubernetes MCP server](/sre_agent/servers/mcp-server-kubernetes/): https://github.com/Flux159/mcp-server-kubernetes

[Anthropic's Model Context Protocol team](https://github.com/modelcontextprotocol) for creating the [Slack](/sre_agent/servers/slack/) and [GitHub](/sre_agent/servers/github/) MCP servers: https://github.com/modelcontextprotocol/servers?tab=MIT-1-ov-file#readme
