"""An MCP SSE Client for interacting with a server using the MCP protocol."""

import time
from asyncio import TimeoutError, wait_for
from contextlib import AsyncExitStack
from functools import lru_cache
from http import HTTPStatus
from typing import Annotated, Any, cast

import requests
from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.shared.exceptions import McpError
from mcp.types import GetPromptResult, TextContent
from shared.logger import logger  # type: ignore[import-not-found]
from shared.schemas import (  # type: ignore[import-not-found]
    Message,
    MessageBlock,
    TextBlock,
    TextGenerationPayload,
)
from utils.auth import is_request_valid  # type: ignore
from utils.schemas import ClientConfig, MCPServer, ServerSession  # type: ignore

load_dotenv()

PORT = 3001
END_TURN = "end_turn"


@lru_cache
def _get_client_config() -> ClientConfig:
    return ClientConfig()


class MCPClient:
    """An MCP client for connecting to a server using SSE transport."""

    def __init__(self) -> None:
        """Initialise the MCP client and set up the LLM API client."""
        self.sessions: dict[MCPServer, ServerSession] = {}
        self.messages: list[dict[str, Any]] = []
        self.stop_reason: str | None = None

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

    async def _run_firewall_check(self, text: str, is_tool: bool = False) -> bool:
        """Check text against the Llama Firewall and update messages if blocked.

        Args:
            text: The text to check.
            is_tool: Whether this is a tool-related check.

        Returns:
            True if the input is blocked, False otherwise.
        """
        logger.info("Running text through Llama Firewall")

        response = requests.post(
            "http://llama-firewall:8000/check",
            json={"content": text, "is_tool": is_tool},
            timeout=60,
        )

        response.raise_for_status()

        response = response.json()

        result, block = response["result"], cast(bool, response["block"])

        logger.info("Llama Firewall result: %s", "BLOCKED" if block else "ALLOWED")

        if block:
            self.messages.append({"role": "assistant", "content": result["reason"]})
            self.stop_reason = END_TURN
        return block

    async def connect_to_sse_server(self, service: MCPServer) -> None:
        """Connect to an MCP server running with SSE transport."""
        server_url = f"http://{service}:{PORT}/sse"
        logger.info(f"Connecting to SSE server: {server_url}")

        logger.info("Creating SSE client context")
        stream_ctx = sse_client(url=server_url)
        streams = await self.exit_stack.enter_async_context(stream_ctx)

        logger.info("Creating MCP client session")
        session = ClientSession(*streams)
        session = await self.exit_stack.enter_async_context(session)

        logger.info(f"Initialising session for {server_url}")
        await session.initialize()

        logger.info(f"Initialised SSE client for {server_url}")
        logger.debug("Listing available tools")
        response = await session.list_tools()
        tools = response.tools
        logger.info(
            f"Connected to {server_url} with tools: {[tool.name for tool in tools]}"
        )

        self.sessions[service] = ServerSession(tools=tools, session=session)

    async def _get_prompt(self, service: str, slack_channel_id: str) -> MessageBlock:
        """A helper method for retrieving the prompt from the prompt server."""
        prompt: GetPromptResult = await self.sessions[
            MCPServer.PROMPT
        ].session.get_prompt(
            "diagnose",
            arguments={"service": service, "slack_channel_id": slack_channel_id},
        )

        if isinstance(prompt.messages[0].content, TextContent):
            return MessageBlock(
                role=prompt.messages[0].role,
                content=[TextBlock(**prompt.messages[0].content.model_dump())],
            )
        else:
            raise TypeError(
                f"{type(prompt.messages[0].content)} is invalid for this agent."
            )

    async def process_query(  # noqa: C901, PLR0912, PLR0915
        self, service: str, slack_channel_id: str
    ) -> dict[str, Any]:
        """Process a query using Claude and available tools."""
        query = await self._get_prompt(service, slack_channel_id)
        logger.info(f"Processing query: {query}...")
        start_time = time.perf_counter()

        _ = await self._run_firewall_check(str(query.content[0].model_dump()))

        self.messages = [{"role": query.role, "content": query.content}]

        available_tools = []

        for service, session in self.sessions.items():
            available_tools.extend(
                [
                    tool.model_dump()
                    for tool in session.tools
                    if tool.name in _get_client_config().tools
                ]
            )

        final_text = []

        # Track token usage
        total_input_tokens = 0
        total_output_tokens = 0
        total_cache_creation_tokens = 0
        total_cache_read_tokens = 0

        tool_retries = 0

        while (
            self.stop_reason != END_TURN
            and tool_retries < _get_client_config().max_tool_retries
        ):
            logger.info("Sending request to the LLM")
            llm_start_time = time.perf_counter()

            payload = TextGenerationPayload(
                messages=self.messages, tools=available_tools
            ).model_dump(mode="json")

            logger.debug(payload)

            response = requests.post(
                "http://llm-server:8000/generate", json=payload, timeout=60
            )

            response.raise_for_status()

            llm_response = Message(**response.json())

            logger.debug(llm_response)

            llm_duration = time.perf_counter() - llm_start_time
            logger.info(f"LLM request took {llm_duration:.2f} seconds")
            self.stop_reason = llm_response.stop_reason

            # Track token usage from this response
            if llm_response.usage:
                total_input_tokens += llm_response.usage.input_tokens
                total_output_tokens += llm_response.usage.output_tokens
                if llm_response.usage.cache_creation_input_tokens:
                    total_cache_creation_tokens += (
                        llm_response.usage.cache_creation_input_tokens
                    )
                if llm_response.usage.cache_read_input_tokens:
                    total_cache_read_tokens += (
                        llm_response.usage.cache_read_input_tokens
                    )

            assistant_message_content = []

            for content in llm_response.content:
                if content.type == "text":
                    final_text.append(content.text)
                    logger.debug(f"LLM response: {content.text}")
                elif content.type == "tool_use":
                    tool_name = content.name
                    tool_args = content.arguments
                    logger.info(f"LLM requested to use tool: {tool_name}")

                    if await self._run_firewall_check(
                        f"Calling tool {tool_name} with args: {tool_args}", is_tool=True
                    ):
                        break

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
                                result_content = result.content
                                is_error = result.isError

                                if await self._run_firewall_check(
                                    str(result_content), is_tool=True
                                ):
                                    break

                                tool_retries = 0

                            except McpError as e:
                                error_msg = f"Tool '{tool_name}' failed with error: {str(e)}. Tool args were: {tool_args}. Check the arguments and try again fixing the error."  # noqa: E501
                                logger.info(error_msg)
                                result_content = [
                                    TextBlock(type="text", text=error_msg)
                                ]
                                is_error = True
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

                    assistant_message_content.append(content)
                    self.messages.append(
                        {"role": "assistant", "content": assistant_message_content}
                    )

                    self.messages.append(
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": content.id,
                                    "name": tool_name,
                                    "content": [i.model_dump() for i in result_content],
                                    "is_error": is_error,
                                }
                            ],
                        }
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


async def run_diagnosis_and_post(service: str) -> None:
    """Run diagnosis for a service and post results back to Slack.

    Args:
        service: The name of the service to diagnose.
    """
    timeout = _get_client_config().query_timeout
    try:
        async with MCPClient() as client:
            logger.info(f"Creating MCPClient for service: {service}")
            try:
                for server in MCPServer:
                    await client.connect_to_sse_server(service=server)

                if not all(server in client.sessions for server in MCPServer):
                    missing = [s.name for s in MCPServer if s not in client.sessions]
                    logger.error(
                        "MCP Client failed to establish required server sessions: "
                        f"{', '.join(missing)}"
                    )
                    # TODO: Post error back to Slack?
                    return

                logger.info("MCPClient connections established successfully.")

            except Exception as conn_err:
                logger.exception(f"Failed to connect MCPClient sessions: {conn_err}")
                # TODO: Post error back to Slack?
                return

            async def _run_diagnosis(mcp_client: MCPClient) -> dict[str, Any]:
                """Inner function to run the actual diagnosis query."""
                result = await mcp_client.process_query(
                    service=service,
                    slack_channel_id=_get_client_config().slack_channel_id,
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

            await wait_for(_run_diagnosis(client), timeout=timeout)

    except TimeoutError:
        logger.error(
            f"Diagnosis duration exceeded maximum timeout of {timeout} seconds for "
            f"service {service}"
        )
        # TODO: Post error back to Slack?
    except Exception as e:
        logger.exception(f"Error during background diagnosis for {service}: {e}")
        # TODO: Post error back to Slack?


@app.post("/diagnose")
async def diagnose(
    request: Request,
    background_tasks: BackgroundTasks,
    _authorisation: Annotated[None, Depends(is_request_valid)],
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

    if service not in _get_client_config().services:
        return JSONResponse(
            status_code=HTTPStatus.BAD_REQUEST,
            content={
                "text": f"Service `{service}` is not supported. Supported services are"
                f": {', '.join(_get_client_config().services)}.",
            },
        )

    logger.info(f"Received diagnose request for service: {service}")

    background_tasks.add_task(run_diagnosis_and_post, service)

    return JSONResponse(
        status_code=HTTPStatus.OK,
        content={
            "response_type": "ephemeral",
            "text": f"🔍 Running diagnosis for `{service}`...",
        },
    )


@app.get("/health")
async def health() -> JSONResponse:
    """Check if connections to all required MCP servers can be established."""
    failed_checks: list[str] = []
    healthy_connections: list[str] = []
    all_servers = list(MCPServer)

    logger.info("Performing health check by attempting temporary connections...")

    try:
        async with MCPClient() as client:
            for server in all_servers:
                server_name = server.name
                try:
                    logger.debug(
                        f"Health check: Attempting connection to {server_name}"
                    )
                    await client.connect_to_sse_server(service=server)
                    await client.sessions[server].session.list_tools()
                    logger.debug(
                        f"Health check connection successful for {server_name}"
                    )
                    healthy_connections.append(server_name)
                except Exception as e:
                    msg = (
                        f"Health check connection failed for {server_name}: "
                        f"{type(e).__name__} - {e}"
                    )
                    logger.error(msg)
                    failed_checks.append(msg)

    except Exception as client_err:
        msg = (
            "Health check failed: Could not initialise or manage MCPClient context: "
            f"{type(client_err).__name__} - {client_err}"
        )
        logger.error(msg)

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "Unavailable",
                "detail": msg,
                "errors": [msg],
            },
        )

    if failed_checks:
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        response_detail = {
            "status": "Partially Available" if healthy_connections else "Unavailable",
            "detail": "One or more MCP server connections failed health checks.",
            "healthy_connections": sorted(healthy_connections),
            "errors": failed_checks,
        }
        logger.warning(
            f"Health check completed with failures. Healthy: "
            f"{len(healthy_connections)}, "
            f"Failed: {len(failed_checks)}. Errors: {failed_checks}"
        )
    else:
        status_code = status.HTTP_200_OK
        response_detail = {
            "status": "OK",
            "detail": "All required MCP server connections are healthy.",
            "checked_servers": sorted([s.name for s in all_servers]),
        }
        logger.info(
            "Health check completed successfully. All connections healthy: "
            f"{sorted([s.name for s in all_servers])}"
        )

    return JSONResponse(content=response_detail, status_code=status_code)
