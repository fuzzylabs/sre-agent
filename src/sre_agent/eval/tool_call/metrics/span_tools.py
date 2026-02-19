"""Helpers for extracting tool-call spans in tool call evaluation."""

from opik.message_processing.emulation.models import SpanModel


def extract_tool_names(task_span: SpanModel) -> list[str]:
    """Extract ordered tool names from a task span tree.

    Args:
        task_span: The task span tree.

    Returns:
        The ordered names of the tools used in the task.
    """
    names: list[str] = []
    for span in _iter_spans(task_span):
        if getattr(span, "type", None) != "tool":
            continue

        name = str(getattr(span, "name", "")).strip()
        if name:
            names.append(name)

    return names


def _iter_spans(span: SpanModel) -> list[SpanModel]:
    """Traverse span tree in depth-first order.

    Args:
        span: The span to traverse.

    Returns:
        The ordered spans.
    """
    stack = [span]
    ordered: list[SpanModel] = []

    while stack:
        current = stack.pop()
        ordered.append(current)
        children = list(getattr(current, "spans", []) or [])
        stack.extend(reversed(children))

    return ordered
