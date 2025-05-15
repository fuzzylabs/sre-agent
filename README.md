<h1 align="center">
    Site Reliability Engineer (SRE) Agent :detective:
</h1>

<h3 align="center">
    <p>Open-source implementation for an Site Reliability Engineer (SRE) AI Agent.</p>
</h3>

# What does it do?

SRE agent is an AI agent that can monitor application and infrastructure logs, diagnose issues, and report on diagnostics following an error in an application. Hook up your Kubernetes cluster, GitHub repository and Slack and let the agent summarise and diagnose issues to your team.

https://github.com/user-attachments/assets/5ef19428-d650-405d-ba88-848aeef58fef

## Why are we making it?

To gain a better understanding of best practices, costs, security and performance of AI agents in production systems, we wanted to create and share an example through open-source development. See our [Production Journey Page](/docs/production-journey.md) to see how we took the deployment of the agent and MCP servers from local to Kubernetes and our [Agent Architecture Page](/docs/agent-architecture.md) for more information on how our client and services are connected and used.

Please feel free to follow along and [contribute](CONTRIBUTING.md) to this repository!

## Features
- Debugging issues - finds the root cause of application and system errors
- Kubernetes logs - queries Kubernetes cluster for information and application logs
- GitHub server - search your application GitHub repository to find respective bugs in code
- Slack integration - report and update your team in Slack
- Triggerable from anywhere with a diagnose endpoint

We use the Model Context Protocol (MCP) created by Anthropic to connect the LLM to the provided tools.

This repository demonstrates how AI agents can accelerate your debugging process and reduce application downtime.

To run this demo, you'll need an application deployed on Kubernetes. If you don't have one yet, you can use our modified [microservices demo](https://github.com/fuzzylabs/microservices-demo) repository, where we have intentionally introduced errors to showcase the agent's diagnostic capabilities.

![ezgif com-speed](https://github.com/user-attachments/assets/42d4abc0-7df4-4062-a971-c5b0ddf112c9)

# Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- A configured `.env` file in the project root directory. See the [Environment Variables](#environment-variables) section below for details.
- An application deployed in AWS on Kubernetes for the agent to interact with.

# How do I get started?

We currently support two deployment methods for the MCP servers and client, one [locally](#deploy-agent-locally-using-docker-compose), and one on [AWS](#deploy-agent-on-amazon-elastic-kubernetes-services-eks).

The easiest way to run the agent is to use Docker Compose locally.

The fully orchestrated SRE Agent can be deployed with Docker Compose, which spins up all the required services — Slack, GitHub, the Kubernetes MCP servers, and an orchestration service that acts as a proxy between the LLM and the backend services. This orchestration service is the client in the context of MCP.

For Terraform-based infrastructure deployment, see the [terraform README](/terraform/README.md). The Terraform configuration sets up all required AWS resources including EKS cluster with proper access policies. Note that this configuration is not production-ready and provides only the bare minimum infrastructure required for a proof of concept deployment.

## Deploy Agent Locally using Docker Compose

Before running the agent, there are a few things we need to set up.

### 1. Giving the Agent Access to Your Kubernetes Cluster (i.e. the cluster where your application is running)

Currently, the agent only supports applications running on EKS (Elastic Kubernetes Service).

To connect your agent to EKS:

1. Go to your AWS access portal and click on Access keys:
![key](./docs/imgs/running_locally/access_key.png)

2. Choose Option 2, and copy the credentials into your ~/.aws/credentials file as shown:
![option_2](./docs/imgs/running_locally/option_2.png)

The file should look something like this:
```bash
[1233456789_AgentAccessRole]
aws_access_key_id=ABCDEFG12345
aws_secret_access_key=abcdefg123456789
aws_session_token=abcdefg123456789....=
```

3. Update the profile name to `[default]`, so it becomes:
```bash
[default]
aws_access_key_id=ABCDEFG12345
aws_secret_access_key=abcdefg123456789
aws_session_token=abcdefg123456789....=
```

### 2. Credentials Setup

This project requires several environment variables for configuration. A template file, `.env.example`, is provided in the root directory as a reference.

We have provided a helper setup script to help you set up the `.env` file. You can run the following command to create a new `.env` file:

```bash
python credential_setup.py
```

### 3. Running the agent

To start the agent, simply run:
```bash
docker compose up --build
```

<details>
<summary>Deploy with ECR images</summary>

See [ECR Setup](docs/ecr-setup.md) for details on how to enable pulling images from ECR.

```
docker compose -f compose.ecr.yaml up
```

</details>

> [!NOTE]
> AWS credentials must be stored in your `~/.aws/credentials` file.

Once everything is up and running, you should see output similar to this:
```bash
...
orchestrator-1   |    FastAPI   Starting production server 🚀
orchestrator-1   |
orchestrator-1   |              Searching for package file structure from directories with
orchestrator-1   |              __init__.py files
kubernetes-1     | ✅ Kubeconfig updated successfully.
kubernetes-1     | 🚀 Starting Node.js application...
orchestrator-1   |              Importing from /
orchestrator-1   |
orchestrator-1   |     module   📁 app
orchestrator-1   |              ├── 🐍 __init__.py
orchestrator-1   |              └── 🐍 client.py
orchestrator-1   |
orchestrator-1   |       code   Importing the FastAPI app object from the module with the following
orchestrator-1   |              code:
orchestrator-1   |
orchestrator-1   |              from app.client import app
orchestrator-1   |
orchestrator-1   |        app   Using import string: app.client:app
orchestrator-1   |
orchestrator-1   |     server   Server started at http://0.0.0.0:80
orchestrator-1   |     server   Documentation at http://0.0.0.0:80/docs
orchestrator-1   |
orchestrator-1   |              Logs:
orchestrator-1   |
orchestrator-1   |       INFO   Started server process [1]
orchestrator-1   |       INFO   Waiting for application startup.
orchestrator-1   |       INFO   Application startup complete.
orchestrator-1   |       INFO   Uvicorn running on http://0.0.0.0:80 (Press CTRL+C to quit)
kubernetes-1     | 2025-04-24 12:53:00 [info]: Initialising Kubernetes manager {
kubernetes-1     |   "service": "kubernetes-server"
kubernetes-1     | }
kubernetes-1     | 2025-04-24 12:53:00 [info]: Kubernetes manager initialised successfully {
kubernetes-1     |   "service": "kubernetes-server"
kubernetes-1     | }
kubernetes-1     | 2025-04-24 12:53:00 [info]: Starting SSE server {
kubernetes-1     |   "service": "kubernetes-server"
kubernetes-1     | }
kubernetes-1     | 2025-04-24 12:53:00 [info]: mcp-kubernetes-server is listening on port 3001
kubernetes-1     | Use the following url to connect to the server:
kubernetes-1     | http://localhost:3001/sse {
kubernetes-1     |   "service": "kubernetes-server"
kubernetes-1     | }
```

This means all the services — Slack, GitHub, the orchestrator, the prompt and the MCP servers have started successfully and are ready to handle requests.

### 4. Using the agent

Once the agent is up and running, you can trigger the SRE Agent by sending a request to the orchestrator service:

```bash
curl -X POST http://localhost:8003/diagnose \
  -H "accept: application/json" \
  -H "Authorization: Bearer <token>" \
  -d "text=<service>"
```

Replace `<token>` with your dev bearer token (e.g. whatever you set in .env), and `<service>` with the name of the Kubernetes service in your target cluster you'd like the agent to investigate.

This will kick off the diagnostic process using the connected Slack, GitHub, and Kubernetes MCP services.

Once the agent has finished, you should receive a response in the Slack channel you configured in your `.env` file under `CHANNEL_ID`.

<details>
<summary>:warning: Checking Service Health</summary>
A `/health` endpoint is available on the orchestrator service to check its status and the connectivity to its dependent MCP servers. This is useful for liveness/readiness probes or for debugging connection issues.

To check the health, run:

```bash
curl -X GET http://localhost:8003/health
```

*   A `200 OK` response indicates the orchestrator has successfully connected to all required MCP servers and they are responsive. The response body will list the healthy connected servers.
*   A `503 Service Unavailable` response indicates an issue, either with the orchestrator's initialisation or with one or more MCP server connections. The response body will contain details about the failure.
</details>

# Running the agent on AWS

## Deploy Agent on Amazon Elastic Kubernetes Services (EKS)

See the [kubernetes-deployment.md](/docs/kubernetes-deployment.md) page for instructions on how to deploy the Agent to EKS.

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- A configured `values-secrets.yaml` file in the root of the [`charts/sre-agent`](charts/sre-agent) directory. See the template [`values-secrets.yaml.example`](charts/sre-agent/values-secrets.yaml.example) file for all required secrets.
- An application deployed in AWS on Kubernetes for the agent to interact with.
- A Slackbot created inside of your Slack account. See [Create Slackbot](https://docs.slack.dev/quickstart) to see how to create a Slackbot.

## Security Tests

Inside the [`tests`](tests) directory are a collection of [security tests](/tests/security_tests) that can be run to ensure defences against possible prompt-injection threats against the agent. Agentic systems can be vulnerable to prompt-injection attacks where an attacker can manipulate the input to the agent to perform unintended actions. These tests are designed to ensure that the agent is robust against such attacks.

To run the security tests, first launch the agent using the `compose.tests.yaml` file:

```bash
docker compose -f compose.tests.yaml up --build
```

Then, in a separate terminal, run the security tests:
```bash
uv run pytest tests/security_tests
```

We are currently testing for the following vulnerabilities:
- [X] Prompt Injection via `/diagnose` endpoint
- [X] Prompt Injection via Kubernetes logs
- [ ] Prompt Injection via application
- [ ] Prompt Injection via GitHub files

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
