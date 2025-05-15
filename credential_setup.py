"""A script for creating a credentials file with secrets."""

import argparse
from getpass import getpass


def main(helm: bool) -> None:
    """The main function for creating a credentials file with secrets."""
    print("Let's populate your credentials file.")

    secrets = {
        "SLACK_BOT_TOKEN": getpass(
            "Enter your Slack Bot Token. If you haven’t set up a Slack app yet, check "
            "out this article https://api.slack.com/apps to create one: "
        ),
        "SLACK_TEAM_ID": input("Enter your Slack Team ID: "),
        "CHANNEL_ID": input("Enter your Slack Channel ID: "),
        "GITHUB_PERSONAL_ACCESS_TOKEN": getpass(
            "Enter your Github Personal Access Token: "
        ),
        "ANTHROPIC_API_KEY": getpass("Enter your Anthropic API Key: "),
        "DEV_BEARER_TOKEN": getpass(
            "Enter a bearer token (password) for developers to directly invoke the "
            "agent via the `/diagnose` endpoint. (This can be anything): "
        ),
        "SLACK_SIGNING_SECRET": getpass(
            "Enter the signing secret associated with the Slack `sre-agent` "
            "application: "
        ),
        "AWS_REGION": input("Enter your AWS region: "),
        "AWS_ACCOUNT_ID": input("Enter your AWS account ID: "),
        "TARGET_EKS_CLUSTER_NAME": input(
            "Enter your target EKS cluster name (the cluster the agent will interact "
            "with): "
        ),
        "SERVICES": str(
            input(
                "Enter the services running on the cluster (comma-separated): "
            ).split(",")
        ),
        "HF_TOKEN": getpass(
            "Enter your Hugging Face API token, ensure this has read access to "
            "https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M, read the "
            "following article (https://huggingface.co/docs/hub/en/security-tokens) "
            "to set up this token: "
        ),
    }

    if helm:
        env_lines = [f"{key.lower()}={value}" for key, value in secrets.items()]
        filename = "charts/sre-agent/values-secrets.yaml"
    else:
        env_lines = [f"{key}={value}" for key, value in secrets.items()]
        filename = ".env"

    with open(filename, "w") as f:
        f.write("\n".join(env_lines))

    print(".env file created successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a credentials file with secrets."
    )

    parser.add_argument(
        "--helm",
        action="store_true",
        help="Generate a helm values-secrets.yaml file instead of a .env file.",
    )

    args = parser.parse_args()

    main(args.helm)
