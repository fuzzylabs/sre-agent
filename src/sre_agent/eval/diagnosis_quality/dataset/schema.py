"""Pydantic evaluation case schema for diagnosis quality evaluation."""

from pydantic import BaseModel, ConfigDict


class MockCloudWatchEntry(BaseModel):
    """One mocked CloudWatch log entry."""

    model_config = ConfigDict(extra="forbid")

    message: list[
        str
    ]  # This is a list of strings because the log message can be multiline for readability.


class DiagnosisQualityEvalCase(BaseModel):
    """One diagnosis quality evaluation case."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    log_group: str
    service_name: str
    github_owner: str
    github_repo: str
    github_ref: str
    mock_cloudwatch_entries: list[MockCloudWatchEntry]
    expected_root_cause: str
    expected_fix_suggestion_mentions: list[str]
    expected_affected_services: list[str]
