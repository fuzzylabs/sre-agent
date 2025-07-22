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
# Local development - AWS
docker compose -f compose.aws.yaml up --build

# Local development - GCP
docker compose -f compose.gcp.yaml up --build

# Production with ECR images
docker compose -f compose.ecr.yaml up

# Production with GAR images (Google)
docker compose -f compose.gar.yaml up

# Test environment
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

### Environment Variables Required
- `DEV_BEARER_TOKEN`: API authentication for the orchestrator
- `ANTHROPIC_API_KEY`: Claude API access (for Anthropic models)
- `GEMINI_API_KEY`: Google Gemini API access (for Gemini models)
- `GITHUB_PERSONAL_ACCESS_TOKEN`: GitHub integration
- `SLACK_BOT_TOKEN`, `SLACK_TEAM_ID`, `CHANNEL_ID`: Slack notifications
- `AWS_REGION`, `TARGET_EKS_CLUSTER_NAME`: AWS EKS cluster access
- `GCP_PROJECT_ID`, `TARGET_GKE_CLUSTER_NAME`, `GKE_ZONE`: GCP GKE cluster access
- `HF_TOKEN`: Hugging Face model access

### Cloud Platform Setup
- **AWS**: Credentials must be available at `~/.aws/credentials` for EKS cluster access
- **GCP**: Use `gcloud auth login` and `gcloud config set project YOUR_PROJECT_ID` for GKE access

### Credential Setup Script
Use the interactive setup script for easy configuration:
```bash
python setup_credentials.py
# or with platform selection
python setup_credentials.py --platform aws
python setup_credentials.py --platform gcp
```

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
- **Local**: Docker Compose with local builds (AWS: `compose.aws.yaml`, GCP: `compose.gcp.yaml`)
- **Production AWS**: ECR-based images on AWS EKS (`compose.ecr.yaml`)
- **Production GCP**: GAR-based images on GCP GKE (`compose.gar.yaml`)
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
