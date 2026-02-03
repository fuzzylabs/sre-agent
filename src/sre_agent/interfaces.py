"""Abstract interfaces for direct API implementations.

These interfaces define contracts for tools that use direct API calls
(not MCP servers). If using an MCP server, no interface is needed.

Currently used by:
- CloudWatch (LoggingInterface)

Not needed for MCP-based tools:
- GitHub (MCP server)
- Slack (MCP server)
"""

from abc import ABC, abstractmethod

from sre_agent.models import LogQueryResult


class LoggingInterface(ABC):
    """Interface for logging platforms (CloudWatch, Cloud Monitoring, Azure Monitor, etc.)."""

    @abstractmethod
    async def query_errors(
        self,
        source: str,
        time_range_minutes: int = 10,
        service_name: str | None = None,
    ) -> LogQueryResult:
        """Query error logs from the platform."""
        raise NotImplementedError


class RepositoryInterface(ABC):
    """Interface for code repositories (GitLab, Bitbucket, etc.).

    Note: GitHub uses MCP server, so this interface is for other providers.
    """

    @abstractmethod
    async def get_file(self, repo: str, path: str, ref: str | None = None) -> str:
        """Get file content from the repository."""
        raise NotImplementedError


class MessagingInterface(ABC):
    """Interface for messaging platforms (Discord, Teams, PagerDuty, etc.).

    Note: Slack uses MCP server, so this interface is for other providers.
    """

    @abstractmethod
    async def send_message(self, channel: str, message: str) -> None:
        """Send a message to a channel."""
        raise NotImplementedError
