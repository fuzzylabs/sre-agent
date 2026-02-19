"""Pydantic evaluation case schema for tool choice evaluation."""

from pydantic import BaseModel, ConfigDict, Field


class MockCloudWatchEntry(BaseModel):
    """One mocked CloudWatch log entry."""

    model_config = ConfigDict(extra="forbid")

    message: list[
        str
    ]  # This is a list of strings because the log message can be multiline for readability.


class ToolChoiceEvalCase(BaseModel):
    """One tool choice evaluation case."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    log_group: str
    service_name: str
    github_owner: str
    github_repo: str
    github_ref: str
    mock_cloudwatch_entries: list[MockCloudWatchEntry] = Field(default_factory=list)
    expected_first_tool: str
    expected_second_tool: str
    expected_last_tool: str
    possible_github_tools: list[str]
