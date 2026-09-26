import pytest

from ai_gif_studio.engines.filtergraph import build_filtergraph


def test_filtergraph_no_char_splitting():
    """Regression: a single filter statement must remain intact."""
    assert build_filtergraph(["[composed]"]) == "[composed]"
    assert ";" not in build_filtergraph(["[composed]"])


def test_filtergraph_multiple_filters():
    fg = build_filtergraph(["[v0]scale=320:320", "[bg]null", "[v0][bg]overlay"])
    assert fg.count(";") == 2
    assert not fg.startswith(";")
    assert not fg.endswith(";")


def test_filtergraph_rejects_string():
    with pytest.raises(TypeError, match="iterable of filters"):
        build_filtergraph("[composed]")


def test_filtergraph_rejects_empty_filter():
    with pytest.raises(ValueError, match="Empty filter"):
        build_filtergraph(["[v0]scale", "", "[bg]null"])
