# DEVELOPER README

This document is for developers of sre-agent, specifically for v0.2.0.

## To start the agent

Create a `.env` file:
```bash
cp .env.example .env
```

Add your AWS credentials and Anthropic API key.

Start the agent server and the Slack MCP server:
```bash
docker compose up -d
```

Trigger an error on the [store](http://aea33d77009704f67b39fe82a5c41aab-398063840.eu-west-2.elb.amazonaws.com/) by adding loaf to the cart, or change the currency from EUR to GBP. (Note, there is an bug that errors might take some time to be indexed so if you trigger the agent immediately after you cause an error it might not be able to find the log.)

Trigger the locally running agent:
```bash
uv run python run.py /aws/containerinsights/no-loafers-for-you/application cartservice
```

Or:
```bash
uv run python run.py /aws/containerinsights/no-loafers-for-you/application currencyservice
```

## Adding a New Tool

When adding a new tool/integration, follow one of these patterns:

### Option 1: MCP Server

If an MCP server exists for the service, you can use that. No interface implementation is needed.

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

Use this when no MCP server is available. You must implement the relevant interface.

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
