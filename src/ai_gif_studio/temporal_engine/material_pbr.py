"""Pure deterministic PBR microfacet primitives.

Phase 3 foundation: GGX distribution, Smith masking-shadowing, and
Fresnel-Schlick.  These functions are intentionally renderer-agnostic.
"""
from __future__ import annotations

import numpy as np


_EPS = np.float32(1e-7)


def _clamp01(value: np.ndarray | float) -> np.ndarray:
    return np.clip(np.asarray(value, dtype=np.float32), 0.0, 1.0)


def fresnel_schlick(cos_theta: np.ndarray | float, f0: np.ndarray | float) -> np.ndarray:
    """Evaluate the Schlick Fresnel approximation."""
    c = _clamp01(cos_theta)
    base = np.asarray(f0, dtype=np.float32)
    if np.any(base < 0.0) or np.any(base > 1.0):
        raise ValueError("f0 must be in [0, 1]")
    return base + (1.0 - base) * np.power(1.0 - c, 5.0)


def ggx_distribution(ndoth: np.ndarray | float, roughness: float) -> np.ndarray:
    """Evaluate the isotropic Trowbridge-Reitz (GGX) normal distribution."""
    if not np.isfinite(roughness) or not 0.0 < roughness <= 1.0:
        raise ValueError("roughness must be finite and in (0, 1]")
    c = _clamp01(ndoth)
    alpha = np.float32(roughness * roughness)
    alpha2 = alpha * alpha
    denominator = np.pi * np.square(np.square(c) * (alpha2 - 1.0) + 1.0)
    return alpha2 / np.maximum(denominator, _EPS)


def _smith_ggx_g1(ndotx: np.ndarray, roughness: float) -> np.ndarray:
    alpha2 = np.float32(roughness * roughness)
    c = _clamp01(ndotx)
    c2 = c * c
    return (2.0 * c) / np.maximum(c + np.sqrt(c2 + alpha2 * (1.0 - c2)), _EPS)


def smith_geometry(
    ndotv: np.ndarray | float,
    ndotl: np.ndarray | float,
    roughness: float,
) -> np.ndarray:
    """Evaluate the separable Smith GGX masking-shadowing term."""
    if not np.isfinite(roughness) or not 0.0 < roughness <= 1.0:
        raise ValueError("roughness must be finite and in (0, 1]")
    v = _clamp01(ndotv)
    l = _clamp01(ndotl)
    return _smith_ggx_g1(v, roughness) * _smith_ggx_g1(l, roughness)


def cook_torrance_specular(
    ndotv: np.ndarray | float,
    ndotl: np.ndarray | float,
    ndoth: np.ndarray | float,
    vdoth: np.ndarray | float,
    roughness: float,
    f0: np.ndarray | float,
) -> np.ndarray:
    """Evaluate the Cook-Torrance microfacet specular BRDF."""
    v = _clamp01(ndotv)
    l = _clamp01(ndotl)
    h = _clamp01(ndoth)
    vh = _clamp01(vdoth)
    d = ggx_distribution(h, roughness)
    g = smith_geometry(v, l, roughness)
    f = fresnel_schlick(vh, f0)
    denominator = np.maximum(4.0 * v * l, _EPS)
    return d * g * f / denominator
