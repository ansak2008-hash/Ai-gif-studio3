import pytest

from ai_gif_studio.engines.filtergraph import (
    build_filterchain,
    build_filtergraph,
    validate_filtergraph_labels,
)


def test_filterchain_uses_commas_without_graph_separators():
    result = build_filterchain(["scale=320:320", "format=rgba"])
    assert result == "scale=320:320,format=rgba"
    assert ";" not in result
    assert "[" not in result
    assert "]" not in result


def test_filterchain_rejects_string_input_and_embedded_graph():
    with pytest.raises(TypeError):
        build_filterchain("scale=320:320")
    with pytest.raises(ValueError):
        build_filterchain(["scale=320:320;[x]null[y]"])


def test_filtergraph_preserves_multi_stream_labels():
    result = build_filtergraph([
        "[0:v]scale=320:320[fg]",
        "color=c=black:s=320x320:d=1[bg]",
        "[bg][fg]overlay=shortest=1[out]",
    ])
    assert result.count(";") == 2
    assert "[0:v]" in result
    assert "[bg][fg]" in result
    assert result.endswith("[out]")


def test_filtergraph_rejects_undefined_and_duplicate_labels():
    with pytest.raises(ValueError, match="undefined labels"):
        build_filtergraph(["[missing]null[out]"])
    with pytest.raises(ValueError, match="duplicate"):
        build_filtergraph(["[0:v]null[x]", "[1:v]null[x]"])


def test_filtergraph_rejects_empty_statements_and_string_input():
    with pytest.raises(ValueError):
        build_filtergraph(["[0:v]null[out]", ""])
    with pytest.raises(TypeError):
        build_filtergraph("[0:v]null[out]")


def test_label_validator_accepts_external_inputs_and_terminal_output():
    graph = "[0:v]null[a];[a]null[out]"
    assert validate_filtergraph_labels(graph) == graph
