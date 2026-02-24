"""Configuration constants for diagnosis quality evaluation."""

DEFAULT_EXPERIMENT_NAME = "sre-agent-diagnosis-quality"
DEFAULT_OPIK_PROJECT_NAME = "sre-agent-eval"
DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
DEFAULT_JUDGE_MODEL = DEFAULT_MODEL
DEFAULT_TIME_RANGE_MINUTES = 10  # Needed for the diagnosis prompt.
DEFAULT_SLACK_CHANNEL_ID = "MOCK_CHANNEL_ID"  # Needed for the diagnosis prompt.
