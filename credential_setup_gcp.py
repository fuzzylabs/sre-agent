"""A script for creating a credentials file with secrets."""

from getpass import getpass


def main() -> None:
    """The main function for creating a credentials file with secrets."""
    print("Let's populate your credentials file.")

    secrets = {
        "SLACK_BOT_TOKEN": getpass(
            "Enter your Slack Bot Token. If you haven’t set up a Slack app yet, check "
            "out this article https://api.slack.com/apps to create one: "
        ),
        "SLACK_SIGNING_SECRET": getpass(
            "Enter the signing secret associated with the Slack `sre-agent` "
            "application: "
        ),
        "SLACK_TEAM_ID": input("Enter your Slack Team ID: "),
        "SLACK_CHANNEL_ID": input("Enter your Slack Channel ID: "),
        "GITHUB_PERSONAL_ACCESS_TOKEN": getpass(
            "Enter your Github Personal Access Token: "
        ),
        "GITHUB_ORGANISATION": getpass("Enter your Github organisation name: "),
        "GITHUB_REPO_NAME": getpass("Enter your Github repository name: "),
        "PROJECT_ROOT": getpass("Enter your Github project root directory: "),
        "PROVIDER": getpass("Enter your LLM provider name: "),
        "MODEL": getpass("Enter your LLM model name: "),
        "GEMINI_API_KEY": getpass("Enter your Gemini API Key: "),
        "DEV_BEARER_TOKEN": getpass(
            "Enter a bearer token (password) for developers to directly invoke the "
            "agent via the `/diagnose` endpoint. (This can be anything): "
        ),
        "QUERY_TIMEOUT": input("Enter your query timeout (e.g. 300): "),
        "CLOUDSDK_CORE_PROJECT": input("Enter your GCP region: "),
        "CLOUDSDK_COMPUTE_REGION": input("Enter your GCP project ID: "),
        "TARGET_GKE_CLUSTER_NAME": input(
            "Enter your target GKE cluster name (the cluster the agent will interact "
            "with): "
        ),
        "SERVICES": str(
            input(
                "Enter the services running on the cluster (comma-separated): "
            ).split(",")
        ),
        "TOOLS": str(
            input("Enter the tools you want to utilise (comma-separated): ").split(",")
        ),
        "HF_TOKEN": getpass(
            "Enter your Hugging Face API token, ensure this has read access to "
            "https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M, read the "
            "following article (https://huggingface.co/docs/hub/en/security-tokens) "
            "to set up this token: "
        ),
    }

    env_lines = [f"{key}={value}" for key, value in secrets.items()]
    filename = ".env"

    with open(filename, "w") as f:
        f.write("\n".join(env_lines))

    print(".env file created successfully.")


if __name__ == "__main__":
    main()
