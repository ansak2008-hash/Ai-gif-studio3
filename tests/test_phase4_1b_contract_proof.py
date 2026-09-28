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


def test_manuscript_asset_rejects_invalid_linear_ranges() -> None:
    invalid_rgb = np.zeros((1, 1, 4), dtype=np.float32)
    invalid_rgb[0, 0, 0] = -0.01
    with pytest.raises(ValueError, match="non-negative"):
        ManuscriptAsset(invalid_rgb)

    invalid_alpha = np.ones((1, 1, 4), dtype=np.float32)
    invalid_alpha[0, 0, 3] = 1.01
    with pytest.raises(ValueError, match="alpha"):
        ManuscriptAsset(invalid_alpha)


def test_manuscript_asset_owns_read_only_storage() -> None:
    source = np.full((1, 1, 4), 0.5, dtype=np.float32)
    source[..., 3] = 1.0
    asset = ManuscriptAsset(source)

    source[0, 0, 0] = 0.0
    assert asset.rgba_linear[0, 0, 0] == 0.5
    assert asset.rgba_linear.flags.writeable is False

    with pytest.raises(ValueError, match="read-only"):
        asset.rgba_linear[0, 0, 0] = 0.0


def test_manuscript_asset_preserves_hdr_linear_rgb() -> None:
    rgba = np.array([[[2.0, 1.0, 0.5, 1.0]]], dtype=np.float32)
    asset = ManuscriptAsset(rgba)
    np.testing.assert_array_equal(asset.rgba_linear, rgba)


def test_from_rgba_u8_requires_uint8() -> None:
    with pytest.raises(TypeError, match="uint8"):
        ManuscriptAsset.from_rgba_u8(np.zeros((1, 1, 4), dtype=np.uint16))


def test_export_boundary_rejects_non_float_linear_rgba() -> None:
    rgba_u8 = np.zeros((1, 1, 4), dtype=np.uint8)
    with pytest.raises(TypeError, match="floating point"):
        linear_rgba_to_srgb_rgb(rgba_u8, ExportColorSpec())


def test_export_boundary_rejects_invalid_alpha_and_negative_rgb() -> None:
    invalid_alpha = np.ones((1, 1, 4), dtype=np.float32)
    invalid_alpha[0, 0, 3] = -0.1
    with pytest.raises(ValueError, match="alpha"):
        linear_rgba_to_srgb_rgb(invalid_alpha)

    invalid_rgb = np.ones((1, 1, 4), dtype=np.float32)
    invalid_rgb[0, 0, 0] = -0.1
    with pytest.raises(ValueError, match="non-negative"):
        linear_rgba_to_srgb_rgb(invalid_rgb)


def test_manuscript_asset_accepts_float_linear_data() -> None:
    linear = np.full((2, 2, 4), 0.5, dtype=np.float32)
    asset = ManuscriptAsset(linear)
    np.testing.assert_array_equal(asset.rgba_linear, linear)


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
