# Credentials

The following credentials must be retrieved prior to running the agent. These credentials are required for the agent to function, allowing it to read Kubernetes logs, read GitHub files and make issues, and send messages in Slack.

## 🔧 Common Credentials (Required for All Platforms)

### Slack Configuration
- **SLACK_BOT_TOKEN**: The token for the sre-agent Slack bot. If you haven't set up a Slack app yet, check out this [page](https://api.slack.com/quickstart) to create one.
- **SLACK_SIGNING_SECRET**: The signing secret associated with the Slack sre-agent application.
- **SLACK_TEAM_ID**: The ID of the Slack team where the agent operates.
- **SLACK_CHANNEL_ID**: The specific Slack channel ID for the agent's responses.

### GitHub Configuration
- **GITHUB_PERSONAL_ACCESS_TOKEN**: A GitHub personal access token with permissions to read relevant files and create issues.
- **GITHUB_ORGANISATION**: Your GitHub organisation name (e.g., "fuzzylabs").
- **GITHUB_REPO_NAME**: Your GitHub repository name (e.g., "sre-agent").
- **PROJECT_ROOT**: The root directory path within your GitHub project where relevant code is located.

### LLM Provider Configuration

> **Note**: You only need to configure **one** LLM provider. Choose either Anthropic or Google Gemini and provide the corresponding API key.

- **PROVIDER**: The LLM provider name (e.g., "anthropic", "google").
- **MODEL**: The specific model name to use (e.g., "claude-3-5-sonnet-20241022", "gemini-1.5-pro").

**Choose one of the following:**
- **ANTHROPIC_API_KEY**: An API key for Anthropic Claude models *(required if using Anthropic provider)*.
- **GEMINI_API_KEY**: An API key for Google Gemini models *(required if using Google provider)*.

### Security & Access
- **DEV_BEARER_TOKEN**: A bearer token (password) for developers to directly invoke the agent via the `/diagnose` endpoint. This can be any secure string you choose.
- **HF_TOKEN**: The Hugging Face Hub access token. Ensure this has read access to https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M. Read [this article](https://huggingface.co/docs/hub/en/security-tokens) to set up this token.

### Service Configuration
- **SERVICES**: Comma-separated list of services running on your cluster that the agent should monitor (e.g., "api,database,frontend").
- **TOOLS**: Comma-separated list of tools you want the agent to utilise (e.g., "kubectl,helm,logs").

## ☁️ AWS-Specific Credentials

Required when running on AWS EKS:

- **AWS_REGION**: Your AWS region (e.g., "us-west-2", "eu-west-1").
- **AWS_ACCOUNT_ID**: Your AWS account ID (12-digit number).
- **TARGET_EKS_CLUSTER_NAME**: The name of the target AWS EKS cluster the agent will interact with.

### AWS Authentication Setup
Ensure your AWS credentials are configured in `~/.aws/credentials`:
```bash
[default]
aws_access_key_id=YOUR_ACCESS_KEY
aws_secret_access_key=YOUR_SECRET_KEY
aws_session_token=YOUR_SESSION_TOKEN  # If using temporary credentials
```

## 🌐 GCP-Specific Credentials

Required when running on Google Cloud GKE:

- **CLOUDSDK_CORE_PROJECT**: Your GCP project ID.
- **CLOUDSDK_COMPUTE_REGION**: Your GCP region (e.g., "us-central1", "europe-west1").
- **TARGET_GKE_CLUSTER_NAME**: The name of the target GCP GKE cluster the agent will interact with.
- **QUERY_TIMEOUT**: Timeout for queries in seconds (e.g., "300").

### GCP Authentication Setup
Ensure your GCP credentials are configured using the gcloud CLI:
```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud container clusters get-credentials YOUR_CLUSTER_NAME --region YOUR_REGION
```

## 🚀 Quick Setup

Use our interactive setup script to configure all credentials:

```bash
python setup_credentials.py
```

The script will:
- Auto-detect your platform (AWS/GCP) or let you choose
- Guide you through each credential with helpful prompts
- Show current values (masked for security) and let you update them
- Create your `.env` file automatically

### Platform-Specific Setup

```bash
# For AWS
python setup_credenitals.py --platform aws

# For GCP
python setup_credenitals.py --platform gcp
