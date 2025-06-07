# Credentials

The following credentials must be retrieved prior to running the agent. These credentials are required for the agent to function, allowing it to read Kubernetes logs, read github files and make issues, and send messages in Slack.

- SLACK_BOT_TOKEN: The token for the sre-agent Slack bot. If you haven’t set up a Slack app yet, check out this [page](https://api.slack.com/quickstart) to create one.
- SLACK_TEAM_ID: The ID of the Slack team where the agent operates.
- SLACK_SIGNING_SECRET: The signing secret associated with the Slack sre-agent application.
- SLACK_CHANNEL_ID: The specific Slack channel ID for the agent's responses.
- GITHUB_PERSONAL_ACCESS_TOKEN: A GitHub personal access token with permissions to read relevant files.
- ANTHROPIC_API_KEY: An API key for Anthropic, used for processing tool requests.
- DEV_BEARER_TOKEN: A bearer token (password) for developers to directly invoke the agent via the `/diagnose` endpoint. (This can be anything)
- TARGET_EKS_CLUSTER_NAME: The name of the target AWS EKS cluster the agent will interact with.
- HF_TOKEN: The Hugging Face Hub access token, ensure this has read access to https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M, read the article here to set up this token.
