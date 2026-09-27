import pytest

from ai_gif_studio.engines.filtergraph import (
    build_filterchain,
    build_filtergraph,
    validate_filtergraph_labels,
)
pytestmark = pytest.mark.unit


def test_filterchain_uses_commas_without_graph_separators():
    result = build_filterchain(["scale=320:320", "format=rgba"])
    assert result == "scale=320:320,format=rgba"
    assert ";" not in result
    assert "[" not in result
    assert "]" not in result


def test_filterchain_rejects_string_input_and_embedded_graph():
    with pytest.raises(TypeError, match="iterable of filters"):
        build_filterchain("scale=320:320")
    with pytest.raises(ValueError, match="graph separators"):
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


def test_filtergraph_multiple_statements_with_valid_labels():
    parts = [
        "[0:v]scale=320:320[v0]",
        "color=c=red:s=320x320[bg]",
        "[v0][bg]overlay=0:0[out]",
    ]
    graph = build_filtergraph(parts)
    assert graph.count(";") == 2
    assert not graph.startswith(";")
    assert not graph.endswith(";")


def test_filtergraph_can_skip_label_validation():
    graph = build_filtergraph(["[v0]scale=320:320"], validate_labels=False)
    assert graph == "[v0]scale=320:320"
