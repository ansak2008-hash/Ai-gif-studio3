"""LEGACY: Alpha-Sobel material renderer. Not used by Phase 3.

Phase 3 (GGX/Cook-Torrance) will be implemented in the NEW module
material_pbr.py. Do NOT extend this file.

Deprecated since: Batch 11.
TODO(batch-11): delete after Phase 3 lands.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import numpy as np

class Material(str, Enum):
    CHROME = "chrome"
    GOLD = "gold"
    PURPLE = "purple"

@dataclass(frozen=True)
class MaterialSpec:
    material: Material = Material.GOLD
    base_color: tuple[float,float,float] = (0.83,0.62,0.18)
    metallic: float = 1.0
    roughness: float = 0.10
    specular: float = 1.0
    fresnel_f0: float = 0.90

_PRESETS = {
    Material.CHROME: MaterialSpec(Material.CHROME, (0.72,0.76,0.82),1.0,0.07,1.0,0.92),
    Material.GOLD: MaterialSpec(Material.GOLD, (0.83,0.62,0.18),1.0,0.10,1.0,0.88),
    Material.PURPLE: MaterialSpec(Material.PURPLE, (0.34,0.16,0.48),1.0,0.12,1.0,0.86),
}

def material_preset(material: Material) -> MaterialSpec:
    return _PRESETS[material]

def normals_from_alpha(alpha: np.ndarray) -> np.ndarray:
    a = np.clip(np.asarray(alpha,dtype=np.float32),0,1)
    gx = np.gradient(a, axis=1)
    gy = np.gradient(a, axis=0)
    scale = max(float(np.percentile(np.abs(np.concatenate([gx.ravel(),gy.ravel()])),95)), 1e-3)
    nx, ny = -gx/scale, -gy/scale
    nz = np.sqrt(np.clip(1.0-nx*nx-ny*ny,0,1))
    return np.stack([nx,ny,nz],axis=-1).astype(np.float32)

def shade_metallic(rgb_linear: np.ndarray, alpha: np.ndarray, spec: MaterialSpec,
                   light_dir: tuple[float,float,float]=(0.25,-0.35,0.90),
                   view_dir: tuple[float,float,float]=(0.0,0.0,1.0)) -> np.ndarray:
    rgb = np.asarray(rgb_linear,dtype=np.float32)
    a = np.clip(np.asarray(alpha,dtype=np.float32),0,1)
    n = normals_from_alpha(a)
    l = np.asarray(light_dir,dtype=np.float32); l /= max(np.linalg.norm(l),1e-8)
    v = np.asarray(view_dir,dtype=np.float32); v /= max(np.linalg.norm(v),1e-8)
    ndotl = np.clip(n @ l,0,1)
    h = l + v; h /= max(np.linalg.norm(h),1e-8)
    ndoth = np.clip(n @ h,0,1)
    shininess = max(2.0, (1.0-spec.roughness)**4 * 2048.0)
    fresnel = spec.fresnel_f0 + (1.0-spec.fresnel_f0)*(1.0-np.clip(n[...,2],0,1))**5
    specular = (ndoth ** shininess) * spec.specular * fresnel
    base = np.asarray(spec.base_color,dtype=np.float32)
    lit = rgb * (0.18 + 0.82*ndotl[...,None]) * (1.0-spec.metallic) + base * spec.metallic
    return np.clip(lit + specular[...,None],0,4) * a[...,None]
