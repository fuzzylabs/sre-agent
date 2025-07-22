<h1 align="center">
    🚀 Site Reliability Engineer (SRE) Agent :detective:
</h1>

Welcome to the **SRE Agent** project! This open-source AI agent is here to assist your debugging, keep your systems healthy, and make your DevOps life a whole lot easier. Plug in your Kubernetes cluster, GitHub repo, and Slack, and let the agent do the heavy lifting—diagnosing, reporting, and keeping your team in the loop.

## 🌟 What is SRE Agent?

SRE Agent is your AI-powered teammate for monitoring application and infrastructure logs, diagnosing issues, and reporting diagnostics after errors. It connects directly into your stack, so you can focus on building, not firefighting.

![SRE Agent in action](https://github.com/user-attachments/assets/5ef19428-d650-405d-ba88-848aeef58fef)

## 🤔 Why Did We Build This?

We wanted to learn best practices, costs, security, and performance tips for AI agents in production. Our journey is open-source—check out our [Production Journey Page](/docs/production-journey.md) and [Agent Architecture Page](/docs/agent-architecture.md) for the full story.

We've been writing blogs and sharing our learnings along the way. Check out our [blog](https://www.fuzzylabs.ai/blog) for insights and updates.

> **Contributions welcome!** [Join us](CONTRIBUTING.md) and help shape the future of AI-powered SRE.

## ✨ Features

- 🕵️‍♂️ **Root Cause Debugging** – Finds the real reason behind app and system errors
- 📜 **Kubernetes Logs** – Queries your cluster for logs and info
- 🔍 **GitHub Search** – Digs through your codebase for bugs
- 💬 **Slack Integration** – Notifies and updates your team
- 🚦 **Diagnose from Anywhere** – Trigger diagnostics with a simple endpoint

> Powered by the [Model Context Protocol (MCP)](https://github.com/modelcontextprotocol) for seamless LLM-to-tool connectivity.

## 🤖 Supported LLM Providers

The SRE Agent supports multiple the following LLM providers:

### Anthropic
- **Models**: e.g. "claude-4-0-sonnet-latest"
- **Setup**: Requires `ANTHROPIC_API_KEY`

### Google Gemini
- **Models**: e.g, "gemini-2.5-flash"
- **Setup**: Requires `GEMINI_API_KEY`


## 🛠️ Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- A `.env` file in your project root ([see below](#getting-started))
- An app deployed on AWS EKS (Elastic Kubernetes Service) or GCP GKE (Google Kubernetes Engine)

## ⚡ Quick Start (5 minutes)

### 1️⃣ Set up credentials
```bash
python setup_credentials.py --platform aws  # or --platform gcp
```

### 2️⃣ Configure cloud access
**AWS:** Add credentials to `~/.aws/credentials` | **GCP:** Run `gcloud auth login`

### 3️⃣ Deploy with pre-built images (fastest!)
```bash
# AWS ECR (recommended)
aws ecr get-login-password --region [YOUR_REGION] | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.[YOUR_REGION].amazonaws.com
docker compose -f compose.ecr.yaml up -d

# OR GCP GAR
gcloud auth configure-docker [YOUR_REGION]-docker.pkg.dev
docker compose -f compose.gar.yaml up -d
```

### 4️⃣ Test it works
```bash
curl -X POST http://localhost:8003/diagnose \
  -H "Authorization: Bearer $(grep DEV_BEARER_TOKEN .env | cut -d'=' -f2)" \
  -d '{"text": "your-service-name"}'
```

---

## 📋 Detailed Setup Guide

<details>
<summary>🔧 Step-by-step credential configuration</summary>

### Interactive Credential Setup

Use our interactive setup script to configure your credentials:

```bash
python setup_credentials.py
```

The script will:
- ✅ Auto-detect your platform (AWS/GCP) or let you choose
- ✅ Guide you through credential setup with helpful prompts
- ✅ Show current values and let you update them
- ✅ Create your `.env` file automatically

**Quick start with platform selection:**
```bash
python setup_credentials.py --platform aws
# or
python setup_credentials.py --platform gcp
```

### Manual Cloud Credential Setup

#### For AWS EKS:
1. Go to your AWS access portal and grab your access keys:
   ![key](./docs/imgs/running_locally/access_key.png)
2. Choose Option 2 and copy credentials into `~/.aws/credentials`:
   ![option_2](./docs/imgs/running_locally/option_2.png)

   ```bash
   [default]
   aws_access_key_id=ABCDEFG12345
   aws_secret_access_key=abcdefg123456789
   aws_session_token=abcdefg123456789....=
   ```

#### For GCP GKE:
Set up your GCP credentials using the gcloud CLI:
```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

</details>

## 🚀 Deployment Options

### **Recommended: Pre-built Registry Images (2-5 minutes)**

Use pre-built container images for the fastest deployment:

**AWS ECR (Fastest):**
```bash
# Authenticate with ECR
aws ecr get-login-password --region [YOUR_REGION] | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.[YOUR_REGION].amazonaws.com

# Deploy with pre-built images
docker compose -f compose.ecr.yaml up -d
```

**GCP GAR:**
```bash
# Authenticate with GAR
gcloud auth configure-docker [YOUR_REGION]-docker.pkg.dev

# Deploy with pre-built images
docker compose -f compose.gar.yaml up -d
```

### **Alternative: Local Build (20-30 minutes)**

If you need to build from source or modify the code:

**For AWS:**
```bash
docker compose -f compose.aws.yaml up --build
```

**For GCP:**
```bash
docker compose -f compose.gcp.yaml up --build
```

### **For Developers: Building and Pushing New Images**

If you're developing features or need to create new registry images:

**Build and Push to AWS ECR:**
```bash
# Build and push all services to ECR
./build_push_docker.sh --aws

# Or set environment variables and run manually
export AWS_REGION=your-region
export AWS_ACCOUNT_ID=your-account-id
./build_push_docker.sh --aws
```

**Build and Push to GCP GAR:**
```bash
# Build and push all services to GAR
./build_push_docker.sh --gcp

# Or set environment variables and run manually
export CLOUDSDK_COMPUTE_REGION=your-region
export CLOUDSDK_CORE_PROJECT=your-project-id
./build_push_docker.sh --gcp
```

**What the build script does:**
- Builds all 7 microservices with `--platform linux/amd64` for consistency
- Tags images with `:dev` for development or `:latest` for production
- Pushes to your configured registry (ECR or GAR)
- **Takes 15-20 minutes** but only needs to be done once per code change

**After pushing new images, use them with:**
```bash
# Pull your new images and deploy
docker compose -f compose.ecr.yaml pull
docker compose -f compose.ecr.yaml up -d
```

> **Note:** AWS credentials must be in your `~/.aws/credentials` file.

You'll see logs like this when everything's running:

```bash
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

## 🧑‍💻 Using the Agent

Trigger a diagnosis with a simple curl command:

```bash
curl -X POST http://localhost:8003/diagnose \
  -H "accept: application/json" \
  -H "Authorization: Bearer <token>" \
  -d "text=<service>"
```

- Replace `<token>` with your dev bearer token (from `.env`)
- Replace `<service>` with the name of your target Kubernetes service

The agent will do its thing and report back in your configured Slack channel 🎉

<details>
<summary>🩺 Checking Service Health</summary>

A `/health` endpoint is available on the orchestrator service:

```bash
curl -X GET http://localhost:8003/health
```

- `200 OK` = All systems go!
- `503 Service Unavailable` = Something's up; check the response for details.

</details>

<details>
<summary>🔧 Deployment Troubleshooting</summary>

**Common Issues:**

**ECR Authentication Errors:**
```bash
# Ensure your AWS region matches your .env file
aws configure get region
# Should match AWS_REGION in your .env file

# Re-authenticate with ECR if login fails
aws ecr get-login-password --region eu-west-2 | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.eu-west-2.amazonaws.com
```

**Image Pull Errors:**
- Check that `AWS_ACCOUNT_ID` and `AWS_REGION` in your `.env` file match your actual AWS account
- Ensure you have ECR permissions in your AWS IAM role
- For missing images, the build-and-push script can create them: `./build_push_docker.sh --aws`

**Long Build Times:**
- Use pre-built registry images (`compose.ecr.yaml` or `compose.gar.yaml`) instead of local builds
- Registry deployment takes 2-5 minutes vs 20-30 minutes for local builds

</details>

## 🚀 Deployments

Want to run this in the cloud? Check out our deployment examples:

- [EKS Deployment](https://github.com/fuzzylabs/sre-agent-deployment)

---

## 🔧 For Developers

<details>
<summary>📦 Development Workflow</summary>

### Project Structure
This is a uv workspace with multiple Python services and TypeScript MCP servers:
- `sre_agent/client/`: FastAPI orchestrator (Python)
- `sre_agent/llm/`: LLM service with multi-provider support (Python)
- `sre_agent/firewall/`: Llama Prompt Guard security layer (Python)
- `sre_agent/servers/mcp-server-kubernetes/`: Kubernetes operations (TypeScript)
- `sre_agent/servers/github/`: GitHub API integration (TypeScript)
- `sre_agent/servers/slack/`: Slack notifications (TypeScript)
- `sre_agent/servers/prompt_server/`: Structured prompts (Python)

### Development Commands
```bash
make project-setup    # Install uv, create venv, install pre-commit hooks
make check            # Run linting, pre-commit hooks, and lock file check
make tests            # Run pytest with coverage
make license-check    # Verify dependency licenses
```

### Building Custom Images
```bash
# Build and push to your registry
./build_push_docker.sh --aws    # for AWS ECR
./build_push_docker.sh --gcp    # for GCP GAR

# Use your custom images
docker compose -f compose.ecr.yaml pull
docker compose -f compose.ecr.yaml up -d
```

### TypeScript MCP Servers
```bash
# Kubernetes MCP server
cd sre_agent/servers/mcp-server-kubernetes
npm run build && npm run test

# GitHub/Slack MCP servers
cd sre_agent/servers/github  # or /slack
npm run build && npm run watch
```

</details>

## 📚 Documentation

Find all the docs you need in the [docs](docs) folder:

- [Creating an IAM Role](docs/creating-an-iam-role.md)
- [ECR Setup Steps](docs/ecr-setup.md)
- [Agent Architecture](docs/agent-architecture.md)
- [Production Journey](docs/production-journey.md)
- [Credentials](docs/credentials.md)
- [Security Testing](docs/security-testing.md)

## 🙏 Acknowledgements & Attribution

Big thanks to:

- [Suyog Sonwalkar](https://github.com/Flux159) for the [Kubernetes MCP server](/sre_agent/servers/mcp-server-kubernetes/)
- [Anthropic's Model Context Protocol team](https://github.com/modelcontextprotocol) for the [Slack](/sre_agent/servers/slack/) and [GitHub](/sre_agent/servers/github/) MCP servers

## :book: Blogs

Check out our blog posts for insights and updates:

- [Bringing Agentic AI into the Real World](https://www.fuzzylabs.ai/blog-post/bringing-agentic-ai-into-the-real-world)
- [How We're Building an Autonomous SRE with FastMCP](https://www.fuzzylabs.ai/blog-post/how-were-building-an-autonomous-sre-with-fastmcp)
