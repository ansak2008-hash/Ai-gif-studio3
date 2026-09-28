from __future__ import annotations

import numpy as np
import pytest

from ai_gif_studio.temporal_engine.render_buffer import RenderBuffer
from ai_gif_studio.temporal_engine.render_graph import RenderGraph, RenderNode

pytestmark = pytest.mark.unit


def _buffer(value: float = 1.0) -> RenderBuffer:
    return RenderBuffer.from_linear_rgba(
        np.full((1, 1, 4), (value, value, value, 1.0), dtype=np.float32)
    )


def test_render_node_requires_non_empty_unique_name() -> None:
    with pytest.raises(ValueError, match="name"):
        RenderNode("", lambda inputs: inputs[0])
    with pytest.raises(TypeError, match="callable"):
        RenderNode("stage", None)  # type: ignore[arg-type]

def test_graph_rejects_duplicate_names() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        RenderGraph([
            RenderNode("stage", lambda inputs: inputs[0]),
            RenderNode("stage", lambda inputs: inputs[0]),
        ])

def test_graph_rejects_missing_dependency_and_self_dependency() -> None:
    with pytest.raises(ValueError, match="missing"):
        RenderGraph([RenderNode("stage", lambda buffer: buffer, ("unknown",))])
    with pytest.raises(ValueError, match="itself"):
        RenderGraph([RenderNode("stage", lambda buffer: buffer, ("stage",))])

def test_graph_rejects_cycles_before_execution() -> None:
    called = []
    nodes = [
        RenderNode("a", lambda inputs: called.append("a") or inputs[0], ("b",)),
        RenderNode("b", lambda inputs: called.append("b") or inputs[0], ("a",)),
    ]
    with pytest.raises(ValueError, match="cycle"):
        RenderGraph(nodes)
    assert called == []

def test_graph_rejects_empty_graph() -> None:
    with pytest.raises(ValueError, match="at least one"):
        RenderGraph([])

def test_graph_requires_one_terminal_output() -> None:
    nodes = [RenderNode("a", lambda inputs: inputs[0]), RenderNode("b", lambda inputs: inputs[0])]
    with pytest.raises(ValueError, match="terminal"):
        RenderGraph(nodes)

def test_graph_executes_dependencies_in_stable_order() -> None:
    order: list[str] = []
    def stage(name: str):
        def run(inputs: tuple[RenderBuffer, ...]) -> RenderBuffer:
            order.append(name)
            return inputs[-1].copy()
        return run
    graph = RenderGraph([
        RenderNode("root", stage("root")),
        RenderNode("left", stage("left"), ("root",)),
        RenderNode("right", stage("right"), ("root",)),
        RenderNode("final", stage("final"), ("left", "right")),
    ])
    result = graph.execute(_buffer())
    assert order == ["root", "left", "right", "final"]
    assert isinstance(result, RenderBuffer)

def test_graph_does_not_mutate_initial_buffer() -> None:
    source = _buffer(2.0)
    before = source.data.copy()
    graph = RenderGraph([RenderNode("copy", lambda inputs: inputs[0].copy())])
    result = graph.execute(source)
    np.testing.assert_array_equal(source.data, before)
    assert result is not source

def test_graph_rejects_non_renderbuffer_output() -> None:
    graph = RenderGraph([RenderNode("bad", lambda inputs: np.zeros((1, 1, 4), dtype=np.float32))])
    with pytest.raises(TypeError, match="bad"):
        graph.execute(_buffer())

def test_graph_rejects_dimension_changes() -> None:
    def resize(_: tuple[RenderBuffer, ...]) -> RenderBuffer:
        return RenderBuffer.allocate(2, 1)
    graph = RenderGraph([RenderNode("resize", resize)])
    with pytest.raises(ValueError, match="dimensions"):
        graph.execute(_buffer())

def test_graph_produces_terminal_output_and_allows_identity() -> None:
    source = _buffer(3.0)
    graph = RenderGraph([RenderNode("identity", lambda inputs: inputs[0].copy())])
    result = graph.execute(source)
    assert isinstance(result, RenderBuffer)
    assert result is not source
    np.testing.assert_array_equal(result.data, source.data)

def test_graph_runtime_node_errors_propagate() -> None:
    error = RuntimeError("node failed")
    def fail(_: tuple[RenderBuffer, ...]) -> RenderBuffer:
        raise error
    graph = RenderGraph([RenderNode("fail", fail)])
    with pytest.raises(RuntimeError) as caught:
        graph.execute(_buffer())
    assert caught.value is error


def test_graph_passes_dependencies_in_declared_order() -> None:
    received: list[tuple[float, ...]] = []

    def first(inputs: tuple[RenderBuffer, ...]) -> RenderBuffer:
        return RenderBuffer.from_linear_rgba(
            np.full((1, 1, 4), (1, 1, 1, 1), dtype=np.float32)
        )

    def second(inputs: tuple[RenderBuffer, ...]) -> RenderBuffer:
        return RenderBuffer.from_linear_rgba(
            np.full((1, 1, 4), (2, 2, 2, 1), dtype=np.float32)
        )

    def merge(inputs: tuple[RenderBuffer, ...]) -> RenderBuffer:
        received.append(tuple(float(item.data[0, 0, 0]) for item in inputs))
        return inputs[1].copy()

    graph = RenderGraph(
        [
            RenderNode("first", first),
            RenderNode("second", second),
            RenderNode("merge", merge, ("second", "first")),
        ]
    )
    graph.execute(_buffer())
    assert received == [(2.0, 1.0)]


def test_graph_rejects_returning_an_input_buffer() -> None:
    graph = RenderGraph([RenderNode("alias", lambda inputs: inputs[0])])
    with pytest.raises(ValueError, match="new RenderBuffer"):
        graph.execute(_buffer())
