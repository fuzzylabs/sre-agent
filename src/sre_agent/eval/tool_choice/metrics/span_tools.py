"""Helpers for extracting tool-call spans in tool choice evaluation."""

from opik.message_processing.emulation.models import SpanModel


def extract_tool_names(task_span: SpanModel | None) -> list[str]:
    """Extract ordered tool names from a task span tree."""
    if task_span is None:
        return []

    names: list[str] = []
    for span in _iter_spans(task_span):
        if getattr(span, "type", None) != "tool":
            continue

        name = str(getattr(span, "name", "")).strip()
        if name:
            names.append(name)

    return names


def _iter_spans(span: SpanModel) -> list[SpanModel]:
    """Traverse span tree in depth-first order."""
    stack = [span]
    ordered: list[SpanModel] = []

    while stack:
        current = stack.pop()
        ordered.append(current)
        children = list(getattr(current, "spans", []) or [])
        stack.extend(reversed(children))

    return ordered
