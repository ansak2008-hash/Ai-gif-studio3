from __future__ import annotations

import pytest

from ai_gif_studio.domain.canonical_validation import (
    UTF8ValidationError,
    validate_mapping,
    validate_string,
    validate_value,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "value",
    [
        "\ud800",
        "\ud801",
        "\udbff",
        "\udc00",
        "\udfff",
        "safe\ud800text",
        "x\udfff",
        "\ud800\udfff",
    ],
)
def test_rejects_invalid_surrogate_strings(value: str) -> None:
    with pytest.raises(UTF8ValidationError):
        validate_string(value)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "ascii",
        "العربية",
        "Русский",
        "中文",
        "😀",
        "a\n\tb",
        "é",
        "𐍈",
    ],
)
def test_accepts_valid_unicode_strings(value: str) -> None:
    assert validate_string(value) == value


@pytest.mark.parametrize(
    "payload",
    [
        {"x": "\ud800"},
        {"x": ["safe", "\udfff"]},
        {"nested": {"x": "\ud800"}},
        {"layers": [{"title": "\ud800"}]},
        {"a": [{"b": [{"c": "\udfff"}]}]},
        {"\ud800": "value"},
    ],
)
def test_rejects_surrogates_in_nested_mappings(payload: dict) -> None:
    with pytest.raises((UTF8ValidationError, TypeError)):
        validate_mapping(payload)


@pytest.mark.parametrize(
    "payload",
    [
        {"x": "safe"},
        {"x": ["العربية", "Русский", "中文"]},
        {"nested": {"x": "😀"}},
        {"layers": [{"title": "مرحبا"}]},
        {"a": [{"b": [{"c": "ok"}]}]},
    ],
)
def test_accepts_nested_valid_unicode(payload: dict) -> None:
    assert validate_mapping(payload) == payload


@pytest.mark.parametrize("depth", [0, 1, 2, 8, 32, 64, 128])
def test_accepts_supported_depths(depth: int) -> None:
    payload: object = "ok"
    for _ in range(depth):
        payload = {"x": payload}
    assert validate_value(payload, max_depth=128) == payload


@pytest.mark.parametrize("depth", [129, 160, 256, 512])
def test_rejects_excessive_depth(depth: int) -> None:
    payload: object = "ok"
    for _ in range(depth):
        payload = {"x": payload}
    with pytest.raises(UTF8ValidationError):
        validate_value(payload, max_depth=128)


@pytest.mark.parametrize("value", [b"bytes", bytearray(b"bytes")])
def test_rejects_binary_values(value: object) -> None:
    with pytest.raises(TypeError):
        validate_value(value)


@pytest.mark.parametrize("value", [object(), {1: "not-a-string-key"}])
def test_rejects_non_json_types(value: object) -> None:
    with pytest.raises(TypeError):
        validate_value(value)


def test_rejects_negative_depth_limit() -> None:
    with pytest.raises(ValueError):
        validate_value("ok", max_depth=-1)


def test_mapping_is_not_mutated() -> None:
    payload = {"nested": {"value": "safe"}}
    before = repr(payload)
    validate_mapping(payload)
    assert repr(payload) == before


def test_validator_is_deterministic() -> None:
    payload = {"z": "ok", "a": ["العربية", "😀"]}
    assert validate_mapping(payload) == validate_mapping(payload)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_rejects_non_finite_numbers(value: float) -> None:
    with pytest.raises(UTF8ValidationError):
        validate_value(value)


def test_rejects_cyclic_mapping() -> None:
    payload: dict[str, object] = {}
    payload["self"] = payload
    with pytest.raises(UTF8ValidationError):
        validate_mapping(payload)


def test_rejects_cyclic_sequence() -> None:
    payload: list[object] = []
    payload.append(payload)
    with pytest.raises(UTF8ValidationError):
        validate_value(payload)
