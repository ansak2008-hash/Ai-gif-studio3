from __future__ import annotations

import re
from collections.abc import Iterable

_LABEL_RE = re.compile(r"\[([A-Za-z_][A-Za-z0-9_:]*)\]")
_EXTERNAL_LABELS = {"0:v", "1:v", "2:v", "3:v"}


def build_filterchain(filters: Iterable[str]) -> str:
    """Join filters that operate sequentially on one stream."""
    if isinstance(filters, str):
        raise TypeError(
            "build_filterchain expects an iterable of filters, not a string. "
            "Wrap a single filter in a list: [filter]"
        )
    parts = list(filters)
    for index, value in enumerate(parts):
        if not isinstance(value, str):
            raise TypeError(f"Filter at index {index} is not str: {type(value)}")
        if not value.strip():
            raise ValueError(f"Empty filter at index {index}")
        if any(token in value for token in (";", "[", "]")):
            raise ValueError(
                "Filter-chain items must not contain graph separators or labels; "
                "use build_filtergraph for multi-stream graphs"
            )
    return ",".join(parts)


def validate_filtergraph_labels(graph: str) -> str:
    """Validate internal FFmpeg stream labels without interpreting filter options."""
    if not isinstance(graph, str):
        raise TypeError("graph must be a string")
    statements = [item.strip() for item in graph.split(";")]
    if any(not item for item in statements):
        raise ValueError("filtergraph contains an empty statement")

    defined: set[str] = set()
    consumed: list[str] = []
    for statement in statements:
        labels = _LABEL_RE.findall(statement)
        if not labels:
            continue
        input_labels = []
        cursor = 0
        for match in _LABEL_RE.finditer(statement):
            if match.start() != cursor:
                break
            input_labels.append(match.group(1))
            cursor = match.end()
        output_labels = []
        cursor = len(statement)
        matches = list(_LABEL_RE.finditer(statement))
        for match in reversed(matches):
            if match.end() != cursor:
                break
            output_labels.append(match.group(1))
            cursor = match.start()
        output_labels.reverse()
        for label in output_labels:
            if label in defined:
                raise ValueError(f"duplicate filtergraph output label: [{label}]")
            defined.add(label)
        consumed.extend(input_labels)

    missing = sorted(
        label for label in consumed
        if label not in defined and label not in _EXTERNAL_LABELS
    )
    if missing:
        raise ValueError(f"filtergraph references undefined labels: {missing}")
    return graph


def build_filtergraph(filters: Iterable[str]) -> str:
    """Join complete FFmpeg filtergraph statements with semicolons."""
    if isinstance(filters, str):
        raise TypeError(
            "build_filtergraph expects an iterable of graph statements, not a string"
        )
    parts = list(filters)
    for index, value in enumerate(parts):
        if not isinstance(value, str):
            raise TypeError(f"Graph statement at index {index} is not str: {type(value)}")
        if not value.strip():
            raise ValueError(f"Empty graph statement at index {index}")
        if ";" in value:
            raise ValueError(
                "Graph statements must not contain ';'; split them before calling build_filtergraph"
            )
    graph = ";".join(parts)
    return validate_filtergraph_labels(graph)
