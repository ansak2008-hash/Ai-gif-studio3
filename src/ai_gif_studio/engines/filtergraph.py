from __future__ import annotations

from collections.abc import Iterable


def build_filtergraph(filters: Iterable[str]) -> str:
    """Join complete FFmpeg filtergraph statements without splitting strings."""
    if isinstance(filters, str):
        raise TypeError(
            "build_filtergraph expects an iterable of filters, not a string. "
            "Wrap single filters in a list: [filter]"
        )
    parts = list(filters)
    for index, value in enumerate(parts):
        if not isinstance(value, str):
            raise TypeError(f"Filter at index {index} is not str: {type(value)}")
        if not value:
            raise ValueError(f"Empty filter at index {index}")
    return ";".join(parts)
