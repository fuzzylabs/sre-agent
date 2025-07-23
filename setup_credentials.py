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


def get_credential_config(
    platform: str, mode: str = "full"
) -> dict[str, dict[str, Any]]:
    """Get the credential configuration for the specified platform and mode.

    Config structure:
    - mask_value: When displaying existing values,
        show masked (True) vs full value (False)
    - tier: essential, feature_specific, or optional
    - default: default value if any
    """
    # Essential credentials - required for basic functionality
    essential_creds = {
        "DEV_BEARER_TOKEN": {
            "prompt": "Enter a bearer token (password) for developers to "
            "directly invoke the agent via the `/diagnose` endpoint. "
            "(This can be anything): ",
            "mask_value": True,
            "tier": "essential",
            "default": "dev-token-123",
        },
        "HF_TOKEN": {
            "prompt": "Enter your Hugging Face API token, ensure this has read "
            "access to https://huggingface.co/meta-llama/"
            "Llama-Prompt-Guard-2-86M, read the following article "
            "(https://huggingface.co/docs/hub/en/security-tokens) "
            "to set up this token: ",
            "mask_value": True,
            "tier": "essential",
        },
        "PROVIDER": {
            "prompt": "Enter your LLM provider name (anthropic/gemini/mock): ",
            "mask_value": False,
            "tier": "essential",
            "default": "mock",
        },
        "MODEL": {
            "prompt": "Enter your LLM model name: ",
            "mask_value": False,
            "tier": "essential",
            "default": "claude-3-5-sonnet-20241022",
        },
    }

    # LLM provider credentials - at least one required
    llm_creds = {
        "ANTHROPIC_API_KEY": {
            "prompt": "Enter your Anthropic API Key "
            "(required if using anthropic provider): ",
            "mask_value": True,
            "tier": "essential_conditional",
        },
        "GEMINI_API_KEY": {
            "prompt": "Enter your Gemini API Key "
            "(required if using gemini provider): ",
            "mask_value": True,
            "tier": "essential_conditional",
        },
    }

    # Feature-specific credentials
    feature_creds = {
        "SLACK_BOT_TOKEN": {
            "prompt": "Enter your Slack Bot Token (for notifications). "
            "If you haven't set up a Slack app yet, check out this article "
            "https://api.slack.com/apps to create one: ",
            "mask_value": True,
            "tier": "feature_specific",
        },
        "SLACK_TEAM_ID": {
            "prompt": "Enter your Slack Team ID (for notifications): ",
            "mask_value": False,
            "tier": "feature_specific",
        },
        "GITHUB_PERSONAL_ACCESS_TOKEN": {
            "prompt": "Enter your Github Personal Access Token "
            "(for repository access): ",
            "mask_value": True,
            "tier": "feature_specific",
        },
    }

    # Optional credentials with defaults
    optional_creds = {
        "SLACK_SIGNING_SECRET": {
            "prompt": "Enter the signing secret associated with the Slack "
            "`sre-agent` application: ",
            "mask_value": True,
            "tier": "optional",
            "default": "null",
        },
        "SLACK_CHANNEL_ID": {
            "prompt": "Enter your Slack Channel ID: ",
            "mask_value": False,
            "tier": "optional",
            "default": "null",
        },
        "GITHUB_ORGANISATION": {
            "prompt": "Enter your Github organisation name: ",
            "mask_value": False,
            "tier": "optional",
            "default": "fuzzylabs",
        },
        "GITHUB_REPO_NAME": {
            "prompt": "Enter your Github repository name: ",
            "mask_value": False,
            "tier": "optional",
            "default": "microservices-demo",
        },
        "PROJECT_ROOT": {
            "prompt": "Enter your Github project root directory: ",
            "mask_value": False,
            "tier": "optional",
            "default": "src",
        },
        "MAX_TOKENS": {
            "prompt": "Controls the maximum number of tokens the LLM can generate in "
            "its response e.g. 10000: ",
            "mask_value": False,
            "tier": "optional",
            "default": "10000",
        },
        "QUERY_TIMEOUT": {
            "prompt": "Enter your query timeout in seconds (e.g. 300): ",
            "mask_value": False,
            "tier": "optional",
            "default": "300",
        },
    }

    # Combine credentials based on mode
    if mode == "minimal":
        common_creds = {**essential_creds, **llm_creds}
    elif mode == "testing":
        # For testing, use mock provider and minimal setup
        testing_creds = {
            **essential_creds,
            "GITHUB_ORGANISATION": optional_creds["GITHUB_ORGANISATION"],
            "GITHUB_REPO_NAME": optional_creds["GITHUB_REPO_NAME"],
            "PROJECT_ROOT": optional_creds["PROJECT_ROOT"],
        }
        # Override defaults for testing
        testing_creds["PROVIDER"]["default"] = "mock"
        testing_creds["MODEL"]["default"] = "mock-model"
        common_creds = testing_creds
    else:  # full mode
        common_creds = {
            **essential_creds,
            **llm_creds,
            **feature_creds,
            **optional_creds,
        }

    # Platform-specific credentials (only added in full mode unless minimal AWS/GCP 
    # testing)
    if platform == "aws" and mode != "testing":
        aws_specific = {
            "AWS_REGION": {
                "prompt": "Enter your AWS region: ",
                "mask_value": False,
                "tier": "feature_specific",
                "default": "us-east-1",
            },
            "AWS_ACCOUNT_ID": {
                "prompt": "Enter your AWS account ID: ",
                "mask_value": False,
                "tier": "feature_specific",
            },
            "TARGET_EKS_CLUSTER_NAME": {
                "prompt": "Enter your target EKS cluster name (the cluster the "
                "agent will interact with): ",
                "mask_value": False,
                "tier": "feature_specific",
            },
        }
        if mode == "full":
            common_creds.update(aws_specific)

    elif platform == "gcp" and mode != "testing":
        gcp_specific = {
            "CLOUDSDK_CORE_PROJECT": {
                "prompt": "Enter your GCP project ID: ",
                "mask_value": False,
                "tier": "feature_specific",
            },
            "CLOUDSDK_COMPUTE_REGION": {
                "prompt": "Enter your GCP region: ",
                "mask_value": False,
                "tier": "feature_specific",
                "default": "us-central1",
            },
            "TARGET_GKE_CLUSTER_NAME": {
                "prompt": "Enter your target GKE cluster name (the cluster the "
                "agent will interact with): ",
                "mask_value": False,
                "tier": "feature_specific",
            },
        }
        if mode == "full":
            common_creds.update(gcp_specific)

    return common_creds


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
    prompt: str,
    current_value: Optional[str] = None,
    mask_value: bool = True,
    default_value: Optional[str] = None,
) -> str:
    """Get credential input from user, showing current value if it exists."""
    display_value = current_value or default_value

    if display_value:
        # Show the current value (masked or unmasked based on mask_value)
        displayed_current = mask_credential(display_value, mask_value)
        value_type = "Current value" if current_value else "Default"
        display_prompt = (
            f"{prompt}\n{value_type}: {displayed_current}\n"
            f"Press Enter to keep {value_type.lower()}, or enter new value: "
        )
    else:
        display_prompt = prompt

    # Use regular input for all inputs
    new_value = input(display_prompt)

    # If user pressed Enter and there's a current/default value, keep it
    if not new_value and display_value:
        return current_value or default_value or ""

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
    platform: str, existing_creds: dict[str, str], mode: str = "full"
) -> dict[str, str]:
    """Get credentials for the specified platform and mode."""
    print(f"Setting up {platform.upper()} credentials in {mode} mode...")

    credentials = {}
    creds_config = get_credential_config(platform, mode)

    # Group credentials by tier for better UX
    essential_creds = {
        k: v for k, v in creds_config.items() if v.get("tier") == "essential"
    }
    conditional_creds = {
        k: v
        for k, v in creds_config.items()
        if v.get("tier") == "essential_conditional"
    }
    feature_creds = {
        k: v for k, v in creds_config.items() if v.get("tier") == "feature_specific"
    }
    optional_creds = {
        k: v for k, v in creds_config.items() if v.get("tier") == "optional"
    }

    # Process essential credentials first
    if essential_creds:
        print("\n📋 Essential credentials for basic functionality:")
        for key, config in essential_creds.items():
            credentials[key] = get_credential_input(
                config["prompt"],
                existing_creds.get(key),
                config["mask_value"],
                config.get("default"),
            )

    # Handle LLM provider credentials with validation
    if conditional_creds and mode in ["full", "minimal"]:
        print("\n🔑 LLM Provider credentials (at least one required):")
        provider = credentials.get("PROVIDER", "").lower()

        for key, config in conditional_creds.items():
            if (
                (provider == "anthropic" and "ANTHROPIC" in key)
                or (provider == "gemini" and "GEMINI" in key)
                or provider in ["mock", ""]
            ):
                credentials[key] = get_credential_input(
                    config["prompt"],
                    existing_creds.get(key),
                    config["mask_value"],
                    config.get("default"),
                )

    # Process feature-specific credentials
    if feature_creds and mode == "full":
        print("\n🔧 Feature-specific credentials (optional - skip if not needed):")
        for key, config in feature_creds.items():
            credentials[key] = get_credential_input(
                config["prompt"],
                existing_creds.get(key),
                config["mask_value"],
                config.get("default"),
            )

    # Process optional credentials
    if optional_creds and mode == "full":
        print("\n⚙️  Additional configuration (optional - defaults will be used):")
        for key, config in optional_creds.items():
            credentials[key] = get_credential_input(
                config["prompt"],
                existing_creds.get(key),
                config["mask_value"],
                config.get("default"),
            )

    # Handle special cases for comma-separated values (only in full mode)
    if mode == "full":
        credentials["SERVICES"] = handle_comma_separated_input(
            "SERVICES",
            "Enter the services running on the cluster (comma-separated)",
            existing_creds,
        )

        credentials["TOOLS"] = handle_comma_separated_input(
            "TOOLS",
            "Enter the tools you want to utilise (comma-separated)",
            existing_creds,
        )
    else:
        # Use defaults for testing/minimal modes
        credentials["SERVICES"] = existing_creds.get(
            "SERVICES", '["cartservice", "adservice", "emailservice"]'
        )
        credentials["TOOLS"] = existing_creds.get(
            "TOOLS",
            '["list_pods", "get_logs", "get_file_contents", "slack_post_message"]',
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
    parser.add_argument(
        "--mode",
        choices=["minimal", "testing", "full"],
        help="Setup mode: minimal (essential only), testing (mock setup), "
        "full (all features)",
        default="full",
    )

    args = parser.parse_args()

    print("=== SRE Agent Credential Setup ===")
    print("This script will help you set up credentials for running the agent locally.")

    # Explain modes if not specified
    if not args.mode or args.mode == "full":
        print("\n🎯 Setup Modes:")
        print("  • minimal  - Essential credentials only (for basic testing)")
        print("  • testing  - Mock setup (no real API keys needed)")
        print("  • full     - Complete setup (all features)")

        mode_choice = (
            input("\nChoose setup mode (minimal/testing/full) [full]: ").strip().lower()
        )
        mode = mode_choice if mode_choice in ["minimal", "testing", "full"] else "full"
    else:
        mode = args.mode

    print(f"\n🔧 Setup mode: {mode.upper()}")

    if mode == "testing":
        print("   Using mock provider - no real API keys required!")
    elif mode == "minimal":
        print("   Only essential credentials - basic functionality only")
    else:
        print("   Complete setup - all features will be available")

    # Read existing credentials
    existing_creds = read_env_file()

    # For testing mode, we can skip platform selection
    platform = args.platform
    if mode != "testing":
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
    else:
        # For testing mode, default to aws if not specified
        platform = platform or "aws"

    print(f"\nYou selected: {platform.upper()}")

    # Show existing credentials if any
    if existing_creds:
        creds_config = get_credential_config(platform, mode)
        display_current_credentials(existing_creds, creds_config)

    # Get credentials based on platform and mode
    credentials = get_platform_credentials(platform, existing_creds, mode)

    # Create .env file
    create_env_file(credentials)

    print("\n✅ Credentials saved to .env file!")
    print("\n🚀 Next steps:")

    if mode == "testing":
        print("   Start the test containers with:")
        print("   docker compose -f compose.tests.yaml up")
    else:
        print("   Start the containers with:")
        if platform == "aws":
            print("   docker compose -f compose.aws.yaml up")
        elif platform == "gcp":
            print("   docker compose -f compose.gcp.yaml up")

    print(
        f"\n💡 Tip: You can run 'python setup_credentials.py --mode {mode}' "
        f"again to use the same mode"
    )


if __name__ == "__main__":
    main()
