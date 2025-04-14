"""An MCTP SSE Client for interacting with a server using the MCP protocol."""

import os
from collections import defaultdict
from contextlib import AsyncExitStack
from typing import Any, Optional

from anthropic import Anthropic
from anthropic.types.message_param import MessageParam
from anthropic.types.tool_param import ToolParam
from dotenv import load_dotenv
from fastapi import FastAPI
from mcp import ClientSession
from mcp.client.sse import sse_client

from .utils.logger import logger

load_dotenv()  # load environment variables from .env


CHANNEL_ID = os.getenv("CHANNEL_ID")

if CHANNEL_ID is None:
    logger.error("Environment variable CHANNEL_ID is not set.")
    raise ValueError("Environment variable CHANNEL_ID is not set.")

# Break long string into multiple lines for better readability
PROMPT = (
    f"Can you list pull requests for the microservices-demo repository in the "
    f"fuzzylabs organisation and then post a message in the slack channel {CHANNEL_ID} "
    "with the list of pull requests? Once this is done you can end the conversation."
)


class MCPClient:
    """An MCP client for connecting to a server using SSE transport."""

    def __init__(self) -> None:
        """Initialize the MCP client and set up the Anthropic API client."""
        logger.info("Initialising MCP client")
        self.anthropic = Anthropic()
        self.sessions: dict[str, dict[str, Any]] = defaultdict(dict)

    async def __aenter__(self) -> "MCPClient":
        """Set up AsyncExitStack when entering the context manager."""
        logger.debug("Entering MCP client context")
        self.exit_stack = AsyncExitStack()
        await self.exit_stack.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[Exception],
        exc_tb: Optional[Any],
    ) -> None:
        """Clean up resources when exiting the context manager."""
        logger.debug("Exiting MCP client context")
        await self.exit_stack.__aexit__(exc_type, exc_val, exc_tb)

    async def connect_to_sse_server(self, server_url: str) -> None:
        """Connect to an MCP server running with SSE transport."""
        logger.info(f"Connecting to SSE server: {server_url}")
        # Create and enter the SSE client context
        stream_ctx = sse_client(url=server_url)
        streams = await self.exit_stack.enter_async_context(stream_ctx)

        # Create and enter the ClientSession context
        session = ClientSession(*streams)
        session = await self.exit_stack.enter_async_context(session)

        # Initialise the session
        await session.initialize()

        # List available tools to verify connection
        logger.info(f"Initialised SSE client for {server_url}")
        logger.debug("Listing available tools")
        response = await session.list_tools()
        tools = response.tools
        logger.info(
            f"Connected to {server_url} with tools: {[tool.name for tool in tools]}"
        )

        self.sessions[server_url] = {"session": session, "tools": tools}

    async def process_query(self, query: str) -> dict[str, Any]:
        """Process a query using Claude and available tools."""
        logger.info(f"Processing query: {query[:50]}...")
        messages = [
            MessageParam(role="user", content=query),
        ]

        available_tools = []

        for service, session in self.sessions.items():
            available_tools.extend(
                [
                    ToolParam(
                        name=tool.name,
                        description=tool.description if tool.description else "",
                        input_schema=tool.inputSchema,
                    )
                    for tool in session["tools"]
                ]
            )

        tool_results = []
        final_text = []
        stop_reason = None

        # Track token usage
        total_input_tokens = 0
        total_output_tokens = 0

        while stop_reason != "end_turn":
            logger.info("Sending request to Claude")
            response = self.anthropic.messages.create(
                model="claude-3-5-sonnet-latest",
                max_tokens=1000,
                messages=messages,
                tools=available_tools,
            )
            stop_reason = response.stop_reason

            # Track token usage from this response
            if hasattr(response, "usage"):
                total_input_tokens += response.usage.input_tokens
                total_output_tokens += response.usage.output_tokens
                print(
                    f"Token usage - Input: {response.usage.input_tokens}, "
                    f"Output: {response.usage.output_tokens}"
                )

            for content in response.content:
                if content.type == "text":
                    final_text.append(content.text)
                    logger.debug(f"Claude response: {content.text}")
                elif content.type == "tool_use":
                    tool_name = content.name
                    tool_args: dict[str, Any] = content.input
                    logger.info(f"Claude requested to use tool: {tool_name}")

                    for service, session in self.sessions.items():
                        if tool_name in [tool.name for tool in session["tools"]]:
                            logger.debug(
                                f"Calling tool {tool_name} with args: {tool_args}"
                            )
                            result = await session["session"].call_tool(
                                tool_name, tool_args
                            )
                            break
                    else:
                        logger.error(f"Tool {tool_name} not found in available tools")
                        raise ValueError(
                            f"Tool {tool_name} not found in available tools."
                        )

                    tool_results.append({"call": tool_name, "result": result})
                    final_text.append(
                        f"[Calling tool {tool_name} with args {tool_args}]"
                    )

                    if hasattr(content, "text") and content.text:
                        messages.append(
                            MessageParam(role="assistant", content=content.text),
                        )
                    messages.append(MessageParam(role="user", content=result.content))

        logger.info("Query processing completed")
        return {
            "response": "\n".join(final_text),
            "token_usage": {
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "total_tokens": total_input_tokens + total_output_tokens,
            },
        }


app = FastAPI()


@app.get("/diagnose")
async def diagnose() -> dict[str, Any]:
    """Handle the diagnose endpoint request."""
    logger.info("Received diagnose request")
    async with MCPClient() as client:
        logger.info("Connecting to services")
        await client.connect_to_sse_server(server_url="http://slack:3001/sse")
        await client.connect_to_sse_server(server_url="http://github:3001/sse")
        await client.connect_to_sse_server(server_url="http://kubernetes:3001/sse")
        logger.info("Processing query")
        result = await client.process_query(PROMPT)
        logger.info(
            f"Token usage - Input: {result['token_usage']['input_tokens']}, "
            f"Output: {result['token_usage']['output_tokens']}, "
            f"Total: {result['token_usage']['total_tokens']}"
        )
        logger.info("Query processed successfully")
        return result
