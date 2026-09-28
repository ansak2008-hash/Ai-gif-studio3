from __future__ import annotations

import numpy as np
import pytest

from ai_gif_studio.temporal_engine.material_pbr import DirectLight, PBRMaterial
from ai_gif_studio.temporal_engine.render_buffer import RenderBuffer
from ai_gif_studio.temporal_engine.pbr_graph import PBRDirectLightNode
from ai_gif_studio.temporal_engine.render_graph import RenderGraph, RenderNode

pytestmark = pytest.mark.unit


def _scene() -> tuple[RenderBuffer, np.ndarray, np.ndarray, PBRMaterial, tuple[DirectLight, ...]]:
    rgba = np.zeros((4, 5, 4), dtype=np.float32)
    rgba[..., :3] = (0.8, 0.3, 0.1)
    rgba[..., 3] = 1.0
    normals = np.zeros((4, 5, 3), dtype=np.float64)
    normals[..., 2] = 1.0
    views = normals.copy()
    material = PBRMaterial((0.8, 0.3, 0.1), roughness=0.35, metallic=0.25)
    lights = (DirectLight((0.0, 0.0, 1.0), intensity=1.5),)
    return RenderBuffer.from_linear_rgba(rgba), normals, views, material, lights


def test_pbr_graph_node_produces_canonical_render_buffer() -> None:
    source, normals, views, material, lights = _scene()
    node = PBRDirectLightNode(normals, views, material, lights)
    result = node.process((source,))
    assert isinstance(result, RenderBuffer)
    assert result.shape == source.shape
    assert result.dtype == np.dtype(np.float32)
    assert np.isfinite(result.data).all()
    np.testing.assert_array_equal(result.data[..., 3], source.data[..., 3])


def test_pbr_graph_node_uses_existing_pbr_kernel_and_is_deterministic() -> None:
    source, normals, views, material, lights = _scene()
    node = PBRDirectLightNode(normals, views, material, lights)
    first = node.process((source,))
    second = node.process((source,))
    np.testing.assert_array_equal(first.data, second.data)


def test_pbr_graph_node_does_not_mutate_input_and_owns_output() -> None:
    source, normals, views, material, lights = _scene()
    before = source.data.copy()
    result = PBRDirectLightNode(normals, views, material, lights).process((source,))
    np.testing.assert_array_equal(source.data, before)
    assert not np.shares_memory(source.data, result.data)


@pytest.mark.parametrize("metallic,roughness", [(0.25, 0.2), (0.5, 0.5), (0.75, 0.8)])
def test_pbr_graph_node_intermediate_materials_remain_energy_bounded(metallic, roughness) -> None:
    source, normals, views, _, lights = _scene()
    material = PBRMaterial((0.8, 0.3, 0.1), roughness=roughness, metallic=metallic)
    result = PBRDirectLightNode(normals, views, material, lights).process((source,))
    assert np.all(result.data[..., :3] >= 0.0)
    assert np.isfinite(result.data[..., :3]).all()


def test_pbr_graph_node_rejects_wrong_input_count() -> None:
    _, normals, views, material, lights = _scene()
    node = PBRDirectLightNode(normals, views, material, lights)
    with pytest.raises(ValueError):
        node.process(())
    with pytest.raises(ValueError):
        node.process((RenderBuffer.allocate(5, 4), RenderBuffer.allocate(5, 4)))


def test_pbr_graph_node_rejects_geometry_dimension_mismatch() -> None:
    source, normals, views, material, lights = _scene()
    bad_normals = normals[:-1]
    with pytest.raises(ValueError, match="normals and views must have identical shapes"):
        PBRDirectLightNode(bad_normals, views, material, lights)


def test_pbr_graph_node_integrates_with_render_graph() -> None:
    source, normals, views, material, lights = _scene()
    pbr = PBRDirectLightNode(normals, views, material, lights)
    graph = RenderGraph((RenderNode("pbr", pbr.process),))
    result = graph.execute(source)
    assert result.shape == source.shape
    assert result.dtype == np.dtype(np.float32)
