#!/usr/bin/env python3
"""A script for setting up credentials for local development."""

import argparse
import os
from typing import Any, Optional


def mask_credential(value: str, mask_value: bool, show_chars: int = 3) -> str:
    """Mask a credential value, showing only the first and last few characters."""
    if not value or not mask_value:
        return value

    # For short values, just mask everything
    if len(value) <= show_chars * 2:
        return "*" * len(value)

    return (
        f"{value[:show_chars]}{'*' * (len(value) - show_chars * 2)}"
        f"{value[-show_chars:]}"
    )


def read_env_file(filename: str = ".env") -> dict[str, str]:
    """Read environment variables from a .env file."""
    env_vars: dict[str, str] = {}

    if not os.path.exists(filename):
        return env_vars

    try:
        with open(filename) as f:
            for file_line in f:
                line = file_line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()
    except Exception as e:
        print(f"Error reading {filename}: {e}")

    return env_vars


def get_credential_config(platform: str) -> dict[str, dict[str, Any]]:
    """Get the credential configuration for the specified platform.

    Config structure:
    - mask_value: When displaying existing values,
        show masked (True) vs full value (False)
    """
    # Common credentials for both platforms
    common_creds = {
        "SLACK_BOT_TOKEN": {
            "prompt": "Enter your Slack Bot Token. If you haven't set up a Slack "
            "app yet, check out this article https://api.slack.com/apps "
            "to create one: ",
            "mask_value": True,
        },
        "SLACK_SIGNING_SECRET": {
            "prompt": "Enter the signing secret associated with the Slack "
            "`sre-agent` application: ",
            "mask_value": True,
        },
        "SLACK_TEAM_ID": {"prompt": "Enter your Slack Team ID: ", "mask_value": False},
        "SLACK_CHANNEL_ID": {
            "prompt": "Enter your Slack Channel ID: ",
            "mask_value": False,
        },
        "GITHUB_PERSONAL_ACCESS_TOKEN": {
            "prompt": "Enter your Github Personal Access Token: ",
            "mask_value": True,
        },
        "GITHUB_ORGANISATION": {
            "prompt": "Enter your Github organisation name: ",
            "mask_value": False,
        },
        "GITHUB_REPO_NAME": {
            "prompt": "Enter your Github repository name: ",
            "mask_value": False,
        },
        "PROJECT_ROOT": {
            "prompt": "Enter your Github project root directory: ",
            "mask_value": False,
        },
        "PROVIDER": {"prompt": "Enter your LLM provider name: ", "mask_value": False},
        "MODEL": {"prompt": "Enter your LLM model name: ", "mask_value": False},
        "GEMINI_API_KEY": {"prompt": "Enter your Gemini API Key: ", "mask_value": True},
        "ANTHROPIC_API_KEY": {
            "prompt": "Enter your Anthropic API Key: ",
            "mask_value": True,
        },
        "MAX_TOKENS": {
            "prompt": "Controls the maximum number of tokens the LLM can generate in "
            "its response e.g. 10000: ",
            "mask_value": False,
        },
        "DEV_BEARER_TOKEN": {
            "prompt": "Enter a bearer token (password) for developers to "
            "directly invoke the agent via the `/diagnose` endpoint. "
            "(This can be anything): ",
            "mask_value": True,
        },
        "HF_TOKEN": {
            "prompt": "Enter your Hugging Face API token, ensure this has read "
            "access to https://huggingface.co/meta-llama/"
            "Llama-Prompt-Guard-2-86M, read the following article "
            "(https://huggingface.co/docs/hub/en/security-tokens) "
            "to set up this token: ",
            "mask_value": True,
        },
    }

    if platform == "aws":
        aws_specific = {
            "AWS_REGION": {"prompt": "Enter your AWS region: ", "mask_value": False},
            "AWS_ACCOUNT_ID": {
                "prompt": "Enter your AWS account ID: ",
                "mask_value": False,
            },
            "TARGET_EKS_CLUSTER_NAME": {
                "prompt": "Enter your target EKS cluster name (the cluster the "
                "agent will interact with): ",
                "mask_value": False,
            },
        }
        return {**common_creds, **aws_specific}

    elif platform == "gcp":
        gcp_specific = {
            "QUERY_TIMEOUT": {
                "prompt": "Enter your query timeout (e.g. 300): ",
                "mask_value": False,
            },
            "CLOUDSDK_CORE_PROJECT": {
                "prompt": "Enter your GCP project ID: ",
                "mask_value": False,
            },
            "CLOUDSDK_COMPUTE_REGION": {
                "prompt": "Enter your GCP region: ",
                "mask_value": False,
            },
            "TARGET_GKE_CLUSTER_NAME": {
                "prompt": "Enter your target GKE cluster name (the cluster the "
                "agent will interact with): ",
                "mask_value": False,
            },
        }
        return {**common_creds, **gcp_specific}

    else:
        raise ValueError(
            f"Unsupported platform: {platform}. Supported "
            "platforms are 'aws' and 'gcp'."
        )


def display_current_credentials(
    credentials: dict[str, str], creds_config: dict[str, dict[str, Any]]
) -> None:
    """Display current credentials with appropriate masking based on config."""
    if not credentials:
        print("No existing credentials found.")
        return

    print("\nCurrent credentials:")
    print("-" * 50)

    for key, value in credentials.items():
        config = creds_config.get(key, {})
        mask_value = config.get("mask_value", True)  # Default to masking
        masked_value = mask_credential(value, mask_value)
        print(f"{key}: {masked_value}")

    print("-" * 50)


def get_credential_input(
    prompt: str, current_value: Optional[str] = None, mask_value: bool = True
) -> str:
    """Get credential input from user, showing current value if it exists."""
    if current_value:
        # Show the current value (masked or unmasked based on mask_value)
        displayed_current = mask_credential(current_value, mask_value)
        display_prompt = (
            f"{prompt}\nCurrent value: {displayed_current}\n"
            "Press Enter to keep current value, or enter new value: "
        )
    else:
        display_prompt = prompt

    # Use regular input for all inputs
    new_value = input(display_prompt)

    # If user pressed Enter and there's a current value, keep it
    if not new_value and current_value:
        return current_value

    return new_value


def handle_comma_separated_input(
    key: str, prompt: str, existing_creds: dict[str, str]
) -> str:
    """Handle input for comma-separated values like SERVICES and TOOLS."""
    current_value = existing_creds.get(key, "")
    if current_value.startswith("['") and current_value.endswith("']"):
        # Convert from string representation back to comma-separated
        current_value = current_value[2:-2].replace("', '", ",")

    user_input = input(
        f"{prompt}:\nCurrent value: {current_value}\n"
        "Press Enter to keep current value, or enter new value: "
    )

    if not user_input and current_value:
        return existing_creds.get(key, "")
    else:
        return str(user_input.split(",")) if user_input else str([])


def get_platform_credentials(
    platform: str, existing_creds: dict[str, str]
) -> dict[str, str]:
    """Get credentials for the specified platform."""
    print(f"Setting up {platform.upper()} credentials...")

    credentials = {}
    creds_config = get_credential_config(platform)

    # Process standard credentials
    for key, config in creds_config.items():
        credentials[key] = get_credential_input(
            config["prompt"], existing_creds.get(key), config["mask_value"]
        )

    # Handle special cases for comma-separated values
    credentials["SERVICES"] = handle_comma_separated_input(
        "SERVICES",
        "Enter the services running on the cluster (comma-separated)",
        existing_creds,
    )

    credentials["TOOLS"] = handle_comma_separated_input(
        "TOOLS", "Enter the tools you want to utilise (comma-separated)", existing_creds
    )

    return credentials


def detect_platform_from_env(existing_creds: dict[str, str]) -> Optional[str]:
    """Detect platform from existing environment variables."""
    aws_indicators = ["AWS_REGION", "AWS_ACCOUNT_ID", "TARGET_EKS_CLUSTER_NAME"]
    gcp_indicators = [
        "CLOUDSDK_CORE_PROJECT",
        "CLOUDSDK_COMPUTE_REGION",
        "TARGET_GKE_CLUSTER_NAME",
    ]

    aws_count = sum(1 for key in aws_indicators if key in existing_creds)
    gcp_count = sum(1 for key in gcp_indicators if key in existing_creds)

    if aws_count > gcp_count:
        return "aws"
    elif gcp_count > aws_count:
        return "gcp"

    return None


def create_env_file(credentials: dict[str, str], filename: str = ".env") -> None:
    """Create .env file with the provided credentials."""
    env_lines = [f"{key}={value}" for key, value in credentials.items()]

    with open(filename, "w") as f:
        f.write("\n".join(env_lines))

    print(f"{filename} file created successfully.")


def main() -> None:
    """Main function to set up credentials."""
    parser = argparse.ArgumentParser(description="SRE Agent Credential Setup")
    parser.add_argument(
        "--platform",
        choices=["aws", "gcp"],
        help="Specify platform (aws/gcp) to skip platform selection",
    )

    args = parser.parse_args()

    print("=== SRE Agent Credential Setup ===")
    print("This script will help you set up credentials for running the agent locally.")

    # Read existing credentials
    existing_creds = read_env_file()

    # Ask for platform choice first to get the right config
    platform = args.platform
    if not platform:
        detected_platform = detect_platform_from_env(existing_creds)
        if detected_platform:
            use_detected = (
                input(
                    f"\nDetected platform: "
                    f"{detected_platform.upper()}. Use this? "
                    "(y/n): "
                )
                .lower()
                .strip()
            )
            if use_detected in ["y", "yes"]:
                platform = detected_platform

        if not platform:
            while True:
                platform = (
                    input("\nWhich platform is your target cluster on? (aws/gcp): ")
                    .lower()
                    .strip()
                )
                if platform in ["aws", "gcp"]:
                    break
                print("Please enter 'aws' or 'gcp'")

    print(f"\nYou selected: {platform.upper()}")

    # Show existing credentials if any
    if existing_creds:
        creds_config = get_credential_config(platform)
        display_current_credentials(existing_creds, creds_config)

    # Get credentials based on platform
    credentials = get_platform_credentials(platform, existing_creds)

    # Create .env file
    create_env_file(credentials)

    print("\n✅ Credentials saved to .env file!")
    print("\n🚀 Next steps:")
    print("   Start the containers manually with:")
    if platform == "aws":
        print("   docker compose -f compose.aws.yaml up")
    elif platform == "gcp":
        print("   docker compose -f compose.gcp.yaml up")


if __name__ == "__main__":
    main()
