# DEVELOPER README

This document contains documentation intended for developers of sre-agent.

## Adding a New Tool

When adding a new tool/integration, follow one of these patterns:

### Option 1: MCP Server

If you decide to use an MCP server exists for the service. No interface implementation is  needed.

```python
# tools/example.py
from pydantic_ai.mcp import MCPServerStdio
from sre_agent.config import AgentConfig

def create_example_mcp_toolset(config: AgentConfig) -> MCPServerStdio:
    return MCPServerStdio(
        "docker",
        args=["run", "-i", "--rm", "-e", f"TOKEN={config.example.token}", "mcp/example"],
        timeout=30,
    )
```

**Examples:** `github.py`, `slack.py`

### Option 2: Direct API

Use this when no MCP server is available. Must implement the relevant interface.

```python
# tools/example.py
from sre_agent.interfaces import LoggingInterface
from sre_agent.models import LogQueryResult

class ExampleLogging(LoggingInterface):
    async def query_errors(self, source: str, time_range_minutes: int = 10) -> LogQueryResult:
        # Implementation using direct API calls
        ...

def create_example_toolset(config: AgentConfig) -> FunctionToolset:
    toolset = FunctionToolset()
    impl = ExampleLogging(config.example.api_key)

    @toolset.tool
    async def search_logs(...) -> LogQueryResult:
        return await impl.query_errors(...)

    return toolset
```

**Examples:** `cloudwatch.py`
