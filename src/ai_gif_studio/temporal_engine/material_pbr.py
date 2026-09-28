"""Pure deterministic PBR microfacet primitives.

Phase 3 foundation: GGX distribution, Smith masking-shadowing, and
Fresnel-Schlick. These functions are intentionally renderer-agnostic.

Precision contract:
    PBR primitives compute and return float64 values. Callers that need
    float32 rendering buffers should cast explicitly at the pipeline boundary.
"""
from __future__ import annotations

import numpy as np

_EPS_DENOM = np.finfo(np.float64).eps


def _clamp01(value: np.ndarray | float) -> np.ndarray:
    return np.clip(np.asarray(value, dtype=np.float64), 0.0, 1.0)


def fresnel_schlick(
    cos_theta: np.ndarray | float,
    f0: np.ndarray | float,
) -> np.ndarray:
    """Evaluate the Schlick Fresnel approximation."""
    c = _clamp01(cos_theta)
    base = np.asarray(f0, dtype=np.float64)
    if np.any(base < 0.0) or np.any(base > 1.0):
        raise ValueError("f0 must be in [0, 1]")
    return base + (1.0 - base) * np.power(1.0 - c, 5.0)


def ggx_distribution(ndoth: np.ndarray | float, roughness: float) -> np.ndarray:
    """Evaluate the isotropic Trowbridge-Reitz (GGX) normal distribution."""
    if not np.isfinite(roughness) or not 0.0 < roughness <= 1.0:
        raise ValueError("roughness must be finite and in (0, 1]")
    c = _clamp01(ndoth)
    alpha = float(roughness) ** 2
    alpha2 = alpha * alpha
    base = np.square(c) * (alpha2 - 1.0) + 1.0
    denominator = np.pi * np.square(base)
    return alpha2 / denominator


def _smith_ggx_g1(ndotx: np.ndarray, roughness: float) -> np.ndarray:
    alpha2 = float(roughness) ** 2
    c = _clamp01(ndotx)
    c2 = np.square(c)
    denominator = c + np.sqrt(c2 + alpha2 * (1.0 - c2))
    return (2.0 * c) / denominator


def smith_geometry(
    ndotv: np.ndarray | float,
    ndotl: np.ndarray | float,
    roughness: float,
) -> np.ndarray:
    """Evaluate the separable Smith GGX masking-shadowing term."""
    if not np.isfinite(roughness) or not 0.0 < roughness <= 1.0:
        raise ValueError("roughness must be finite and in (0, 1]")
    v = _clamp01(ndotv)
    ndl = _clamp01(ndotl)
    return _smith_ggx_g1(v, roughness) * _smith_ggx_g1(ndl, roughness)


def cook_torrance_specular(
    ndotv: np.ndarray | float,
    ndotl: np.ndarray | float,
    ndoth: np.ndarray | float,
    vdoth: np.ndarray | float,
    roughness: float,
    f0: np.ndarray | float,
) -> np.ndarray:
    """Evaluate the Cook-Torrance microfacet specular BRDF.

    All dot products are clamped to [0, 1]. They must originate from the
    same N, V, L geometry; this primitive does not reconstruct that geometry.
    Roughness must be finite and in (0, 1], and f0 must be in [0, 1].
    """
    v = _clamp01(ndotv)
    ndl = _clamp01(ndotl)
    h = _clamp01(ndoth)
    vh = _clamp01(vdoth)
    d = ggx_distribution(h, roughness)
    g = smith_geometry(v, ndl, roughness)
    f = fresnel_schlick(vh, f0)
    denominator = np.maximum(4.0 * v * ndl, _EPS_DENOM)
    return d * g * f / denominator


def _normalize_vectors(value: np.ndarray | list[float], name: str) -> np.ndarray:
    vectors = np.asarray(value, dtype=np.float64)
    if vectors.shape[-1] != 3:
        raise ValueError(f"{name} must have a final dimension of 3")
    length = np.linalg.norm(vectors, axis=-1, keepdims=True)
    if np.any(length <= _EPS_DENOM) or not np.isfinite(length).all():
        raise ValueError(f"{name} must contain finite non-zero vectors")
    return vectors / length


def shade_pbr(
    normal: np.ndarray,
    view: np.ndarray,
    light: np.ndarray,
    albedo: np.ndarray | list[float],
    roughness: float,
    metallic: float = 0.0,
    light_color: np.ndarray | list[float] | float = 1.0,
    light_intensity: float = 1.0,
) -> np.ndarray:
    """Evaluate one deterministic direct-light PBR sample.

    The inputs N, V, and L are normalized internally. The returned value is
    linear RGB radiance. This stage owns geometry-derived dot products and
    the standard metallic energy split; the microfacet primitives remain
    renderer-agnostic.
    """
    if not np.isfinite(metallic) or not 0.0 <= metallic <= 1.0:
        raise ValueError("metallic must be finite and in [0, 1]")
    if not np.isfinite(light_intensity) or light_intensity < 0.0:
        raise ValueError("light_intensity must be finite and non-negative")

    n = _normalize_vectors(normal, "normal")
    v = _normalize_vectors(view, "view")
    light_vector = _normalize_vectors(light, "light")
    base_color = np.asarray(albedo, dtype=np.float64)
    if base_color.shape[-1] != 3:
        raise ValueError("albedo must have a final dimension of 3")
    if np.any(base_color < 0.0) or np.any(base_color > 1.0):
        raise ValueError("albedo must be in [0, 1]")

    radiance = np.asarray(light_color, dtype=np.float64)
    if np.any(radiance < 0.0) or not np.isfinite(radiance).all():
        raise ValueError("light_color must be finite and non-negative")

    ndotv = np.sum(n * v, axis=-1)
    ndotl = np.sum(n * light_vector, axis=-1)
    visible = (ndotv > 0.0) & (ndotl > 0.0)

    half_raw = v + light_vector
    half_length = np.linalg.norm(half_raw, axis=-1, keepdims=True)
    safe_half_length = np.maximum(half_length, _EPS_DENOM)
    half = half_raw / safe_half_length
    ndoth = np.sum(n * half, axis=-1)
    vdoth = np.sum(v * half, axis=-1)

    f0 = 0.04 * (1.0 - metallic) + base_color * metallic
    fresnel = fresnel_schlick(vdoth[..., None], f0)
    specular = cook_torrance_specular(
        ndotv[..., None],
        ndotl[..., None],
        ndoth[..., None],
        vdoth[..., None],
        roughness,
        f0,
    )
    diffuse_weight = (1.0 - fresnel) * (1.0 - metallic)
    diffuse = diffuse_weight * base_color / np.pi
    brdf = diffuse + specular
    result = brdf * ndotl[..., None] * radiance * light_intensity
    return np.where(visible[..., None], result, 0.0)
