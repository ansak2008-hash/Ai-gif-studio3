from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
from typing import Any

DEFAULT_MAX_DEPTH = 128


class UTF8ValidationError(ValueError):
    """Raised when canonical data cannot be represented as strict UTF-8."""


def validate_string(value: str, *, context: str = "value") -> str:
    if not isinstance(value, str):
        raise TypeError(f"{context} must be a string")
    for index, char in enumerate(value):
        if 0xD800 <= ord(char) <= 0xDFFF:
            raise UTF8ValidationError(
                f"{context} contains an invalid UTF-8 surrogate at index {index}"
            )
    try:
        value.encode("utf-8", "strict")
    except UnicodeEncodeError as exc:
        raise UTF8ValidationError(f"{context} is not valid UTF-8") from exc
    return value


def validate_value(
    value: Any, *, context: str = "value", max_depth: int = DEFAULT_MAX_DEPTH
) -> Any:
    if max_depth < 0:
        raise ValueError("max_depth must be non-negative")
    _validate_value(value, context=context, depth=0, max_depth=max_depth, active_ids=set())
    return value


def _validate_value(
    value: Any,
    *,
    context: str,
    depth: int,
    max_depth: int,
    active_ids: set[int],
) -> None:
    if depth > max_depth:
        raise UTF8ValidationError(f"{context} exceeds maximum validation depth")
    if isinstance(value, str):
        validate_string(value, context=context)
        return
    if isinstance(value, Mapping):
        identity = id(value)
        if identity in active_ids:
            raise UTF8ValidationError(f"{context} contains a cyclic container")
        active_ids.add(identity)
        try:
            items = list(value.items())
            for key, item in items:
            if not isinstance(key, str):
                raise TypeError(f"{context} keys must be strings")
            validate_string(key, context=f"{context}.key")
                _validate_value(
                    item,
                    context=f"{context}[{key!r}]",
                    depth=depth + 1,
                    max_depth=max_depth,
                    active_ids=active_ids,
                )
        finally:
            active_ids.remove(identity)
        return
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        identity = id(value)
        if identity in active_ids:
            raise UTF8ValidationError(f"{context} contains a cyclic container")
        active_ids.add(identity)
        try:
            items = list(value)
            for index, item in enumerate(items):
                _validate_value(
                    item,
                    context=f"{context}[{index}]",
                    depth=depth + 1,
                    max_depth=max_depth,
                    active_ids=active_ids,
                )
        finally:
            active_ids.remove(identity)
        return
    if value is None or isinstance(value, bool) or isinstance(value, int):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise UTF8ValidationError(f"{context} must be finite")
        return
    raise TypeError(f"{context} contains unsupported value type: {type(value).__name__}")


def validate_mapping(
    value: Mapping[str, Any],
    *,
    context: str = "mapping",
    max_depth: int = DEFAULT_MAX_DEPTH,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{context} must be a mapping")
    validate_value(value, context=context, max_depth=max_depth)
    return value
