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


def test_filterchain_rejects_string_and_embedded_graph():
    with pytest.raises(TypeError, match="iterable of filters"):
        build_filterchain("scale=320:320")
    with pytest.raises(ValueError, match="graph separators"):
        build_filterchain(["scale=320:320;[x]null[y]"])


def test_filtergraph_regression_no_character_splitting():
    parts = [
        "[0:v]crop=360:360:0:0[fg]",
        "color=c=#101820:s=320x320:d=1[bg]",
        "[bg][fg]overlay=x=0:y=0:shortest=1[composed]",
        "[composed]drawbox=x=3:y=3:w=314:h=314:color=#ffffff:t=3[out]",
    ]
    result = build_filtergraph(parts)
    assert result.split(";") == parts
    assert "[;c;o;m;p;o;s;e;d;]" not in result
    assert "[;d;r;a;w;b;o;x;]" not in result


def test_filtergraph_rejects_string_and_empty_parts():
    with pytest.raises(TypeError, match="iterable of graph statements"):
        build_filtergraph("[composed]drawbox=...")
    with pytest.raises(ValueError, match="Empty graph statement"):
        build_filtergraph(["[0:v]null[out]", ""])


def test_filtergraph_validates_undefined_and_duplicate_labels():
    with pytest.raises(ValueError, match="undefined labels"):
        build_filtergraph(["[missing]null[out]"])
    with pytest.raises(ValueError, match="duplicate"):
        build_filtergraph(["[0:v]null[x]", "[1:v]null[x]"])


def test_filtergraph_accepts_external_inputs_and_terminal_output():
    graph = "[0:v]null[a];[a]null[out]"
    assert validate_filtergraph_labels(graph) == graph
