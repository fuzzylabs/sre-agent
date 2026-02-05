"""Data models for the SRE Agent."""

from datetime import datetime

from pydantic import BaseModel, Field


class LogEntry(BaseModel):
    """A single log entry from CloudWatch."""

    timestamp: str = Field(description="ISO 8601 timestamp of the log entry")
    message: str = Field(description="The log message content")
    log_stream: str | None = Field(default=None, description="The log stream name")


class LogQueryResult(BaseModel):
    """Result from querying CloudWatch logs."""

    entries: list[LogEntry] = Field(default_factory=list, description="Log entries found")
    log_group: str = Field(description="The log group queried")
    query: str = Field(description="The query that was executed")


class SuggestedFix(BaseModel):
    """A suggested fix for an error."""

    description: str = Field(description="What the fix involves")
    file_path: str | None = Field(default=None, description="File to modify, if applicable")
    code_snippet: str | None = Field(default=None, description="Example code change")


class ErrorDiagnosis(BaseModel):
    """Complete diagnosis of an error from the SRE agent."""

    summary: str = Field(description="Brief summary of the issue")
    root_cause: str = Field(description="Identified root cause")
    affected_services: list[str] = Field(
        default_factory=list,
        description="Services affected by this issue",
    )
    suggested_fixes: list[SuggestedFix] = Field(
        default_factory=list,
        description="Suggested fixes for the issue",
    )
    related_logs: list[str] = Field(
        default_factory=list,
        description="Key log messages related to the issue",
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When the diagnosis was created",
    )
