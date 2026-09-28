from __future__ import annotations

import numpy as np
import pytest

from ai_gif_studio.temporal_engine.affine import AffineTransform, warp_premultiplied_rgba
from ai_gif_studio.temporal_engine.camera import CameraState
from ai_gif_studio.temporal_engine.color_export import (
    ExportColorSpec,
    linear_rgba_to_srgb_rgb,
)
from ai_gif_studio.temporal_engine.depth_field import DepthField
from ai_gif_studio.temporal_engine.manuscript import ManuscriptAsset
from ai_gif_studio.temporal_engine.material_pbr import (
    DirectLight,
    PBRMaterial,
    shade_pbr_lights,
)
from ai_gif_studio.temporal_engine.pbr_renderer import render_pbr_depth_field

pytestmark = pytest.mark.unit


def test_manuscript_asset_enforces_float_rgba_shape_but_not_semantic_color_space() -> None:
    """Characterize the current gap: ndarray carries no runtime color-space identity."""
    linear = np.full((2, 2, 4), 0.5, dtype=np.float32)
    srgb_encoded = linear.copy()
    srgb_encoded[..., :3] = 0.7353569830524495  # sRGB encoding of linear 0.5.

    asset = ManuscriptAsset(srgb_encoded)
    np.testing.assert_array_equal(asset.rgba_linear, srgb_encoded)


def test_export_boundary_currently_accepts_uint8_despite_linear_float_contract() -> None:
    """Characterize the current dtype gap without changing production behavior."""
    rgba_u8 = np.zeros((1, 1, 4), dtype=np.uint8)
    rgba_u8[0, 0] = (255, 0, 0, 255)

    encoded = linear_rgba_to_srgb_rgb(rgba_u8, ExportColorSpec())

    assert encoded.dtype == np.uint8
    assert encoded.shape == (1, 1, 3)


def test_pbr_material_rejects_wrong_runtime_material_type() -> None:
    normal = view = np.array([0.0, 0.0, 1.0], dtype=np.float64)
    light = DirectLight((0.0, 0.0, 1.0))

    with pytest.raises(TypeError, match="PBRMaterial"):
        shade_pbr_lights(normal, view, (light,), object())  # type: ignore[arg-type]


def test_warp_public_contract_is_straight_alpha_and_internal_premultiplication_is_safe() -> None:
    rgba = np.zeros((5, 5, 4), dtype=np.float32)
    rgba[2, 2] = (1.0, 0.25, 0.0, 0.5)

    warped = warp_premultiplied_rgba(
        rgba,
        AffineTransform.identity(),
        (5, 5),
    )

    assert warped.dtype == np.float32
    assert warped.shape == rgba.shape
    np.testing.assert_allclose(warped[2, 2], rgba[2, 2], rtol=0.0, atol=1e-6)
    assert np.all((warped[..., 3] >= 0.0) & (warped[..., 3] <= 1.0))


def test_renderer_boundary_precision_is_explicitly_float32_after_float64_pbr() -> None:
    """The current float64 PBR -> float32 render-buffer boundary is intentional."""
    distance = np.ones((1, 1), dtype=np.float64)
    normals = np.array([[[0.0, 0.0, 1.0]]], dtype=np.float64)
    field = DepthField(distance_px=distance, height=np.zeros_like(distance), normals=normals)
    camera = CameraState(
        position=(0.0, 0.0, 2.0),
        target=(0.0, 0.0, 0.0),
        up=(0.0, 1.0, 0.0),
        fov_y_deg=45.0,
        aspect=1.0,
    )
    points = np.array([[[0.0, 0.0, 0.0]]], dtype=np.float64)
    material = PBRMaterial((0.8, 0.4, 0.2), roughness=0.4)
    light = DirectLight((0.0, 0.0, 1.0))

    frame = render_pbr_depth_field(
        field,
        camera,
        points,
        material.albedo,
        material.roughness,
        material=material,
        lights=(light,),
    )

    assert frame.dtype == np.float32
    assert frame.shape == (1, 1, 4)
    assert np.isfinite(frame).all()
