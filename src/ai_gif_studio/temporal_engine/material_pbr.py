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
