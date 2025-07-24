# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SRE Agent is an AI-powered Site Reliability Engineering assistant that automates debugging, monitors application/infrastructure logs, diagnoses issues, and reports diagnostics. It integrates with Kubernetes clusters, GitHub repositories, and Slack for comprehensive incident response automation.

## Architecture

### Microservices Design
The system uses a microservices architecture with the following components:

- **Orchestrator (Client)**: FastAPI-based MCP client (`sre_agent/client/`) that coordinates all services and handles incoming diagnostic requests
- **LLM Server**: Text generation service (`sre_agent/llm/`) supporting multiple AI providers (Anthropic, OpenAI, Gemini)
- **Llama Firewall**: Security layer (`sre_agent/firewall/`) using Meta's Llama Prompt Guard for content validation
- **MCP Servers**:
  - Kubernetes MCP (`sre_agent/servers/mcp-server-kubernetes/`) - TypeScript/Node.js K8s operations
  - GitHub MCP (`sre_agent/servers/github/`) - TypeScript/Node.js repository operations
  - Slack MCP (`sre_agent/servers/slack/`) - TypeScript/Node.js team notifications
  - Prompt Server MCP (`sre_agent/servers/prompt_server/`) - Python structured prompts

### Key Technologies
- **Languages**: Python 3.12+ (core services), TypeScript/Node.js (MCP servers)
- **Communication**: Model Context Protocol (MCP) with Server-Sent Events (SSE) transport
- **Infrastructure**: Docker Compose, AWS EKS deployment
- **AI/ML**: Multiple LLM providers, Hugging Face transformers

## Quick Start

### 🚀 Fastest Way to Try SRE Agent (2-5 minutes)
```bash
# 1. Basic setup
make project-setup

# 2. Quick setup with minimal credentials
uv run python setup_credentials.py --mode quick

# 3. Start with public images (NO BUILD TIME!)
docker compose -f compose.ghcr.yaml up
```

### 🔧 Production Setup
```bash
# 1. Complete setup with all features
uv run python setup_credentials.py --mode full --platform aws  # or gcp

# 2. Start production environment
docker compose -f compose.aws.yaml up  # or compose.gcp.yaml
```

### 🧪 Testing with Local Builds
```bash
# 1. Testing setup (only needs HF_TOKEN)
uv run python setup_credentials.py --mode testing

# 2. Start testing environment (builds locally - ~10-15 minutes first time)
docker compose -f compose.tests.yaml up --build
```

## Common Development Commands

### Project Setup
```bash
make project-setup    # Install uv, create venv, install pre-commit hooks
```

### Code Quality
```bash
make check           # Run linting, pre-commit hooks, and lock file check
make tests           # Run pytest with coverage
make license-check   # Verify dependency licenses
```

### Service Management
```bash
# Quick start with public images (FASTEST - 2-5 minutes)
docker compose -f compose.ghcr.yaml up

# Local development - AWS
docker compose -f compose.aws.yaml up --build

# Local development - GCP
docker compose -f compose.gcp.yaml up --build

# Production with ECR images
docker compose -f compose.ecr.yaml up

# Production with GAR images (Google)
docker compose -f compose.gar.yaml up

# Test environment (local builds)
docker compose -f compose.tests.yaml up
```

### Testing
```bash
# All tests
make tests

# Specific test file
uv run python -m pytest tests/unit_tests/test_adapters.py

# Specific test function
uv run python -m pytest tests/unit_tests/test_adapters.py::test_specific_function

# With coverage
uv run python -m pytest --cov --cov-config=pyproject.toml --cov-report=xml

# Security tests only
uv run python -m pytest tests/security_tests/
```

## Configuration

### Environment Variables by Priority

#### 🔴 Essential (Required for basic functionality)
- `DEV_BEARER_TOKEN`: API authentication for the orchestrator
- `HF_TOKEN`: Hugging Face token for Llama Firewall security validation
- `PROVIDER`: LLM provider (anthropic, gemini, or mock)
- `MODEL`: LLM model name
- At least one of: `ANTHROPIC_API_KEY` or `GEMINI_API_KEY` (unless using mock)

#### 🟡 Feature-Specific (Required for specific integrations)
- **Slack Integration**: `SLACK_BOT_TOKEN`, `SLACK_TEAM_ID`
- **GitHub Integration**: `GITHUB_PERSONAL_ACCESS_TOKEN`
- **AWS EKS**: `AWS_REGION`, `TARGET_EKS_CLUSTER_NAME`
- **GCP GKE**: `CLOUDSDK_CORE_PROJECT`, `TARGET_GKE_CLUSTER_NAME`

#### 🟢 Optional (Have sensible defaults)
- `MAX_TOKENS`: Token limit (default: 10000)
- `QUERY_TIMEOUT`: Request timeout (default: 300)
- `GITHUB_ORGANISATION`, `GITHUB_REPO_NAME`, `PROJECT_ROOT`: Repository metadata (defaults provided)
- `SERVICES`, `TOOLS`: Available services and tools (defaults provided)

### Cloud Platform Setup
- **AWS**: Credentials must be available at `~/.aws/credentials` for EKS cluster access
- **GCP**: Use `gcloud auth login` and `gcloud config set project YOUR_PROJECT_ID` for GKE access

### Credential Setup Script
The interactive setup script supports different modes for easy configuration:

```bash
# Quick mode - public images, minimal setup (FASTEST - 2-5 minutes!)
uv run python setup_credentials.py --mode quick

# Essential credentials only (basic functionality)
uv run python setup_credentials.py --mode minimal

# Quick testing setup (mock LLM, minimal credentials)
uv run python setup_credentials.py --mode testing

# Complete setup (all features)
uv run python setup_credentials.py --mode full

# With platform selection
uv run python setup_credentials.py --mode full --platform aws
uv run python setup_credentials.py --mode full --platform gcp
```

#### Setup Modes Explained:
- **Quick Mode**: Public images, minimal credentials - perfect for trying it out (2-5 minutes!)
- **Minimal Mode**: Essential credentials only - basic LLM functionality without integrations
- **Testing Mode**: Uses mock LLM provider, only requires HF_TOKEN for security validation
- **Full Mode**: All features enabled - Slack, GitHub, Kubernetes integrations

#### Example .env Templates:
- Copy `.env.testing` for quick local testing
- Copy `.env.minimal` for basic functionality
- Copy `.env.full` for production with all features

## Service Architecture Details

### Communication Flow
1. Orchestrator receives `/diagnose` requests on port 8003
2. Requests pass through Llama Firewall for security validation
3. LLM Server processes AI reasoning
4. MCP servers handle tool operations (K8s, GitHub, Slack)
5. Results reported back via Slack notifications

### Health Checks
All services implement health monitoring accessible via `/health` endpoints.

## Development Patterns

### MCP Integration
All external tool interactions use the Model Context Protocol standard. When adding new tools:
- Follow existing MCP server patterns in `sre_agent/servers/`
- Implement SSE transport for real-time communication
- Add health check endpoints

### Security Considerations
- All requests pass through Llama Firewall validation
- Bearer token authentication required for API access
- Input validation at multiple service layers
- No secrets in code - use environment variables

**IMPORTANT: Never commit the .env file!**
- The `.env` file contains sensitive credentials (API keys, tokens, secrets)
- It is included in `.gitignore` and should never be committed to the repository
- Use `python setup_credentials.py` to generate the `.env` file locally
- Each developer/environment needs their own `.env` file with appropriate credentials
- For production deployments, use proper secret management (AWS Secrets Manager, K8s secrets, etc.)

### Code Style
- Python: Uses ruff, black, mypy for formatting and type checking
- TypeScript: Standard TypeScript/Node.js conventions
- Line length: 88 characters
- Google-style docstrings for Python
- Strict type checking enabled

## Workspace Structure
This is a uv workspace with members:
- `sre_agent/llm`: LLM service with multi-provider support
- `sre_agent/client`: FastAPI orchestrator service
- `sre_agent/servers/prompt_server`: Python MCP server for structured prompts
- `sre_agent/firewall`: Llama Prompt Guard security layer
- `sre_agent/shared`: Shared utilities and schemas

Each Python service has its own `pyproject.toml`. TypeScript MCP servers use `package.json`:
- `sre_agent/servers/mcp-server-kubernetes/`: Kubernetes operations (Node.js/TypeScript)
- `sre_agent/servers/github/`: GitHub API integration (Node.js/TypeScript)
- `sre_agent/servers/slack/`: Slack notifications (Node.js/TypeScript)

## API Usage

### Primary Endpoint
```bash
POST http://localhost:8003/diagnose
Authorization: Bearer <DEV_BEARER_TOKEN>
Content-Type: application/json
{"text": "<service_name>"}
```

### Health Check
```bash
GET http://localhost:8003/health
```

## Deployment

### Deployment Options (by speed)
1. **Public Images (Fastest - 2-5 minutes)**: Use `compose.ghcr.yaml` with pre-built GHCR images
2. **Private Registry (5-10 minutes)**: Use `compose.ecr.yaml` or `compose.gar.yaml` with private images
3. **Local Builds (20-30 minutes)**: Use `compose.aws.yaml` or `compose.gcp.yaml` with local builds

### Build and Push Script
The enhanced `build_push_docker.sh` script supports multiple registries:

```bash
# Build and push to different registries
./build_push_docker.sh --ghcr      # Push to public GitHub Container Registry
./build_push_docker.sh --aws       # Push to private AWS ECR
./build_push_docker.sh --gcp       # Push to private GCP GAR
./build_push_docker.sh --dockerhub # Push to Docker Hub
./build_push_docker.sh --local     # Build locally only (no push)
```

**Requirements for each registry:**
- **GHCR**: `GITHUB_TOKEN` environment variable
- **AWS**: `AWS_ACCOUNT_ID`, `AWS_REGION` in .env + AWS credentials configured
- **GCP**: `CLOUDSDK_*` variables in .env + `gcloud auth login`
- **Docker Hub**: `DOCKER_USERNAME`, `DOCKER_TOKEN` environment variables
- **Local**: No additional requirements

### Deployment Methods
- **Quick Testing**: `compose.ghcr.yaml` (public images)
- **Local Development**: `compose.aws.yaml` or `compose.gcp.yaml` (local builds)
- **Production AWS**: `compose.ecr.yaml` (private ECR images)
- **Production GCP**: `compose.gar.yaml` (private GAR images)
- See [EKS Deployment](https://github.com/fuzzylabs/sre-agent-deployment) for cloud deployment examples

## TypeScript MCP Server Development
For TypeScript MCP servers in `sre_agent/servers/`:

### Building and Testing
```bash
# Kubernetes MCP server
cd sre_agent/servers/mcp-server-kubernetes
npm run build    # Build TypeScript
npm run test     # Run vitest tests
npm run dev      # Watch mode

# GitHub/Slack MCP servers
cd sre_agent/servers/github  # or /slack
npm run build
npm run watch    # Watch mode
```
