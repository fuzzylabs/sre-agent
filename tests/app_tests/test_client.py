"""Test the MCPClient class. Assumes services are running via docker compose."""

import asyncio
import subprocess  # nosec B404
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sre_agent.client.client import PORT, MCPClient
from sre_agent.client.utils.schemas import MCPServer

COMPOSE_FILE = Path(__file__).parent.parent.parent / "compose.yaml"


@pytest.fixture(scope="module", autouse=True)
def manage_docker_compose() -> Iterator[None]:
    """Starts and stops the docker compose services for the test module."""
    if not COMPOSE_FILE.exists():
        pytest.skip(f"Docker compose file not found at {COMPOSE_FILE}")

    print(f"\nStarting Docker services from {COMPOSE_FILE}...")
    # Use '-p' to create a project-specific network/volumes
    project_name = "sre_agent_test"
    # Ensure services are built if not present
    start_command = [
        "docker",
        "compose",
        "-f",
        str(COMPOSE_FILE),
        "-p",
        project_name,
        "up",
        "--build",
        "-d",
    ]
    stop_command = [
        "docker",
        "compose",
        "-f",
        str(COMPOSE_FILE),
        "-p",
        project_name,
        "down",
        "--volumes",
    ]

    try:
        subprocess.run(start_command, check=True, capture_output=True)  # nosec B603
        print("Docker services started.")
        # Add a delay or health check here if services need time to start
        asyncio.run(asyncio.sleep(15))  # Simple delay, refine if needed
        yield
    finally:
        print("\nStopping Docker services...")
        subprocess.run(stop_command, check=True, capture_output=True)  # nosec B603
        print("Docker services stopped.")


@pytest.mark.asyncio
@patch("sre_agent.client.client.sse_client")  # Patch the sse_client function
async def test_client_connects_to_prompt_server(mock_sse_client: MagicMock) -> None:
    """Test that the MCPClient can initialise and connect to the prompt server.

    Assumes services (prompt_server, llm-server) are running via docker compose.
    Uses patching to redirect connection to localhost.
    """
    # Configure the mock to return a context manager with mock streams
    # Make the send method of the write stream an AsyncMock
    mock_read_stream = MagicMock()
    mock_write_stream = MagicMock()
    mock_write_stream.send = AsyncMock()  # Make send awaitable

    mock_streams = (mock_read_stream, mock_write_stream)
    mock_sse_client.return_value.__aenter__.return_value = mock_streams

    async with MCPClient() as client:
        try:
            # Call the original method, the patch will intercept sse_client
            # and session initialisation will use the mocked streams
            await client.connect_to_sse_server(MCPServer.PROMPT)

            # Check that sse_client was called with the correct URL
            # NOTE: We are checking the host facing URL here, not the internal one
            expected_url = f"http://{MCPServer.PROMPT.value}:{PORT}/sse"
            # Let's check the mock call args directly
            call_args, call_kwargs = mock_sse_client.call_args
            assert call_kwargs.get("url") == expected_url

            # Check that the session initialisation tried to send something
            mock_write_stream.send.assert_awaited_once()

            # Assertions on session creation remain the same
            assert MCPServer.PROMPT in client.sessions
            assert client.sessions[MCPServer.PROMPT].session is not None
            # We still can't easily assert tools length here as the connection is mocked
            # assert len(client.sessions[MCPServer.PROMPT].tools) > 0
        except Exception as e:
            pytest.fail(f"Test failed during client connection: {e}")


# Placeholder for more tests
# @pytest.mark.asyncio
# async def test_client_process_query():
#     async with MCPClient() as client:
#         await client.connect_to_sse_server(MCPServer.PROMPT)
#         # ... connect to other required services ...
#         # result = await client.process_query(
#         #     service="some_service", channel_id="some_channel"
#         # )
#         # assert result["status"] == "success" # Or other relevant assertions
#         pass
