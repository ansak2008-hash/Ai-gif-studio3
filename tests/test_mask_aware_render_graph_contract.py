from __future__ import annotations

import numpy as np
import pytest

from ai_gif_studio.temporal_engine.render_buffer import RenderBuffer
from ai_gif_studio.temporal_engine.render_graph import RenderGraph, RenderNode
from ai_gif_studio.temporal_engine.render_mask import RenderMask

pytestmark = pytest.mark.unit


def _buffer(values: tuple[float, float, float, float]) -> RenderBuffer:
    return RenderBuffer.from_linear_rgba(
        np.asarray([[values]], dtype=np.float32)
    )


def _processed(_: tuple[RenderBuffer, ...]) -> RenderBuffer:
    return _buffer((10.0, 20.0, 30.0, 0.25))


def test_masked_node_requires_render_mask() -> None:
    with pytest.raises(TypeError, match="RenderMask"):
        RenderNode("masked", _processed, mask=object())  # type: ignore[arg-type]


def test_masked_node_rejects_fan_in_dependencies() -> None:
    with pytest.raises(ValueError, match="unary"):
        RenderGraph(
            [
                RenderNode("a", lambda inputs: inputs[0].copy()),
                RenderNode("b", lambda inputs: inputs[0].copy()),
                RenderNode(
                    "masked",
                    lambda inputs: inputs[0].copy(),
                    dependencies=("a", "b"),
                    mask=RenderMask.allocate(1, 1, value=1.0),
                ),
            ]
        )


def test_zero_mask_reproduces_source_exactly() -> None:
    source = _buffer((2.0, 4.0, 6.0, 0.8))
    graph = RenderGraph(
        [
            RenderNode(
                "masked",
                _processed,
                mask=RenderMask.allocate(1, 1, value=0.0),
            )
        ]
    )
    result = graph.execute(source)
    np.testing.assert_array_equal(result.data, source.data)


def test_full_mask_reproduces_processed_result_exactly() -> None:
    source = _buffer((2.0, 4.0, 6.0, 0.8))
    graph = RenderGraph(
        [
            RenderNode(
                "masked",
                _processed,
                mask=RenderMask.allocate(1, 1, value=1.0),
            )
        ]
    )
    result = graph.execute(source)
    np.testing.assert_array_equal(result.data, _processed((source,)).data)


def test_intermediate_mask_interpolates_all_rgba_channels() -> None:
    source = _buffer((2.0, 4.0, 6.0, 0.8))
    graph = RenderGraph(
        [
            RenderNode(
                "masked",
                _processed,
                mask=RenderMask.allocate(1, 1, value=0.25),
            )
        ]
    )
    result = graph.execute(source)
    expected = np.asarray([[[4.0, 8.0, 12.0, 0.6625]]], dtype=np.float32)
    np.testing.assert_allclose(result.data, expected, rtol=0.0, atol=1e-6)


def test_masked_node_works_with_one_dependency() -> None:
    source = _buffer((1.0, 1.0, 1.0, 1.0))
    graph = RenderGraph(
        [
            RenderNode("root", lambda inputs: _buffer((2.0, 3.0, 4.0, 0.5))),
            RenderNode(
                "masked",
                _processed,
                dependencies=("root",),
                mask=RenderMask.allocate(1, 1, value=0.5),
            ),
        ]
    )
    result = graph.execute(source)
    expected = np.asarray([[[6.0, 11.5, 17.0, 0.375]]], dtype=np.float32)
    np.testing.assert_allclose(result.data, expected, rtol=0.0, atol=1e-6)


def test_masked_node_rejects_dimension_mismatch() -> None:
    source = _buffer((1.0, 1.0, 1.0, 1.0))
    graph = RenderGraph(
        [
            RenderNode(
                "masked",
                _processed,
                mask=RenderMask.allocate(2, 1, value=1.0),
            )
        ]
    )
    with pytest.raises(ValueError, match="mask dimensions"):
        graph.execute(source)


def test_masking_does_not_mutate_source_or_processed_result() -> None:
    source = _buffer((2.0, 4.0, 6.0, 0.8))
    before = source.data.copy()
    processed = _buffer((10.0, 20.0, 30.0, 0.25))

    def process(_: tuple[RenderBuffer, ...]) -> RenderBuffer:
        return processed

    graph = RenderGraph(
        [
            RenderNode(
                "masked",
                process,
                mask=RenderMask.allocate(1, 1, value=0.5),
            )
        ]
    )
    result = graph.execute(source)
    np.testing.assert_array_equal(source.data, before)
    np.testing.assert_array_equal(processed.data, _buffer((10.0, 20.0, 30.0, 0.25)).data)
    assert result is not source
    assert result is not processed


def test_unmasked_nodes_keep_existing_behavior() -> None:
    source = _buffer((3.0, 3.0, 3.0, 1.0))
    graph = RenderGraph([RenderNode("identity", lambda inputs: inputs[0].copy())])
    result = graph.execute(source)
    np.testing.assert_array_equal(result.data, source.data)


def test_masked_runtime_errors_propagate() -> None:
    error = RuntimeError("effect failed")

    def fail(_: tuple[RenderBuffer, ...]) -> RenderBuffer:
        raise error

    graph = RenderGraph(
        [
            RenderNode(
                "masked",
                fail,
                mask=RenderMask.allocate(1, 1, value=0.5),
            )
        ]
    )
    with pytest.raises(RuntimeError) as caught:
        graph.execute(_buffer((1.0, 1.0, 1.0, 1.0)))
    assert caught.value is error
