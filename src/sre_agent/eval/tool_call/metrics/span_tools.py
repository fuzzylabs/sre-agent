"""Helpers for extracting tool-call spans in tool call evaluation."""

from opik.message_processing.emulation.models import SpanModel


def extract_tool_names(task_span: SpanModel) -> list[str]:
    """Extract ordered tool names from a task span tree.

    Args:
        task_span: The task span tree.

    Returns:
        The ordered names of the tools used in the task.
    """
    tool_names: list[str] = []
    _collect_tool_names(task_span.spans, tool_names)
    return tool_names


def _collect_tool_names(spans: list[SpanModel], tool_names: list[str]) -> None:
    """Collect tool names from nested spans.

    Args:
        spans: The spans to inspect.
        tool_names: The list used to store tool names.
    """
    for span in spans:
        if span.type == "tool" and span.name:
            name = span.name.strip()
            if name:
                tool_names.append(name)

        if span.spans:
            _collect_tool_names(span.spans, tool_names)
