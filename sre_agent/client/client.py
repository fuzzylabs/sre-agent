"""An MCTP SSE Client for interacting with a server using the MCP protocol."""

import time
from asyncio import TimeoutError, wait_for
from contextlib import AsyncExitStack
from functools import lru_cache
from typing import Any, cast

from anthropic import Anthropic
from anthropic.types.message_param import MessageParam
from anthropic.types.text_block_param import TextBlockParam
from anthropic.types.tool_param import ToolParam
from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.shared.exceptions import McpError
from mcp.types import TextContent

from .utils.auth import is_request_valid
from .utils.logger import logger
from .utils.schemas import ClientConfig, MCPServer, ServerSession

load_dotenv()  # load environment variables from .env

PORT = 3001


@lru_cache
def _get_client_config() -> ClientConfig:
    return ClientConfig()


class MCPClient:
    """An MCP client for connecting to a server using SSE transport."""

    def __init__(self) -> None:
        """Initialise the MCP client and set up the Anthropic API client."""
        self.anthropic = Anthropic()
        self.sessions: dict[MCPServer, ServerSession] = {}

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

    async def connect_to_sse_server(self, service: MCPServer) -> None:
        """Connect to an MCP server running with SSE transport."""
        server_url = f"http://{service}:{PORT}/sse"
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

        self.sessions[service] = ServerSession(tools=tools, session=session)

    def _convert_tool_result_to_text_blocks(
        self, result: str | list[TextContent]
    ) -> list[TextBlockParam]:
        """Convert a tool result to a list of text blocks.

        Args:
            result: The result to convert to a list of text blocks.

        Returns:
            The list of text blocks.
        """
        blocks = []
        if isinstance(result, str):
            blocks = [TextBlockParam(text=result, type="text")]
        elif isinstance(result, list):
            for content in result:
                if isinstance(content, TextContent):
                    blocks.append(TextBlockParam(text=content.text, type="text"))
                else:
                    raise ValueError(f"Unsupported tool result type: {type(content)}")

        # Add cache control to the blocks
        blocks[-1]["cache_control"] = {"type": "ephemeral"}

        return blocks

    def _remove_cache_control(self, messages: list[MessageParam]) -> list[MessageParam]:
        """Remove the cache control from the messages.

        Args:
            messages: The list of messages to remove the cache control from.

        Returns:
            The list of messages with the cache control removed.
        """
        for message in messages[::-1]:
            if isinstance(message["content"], str):
                continue
            for block in list(message["content"])[::-1]:
                if isinstance(block, dict) and "cache_control" in block:
                    # We assume there is only one cache control block
                    del block["cache_control"]  # type: ignore
                    return messages
        return messages

    async def _get_prompt(self, service: str, channel_id: str) -> str:
        """A helper method for retrieving the prompt from the prompt server."""
        prompt = await self.sessions[MCPServer.PROMPT].session.get_prompt(
            "diagnose", arguments={"service": service, "channel_id": channel_id}
        )

        if isinstance(prompt.messages[0].content, TextContent):
            return prompt.messages[0].content.text
        else:
            raise TypeError(
                f"{type(prompt.messages[0].content)} is invalid for this agent."
            )

    async def process_query(  # noqa: C901, PLR0912, PLR0915
        self, service: str, channel_id: str
    ) -> dict[str, Any]:
        """Process a query using Claude and available tools."""
        query = await self._get_prompt(service, channel_id)
        logger.info(f"Processing query: {query}...")
        start_time = time.perf_counter()

        messages = [
            MessageParam(
                role="user",
                content=[
                    TextBlockParam(
                        text=query, type="text", cache_control={"type": "ephemeral"}
                    )
                ],
            ),
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

        # Enable tool caching
        available_tools[-1]["cache_control"] = {"type": "ephemeral"}

        final_text = []
        stop_reason = None

        # Track token usage
        total_input_tokens = 0
        total_output_tokens = 0
        total_cache_creation_tokens = 0
        total_cache_read_tokens = 0

        tool_retries = 0

        while (
            stop_reason != "end_turn"
            and tool_retries < _get_client_config().max_tool_retries
        ):
            logger.info("Sending request to Claude")
            claude_start_time = time.perf_counter()
            response = self.anthropic.messages.create(
                model=_get_client_config().model,
                max_tokens=_get_client_config().max_tokens,
                messages=messages,
                tools=available_tools,
            )
            claude_duration = time.perf_counter() - claude_start_time
            logger.info(f"Claude request took {claude_duration:.2f} seconds")
            stop_reason = response.stop_reason

            # Track token usage from this response
            if hasattr(response, "usage"):
                total_input_tokens += response.usage.input_tokens
                total_output_tokens += response.usage.output_tokens
                if response.usage.cache_creation_input_tokens:
                    total_cache_creation_tokens += (
                        response.usage.cache_creation_input_tokens
                    )
                if response.usage.cache_read_input_tokens:
                    total_cache_read_tokens += response.usage.cache_read_input_tokens
                logger.info(
                    f"Token usage - Input: {response.usage.input_tokens}, "
                    f"Output: {response.usage.output_tokens}, "
                    f"Cache Creation: {response.usage.cache_creation_input_tokens}, "
                    f"Cache Read: {response.usage.cache_read_input_tokens}"
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
                                tool_start_time = time.perf_counter()
                                result = await session.session.call_tool(
                                    tool_name, cast(dict[str, str], tool_args)
                                )
                                tool_duration = time.perf_counter() - tool_start_time
                                logger.info(
                                    f"Tool {tool_name} call took "
                                    f"{tool_duration:.2f} seconds"
                                )

                                result_content = cast(str, result.content)
                                logger.debug(result_content)
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

                    messages = self._remove_cache_control(messages)

                    if hasattr(content, "text") and content.text:
                        messages.append(
                            MessageParam(
                                role="assistant",
                                content=[
                                    TextBlockParam(text=content.text, type="text")
                                ],
                            ),
                        )
                    messages.append(
                        MessageParam(
                            role="user",
                            content=self._convert_tool_result_to_text_blocks(
                                result_content
                            ),
                        )
                    )
        total_duration = time.perf_counter() - start_time
        logger.info(f"Total process_query execution took {total_duration:.2f} seconds")

        logger.info("Query processing completed")
        return {
            "response": "\n".join(final_text),
            "token_usage": {
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "cache_creation_tokens": total_cache_creation_tokens,
                "cache_read_tokens": total_cache_read_tokens,
                "total_tokens": total_input_tokens + total_output_tokens,
            },
            "timing": {
                "total_duration": total_duration,
            },
        }


app: FastAPI = FastAPI(
    description="A REST API for the SRE Agent orchestration service."
)


# Background task to run the diagnosis and post back to Slack
async def run_diagnosis_and_post(service: str) -> None:
    """Run diagnosis for a service and post results back to Slack.

    Args:
        service: The name of the service to diagnose.
    """
    timeout = _get_client_config().query_timeout
    try:

        async def _run_diagnosis() -> dict[str, Any]:
            async with MCPClient() as client:
                for server in MCPServer:
                    await client.connect_to_sse_server(service=server)

                result = await client.process_query(
                    service=service, channel_id=_get_client_config().channel_id
                )

                logger.info(
                    f"Token usage - Input: {result['token_usage']['input_tokens']}, "
                    f"Output: {result['token_usage']['output_tokens']}, "
                    f"Cache Creation:"
                    f" {result['token_usage']['cache_creation_tokens']}, "
                    f"Cache Read: {result['token_usage']['cache_read_tokens']}, "
                    f"Total: {result['token_usage']['total_tokens']}"
                )
            logger.info("Query processed successfully")
            logger.info(f"Diagnosis result for {service}: {result['response']}")
            return result

        # Run the diagnosis with a timeout
        await wait_for(_run_diagnosis(), timeout=timeout)

    except TimeoutError:
        logger.error(
            f"Diagnosis duration exceeded maximum timeout of {timeout} seconds"
        )
    except Exception as e:
        logger.error(f"Error during background diagnosis: {e}")


@app.post("/diagnose")
async def diagnose(
    request: Request,
    background_tasks: BackgroundTasks,
    authorisation: None = Depends(is_request_valid),
) -> JSONResponse:
    """Handle incoming Slack slash command requests for service diagnosis.

    Args:
        request: The FastAPI request object containing form data.
        background_tasks: FastAPI background tasks handler.
        authorisation: Authorization check result from is_request_valid dependency.

    Returns:
        JSONResponse: indicating the diagnosis has started.
    """
    form_data = await request.form()
    text_data = form_data.get("text", "")
    text = text_data.strip() if isinstance(text_data, str) else ""
    service = text or "cartservice"

    logger.info(f"Received diagnose request for service: {service}")

    # Run diagnosis in the background
    background_tasks.add_task(run_diagnosis_and_post, service)

    return JSONResponse(
        {
            "response_type": "ephemeral",
            "text": f"🔍 Running diagnosis for `{service}`...",
        }
    )
