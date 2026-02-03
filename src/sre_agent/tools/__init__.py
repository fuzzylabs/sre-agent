"""Tool modules for the SRE Agent.

## Adding a new tool

Follow one of these patterns:

1. **MCP Server**
   - Just return MCPServerStdio
   - No interface implementation needed
   - Example: github.py, slack.py

2. **Direct API**
   - Implement the relevant interface from interfaces.py
   - Create a FunctionToolset with agent-callable tools
   - Example: cloudwatch.py
"""

from sre_agent.tools.cloudwatch import CloudWatchLogging, create_cloudwatch_toolset
from sre_agent.tools.github import create_github_mcp_toolset
from sre_agent.tools.slack import create_slack_mcp_toolset

__all__ = [
    # Interface implementations (Direct API)
    "CloudWatchLogging",
    # Toolset factories
    "create_cloudwatch_toolset",
    "create_github_mcp_toolset",
    "create_slack_mcp_toolset",
]
