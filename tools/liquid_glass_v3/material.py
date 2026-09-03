from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .surface import SurfaceMaps


@dataclass(frozen=True)
class MaterialParams:
    ior: float = 1.50
    container_core_alpha: float = 0.020
    container_edge_alpha: float = 0.145
    container_interface_alpha: float = 0.115
    glyph_core_alpha: float = 0.235
    glyph_edge_alpha: float = 0.185
    glyph_thin_boost: float = 0.105
    bright_interface_gain: float = 0.34
    dark_interface_gain: float = 0.30
    internal_interface_gain: float = 0.12
    specular_gain: float = 0.16
    curvature_gain: float = 0.10


@dataclass(frozen=True)
class BakeFlags:
    specular: bool = True
    shadow: bool = True
    explicit_rim: bool = True


def _smoothstep(a: float, b: float, x: np.ndarray) -> np.ndarray:
    if abs(b - a) < 1e-8:
        return (x >= b).astype(np.float32)
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return (t * t * (3.0 - 2.0 * t)).astype(np.float32)


def _norm01(a: np.ndarray, p: float = 99.5) -> np.ndarray:
    hi = float(np.percentile(np.abs(a), p)) if a.size else 1.0
    if hi <= 1e-8:
        return np.zeros_like(a, dtype=np.float32)
    return np.clip(np.abs(a) / hi, 0.0, 1.0).astype(np.float32)


def schlick_fresnel(ndotv: np.ndarray, ior: float) -> np.ndarray:
    f0 = ((ior - 1.0) / (ior + 1.0)) ** 2
    return (f0 + (1.0 - f0) * np.power(1.0 - np.clip(ndotv, 0.0, 1.0), 5.0)).astype(np.float32)


def bake_static_rgba(
    maps: SurfaceMaps,
    params: MaterialParams = MaterialParams(),
    flags: BakeFlags = BakeFlags(),
) -> np.ndarray:
    """Bake wallpaper-independent straight-alpha RGBA from geometric fields.

    The glass identity is encoded by broad geometric interfaces and a denser
    secondary glyph volume. Specular/shadow are intentionally non-essential.
    """
    cm = np.clip(maps.container_mask, 0.0, 1.0)
    gm = np.clip(maps.glyph_mask, 0.0, 1.0)
    cprof = np.clip(maps.container_profile, 0.0, 1.0)
    gprof = np.clip(maps.glyph_profile, 0.0, 1.0)
    n = maps.normals

    slope = _norm01(maps.slope)
    curv = _norm01(maps.curvature)

    # Geometric edge is a region, not an outline.
    edge_zone = np.clip((1.0 - cprof) * cm, 0.0, 1.0)
    glyph_edge_zone = np.clip((1.0 - gprof) * gm, 0.0, 1.0)

    # Local thickness compensation: thin strokes need stronger interfaces,
    # broad glyph regions preserve more transparent optical mass.
    thin = 1.0 - _smoothstep(3.0, 14.0, maps.local_radius)
    thin *= gm

    # Directional dual-polarity interface derived from the actual surface.
    lx, ly = -0.58, -0.82
    lnorm = max((lx * lx + ly * ly) ** 0.5, 1e-6)
    lx, ly = lx / lnorm, ly / lnorm
    q = n[..., 0] * lx + n[..., 1] * ly
    bright_dir = _smoothstep(0.03, 0.35, q)
    dark_dir = _smoothstep(0.03, 0.35, -q)

    # Broad interfaces. Narrow rim is optional and never carries the volume.
    broad_interface = np.clip(0.62 * slope + 0.38 * edge_zone, 0.0, 1.0)
    glyph_interface = np.clip(0.50 * slope * gm + 0.50 * glyph_edge_zone, 0.0, 1.0)

    # Secondary interface sits slightly inward from the physical edge.
    inner_band = np.clip(_smoothstep(0.20, 0.68, 1.0 - cprof) - _smoothstep(0.70, 0.94, 1.0 - cprof), 0.0, 1.0) * cm
    glyph_inner = np.clip(_smoothstep(0.20, 0.70, 1.0 - gprof) - _smoothstep(0.72, 0.96, 1.0 - gprof), 0.0, 1.0) * gm

    # Base alpha topology. Container core remains very clear; glyph is a
    # visibly denser but still translucent glass volume.
    alpha = params.container_core_alpha * cm
    alpha += params.container_edge_alpha * broad_interface
    alpha += params.container_interface_alpha * inner_band

    glyph_body = gm * (0.52 + 0.48 * gprof)
    alpha += params.glyph_core_alpha * glyph_body
    alpha += params.glyph_edge_alpha * glyph_interface
    alpha += params.glyph_thin_boost * thin

    if flags.explicit_rim:
        tight_rim = _smoothstep(0.82, 0.985, edge_zone) * cm
        glyph_tight = _smoothstep(0.78, 0.985, glyph_edge_zone) * gm
        alpha += 0.055 * tight_rim + 0.065 * glyph_tight

    alpha = np.clip(alpha, 0.0, 0.78)

    # Neutral RGB response. Bright and dark cues coexist spatially, allowing
    # the same PNG to survive both dark and bright wallpapers.
    base = 170.0 + 20.0 * np.clip(maps.thickness / max(float(np.max(maps.thickness)), 1e-6), 0.0, 1.0)
    base += params.curvature_gain * 255.0 * curv

    bright = params.bright_interface_gain * (broad_interface * bright_dir + 1.18 * glyph_interface * bright_dir)
    dark = params.dark_interface_gain * (broad_interface * dark_dir + 1.14 * glyph_interface * dark_dir)
    internal = params.internal_interface_gain * (inner_band + 1.20 * glyph_inner)

    luma = base + 165.0 * bright + 80.0 * internal - 155.0 * dark

    # Specular is deliberately a small final term. Turning it off must leave
    # a complete geometric material.
    if flags.specular:
        vx, vy, vz = 0.0, 0.0, 1.0
        l3 = np.array([-0.45, -0.72, 0.53], dtype=np.float32)
        l3 /= max(float(np.linalg.norm(l3)), 1e-6)
        h = l3 + np.array([vx, vy, vz], dtype=np.float32)
        h /= max(float(np.linalg.norm(h)), 1e-6)
        ndoth = np.clip(n[..., 0] * h[0] + n[..., 1] * h[1] + n[..., 2] * h[2], 0.0, 1.0)
        ndotv = np.clip(n[..., 2], 0.0, 1.0)
        fresnel = schlick_fresnel(ndotv, params.ior)
        spec = np.power(ndoth, 34.0) * (0.25 + 0.75 * fresnel) * slope
        luma += 255.0 * params.specular_gain * spec
        alpha += 0.035 * spec

    # No external drop shadow in the V3 production asset. The shadow flag is
    # kept for acceptance parity and future low-frequency packaging tests.
    if flags.shadow:
        pass

    luma = np.clip(luma, 44.0, 248.0)
    rgb = np.repeat(luma[..., None], 3, axis=2)

    # Ensure transparent pixels carry neutral RGB to avoid colored halos.
    rgb = np.where(cm[..., None] > 1e-4, rgb, 128.0)
    rgba = np.concatenate((rgb, (np.clip(alpha, 0.0, 1.0) * 255.0)[..., None]), axis=2)
    return np.clip(rgba, 0.0, 255.0).astype(np.uint8)
