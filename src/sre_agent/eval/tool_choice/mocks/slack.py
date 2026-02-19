"""Mock Slack tools for tool choice evaluation."""

from typing import Any

import opik

MOCK_THREAD_TS = "1700000000.1000"


async def conversations_add_message(
    channel_id: str,
    payload: str,
    thread_ts: str | None,
) -> dict[str, Any]:
    """Mock Slack conversations_add_message."""
    span_input: dict[str, Any] = {"channel_id": channel_id, "payload": payload}
    if thread_ts is not None:
        span_input["thread_ts"] = thread_ts

    with opik.start_as_current_span(
        name="conversations_add_message",
        type="tool",
        input=span_input,
        metadata={"mocked": True, "provider": "slack"},
    ):
        if thread_ts is None:
            return {"ok": True, "channel": channel_id, "ts": MOCK_THREAD_TS}

        return {"ok": True, "channel": channel_id, "ts": thread_ts}
