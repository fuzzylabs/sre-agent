"""An MCTP SSE Client for interacting with a server using the MCP protocol."""

from contextlib import AsyncExitStack
from functools import lru_cache
from typing import Any, cast

from anthropic import Anthropic
from anthropic.types.message_param import MessageParam
from anthropic.types.tool_param import ToolParam
from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.shared.exceptions import McpError

from .utils.auth import is_request_valid
from .utils.logger import logger
from .utils.schemas import ClientConfig, MCPServer, ServerSession

load_dotenv()  # load environment variables from .env


@lru_cache
def _get_client_config() -> ClientConfig:
    return ClientConfig()


PROMPT = """I have an error with my application, can you check the logs for the
{service} service, I only want you to check the pods logs, look up only the 100 most
recent logs. Feel free to scroll up until you find relevant errors that contain
reference to a file, once you have these errors and the file name, get the file
contents of the path src for the repository microservices-demo in the organisation
fuzzylabs. Keep listing the directories until you find the file name and then get the
contents of the file. Once you have diagnosed the error please report this to the
following slack channel: {channel_id}."""


class MCPClient:
    """An MCP client for connecting to a server using SSE transport."""

    def __init__(self) -> None:
        """Initialise the MCP client and set up the Anthropic API client."""
        self.anthropic = Anthropic()
        self.sessions: dict[str, ServerSession] = {}

    async def __aenter__(self) -> "MCPClient":
        """Set up AsyncExitStack when entering the context manager."""
        logger.debug("Entering MCP client context")
        self.exit_stack = AsyncExitStack()
        await self.exit_stack.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type | None,
        exc_val: Exception | None,
        exc_tb: Any | None,
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

        self.sessions[server_url] = ServerSession(tools=tools, session=session)

    async def process_query(self, query: str) -> dict[str, Any]:  # noqa: C901, PLR0912
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
                    for tool in session.tools
                    if tool.name in _get_client_config().tools
                ]
            )

        final_text = []
        stop_reason = None

        # Track token usage
        total_input_tokens = 0
        total_output_tokens = 0

        tool_retries = 0

        while (
            stop_reason != "end_turn"
            and tool_retries < _get_client_config().max_tool_retries
        ):
            logger.info("Sending request to Claude")
            response = self.anthropic.messages.create(
                model=_get_client_config().model,
                max_tokens=_get_client_config().max_tokens,
                messages=messages,
                tools=available_tools,
            )
            stop_reason = response.stop_reason

            # Track token usage from this response
            if hasattr(response, "usage"):
                total_input_tokens += response.usage.input_tokens
                total_output_tokens += response.usage.output_tokens
                logger.info(
                    f"Token usage - Input: {response.usage.input_tokens}, "
                    f"Output: {response.usage.output_tokens}"
                )

            for content in response.content:
                if content.type == "text":
                    final_text.append(content.text)
                    logger.debug(f"Claude response: {content.text}")
                elif content.type == "tool_use":
                    tool_name = content.name
                    tool_args = content.input
                    logger.info(f"Claude requested to use tool: {tool_name}")

                    for service, session in self.sessions.items():
                        if tool_name in [tool.name for tool in session.tools]:
                            logger.info(
                                f"Calling tool {tool_name} with args: {tool_args}"
                            )
                            try:
                                result = await session.session.call_tool(
                                    tool_name, cast(dict[str, str], tool_args)
                                )
                                result_content = cast(str, result.content)
                                tool_retries = 0

                                # This is a special case. We want to exit immediately
                                # after the slack message is sent.
                                if tool_name == "slack_post_message":
                                    logger.info("Slack message sent, exiting")
                                    stop_reason = "end_turn"
                            except McpError as e:
                                error_msg = f"Tool '{tool_name}' failed with error: {str(e)}. Tool args were: {tool_args}. Check the arguments and try again fixing the error."  # noqa: E501
                                logger.info(error_msg)
                                result_content = error_msg
                                tool_retries += 1
                            break
                    else:
                        logger.error(f"Tool {tool_name} not found in available tools")
                        raise ValueError(
                            f"Tool {tool_name} not found in available tools."
                        )

                    final_text.append(
                        f"[Calling tool {tool_name} with args {tool_args}]"
                    )

                    if hasattr(content, "text") and content.text:
                        messages.append(
                            MessageParam(role="assistant", content=content.text),
                        )
                    messages.append(MessageParam(role="user", content=result_content))

        logger.info("Query processing completed")
        return {
            "response": "\n".join(final_text),
            "token_usage": {
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "total_tokens": total_input_tokens + total_output_tokens,
            },
        }


app: FastAPI = FastAPI(
    description="A REST API for the SRE Agent orchestration service."
)


@app.post("/diagnose")
async def diagnose(
    service: str = "cartservice",
    prompt: str = PROMPT,
    authorisation: None = Depends(is_request_valid),
) -> dict[str, Any]:
    """An endpoint for triggering agent diagnosis.

    Args:
        service: the name of the service to start checking the logs of.
        prompt: the prompt to trigger the agent.
        authorisation: a fastapi authorisation dependency to check for bearer tokens.

    Returns:
        A response containing the output from model and the number of tokens required
        to generate the response.
    """
    logger.info("Received diagnose request")
    async with MCPClient() as client:
        logger.info("Connecting to services")
        for server in MCPServer:
            await client.connect_to_sse_server(server_url=f"http://{server}:3001/sse")

        logger.info("Processing query")
        result = await client.process_query(
            prompt.format(service=service, channel_id=_get_client_config().channel_id)
        )
        logger.info(
            f"Token usage - Input: {result['token_usage']['input_tokens']}, "
            f"Output: {result['token_usage']['output_tokens']}, "
            f"Total: {result['token_usage']['total_tokens']}"
        )
        logger.info("Query processed successfully")
        return result
