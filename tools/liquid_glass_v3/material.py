from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .surface import SurfaceMaps


@dataclass(frozen=True)
class MaterialParams:
    ior: float = 1.50
    container_core_alpha: float = 0.012
    container_edge_alpha: float = 0.105
    container_interface_alpha: float = 0.060
    glyph_core_alpha: float = 0.345
    glyph_edge_alpha: float = 0.150
    glyph_thin_boost: float = 0.085
    bright_interface_gain: float = 0.24
    dark_interface_gain: float = 0.34
    internal_interface_gain: float = 0.10
    specular_gain: float = 0.12
    curvature_gain: float = 0.055


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
    """Bake wallpaper-independent straight-alpha RGBA from V3 geometry."""
    cm = np.clip(maps.container_mask, 0.0, 1.0)
    gm = np.clip(maps.glyph_mask, 0.0, 1.0)
    cprof = np.clip(maps.container_profile, 0.0, 1.0)
    gprof = np.clip(maps.glyph_profile, 0.0, 1.0)
    n = maps.normals

    container_slope = _norm01(maps.container_slope)
    glyph_slope = _norm01(maps.glyph_slope)
    curv = _norm01(maps.curvature)

    edge_zone = np.clip((1.0 - cprof) * cm, 0.0, 1.0)
    glyph_edge_zone = np.clip((1.0 - gprof) * gm, 0.0, 1.0)

    thin = 1.0 - _smoothstep(3.0, 14.0, maps.local_radius)
    thin *= gm

    lx, ly = -0.58, -0.82
    lnorm = max((lx * lx + ly * ly) ** 0.5, 1e-6)
    lx, ly = lx / lnorm, ly / lnorm
    q = n[..., 0] * lx + n[..., 1] * ly
    bright_dir = _smoothstep(0.025, 0.32, q)
    dark_dir = _smoothstep(0.025, 0.32, -q)

    # Crucially, container and glyph slopes are independent. The raised glyph
    # cannot generate a giant container ring anymore.
    broad_interface = np.clip(0.64 * container_slope + 0.36 * edge_zone, 0.0, 1.0)
    glyph_interface = np.clip(0.58 * glyph_slope + 0.42 * glyph_edge_zone, 0.0, 1.0)

    inner_band = np.clip(_smoothstep(0.18, 0.56, 1.0 - cprof) - _smoothstep(0.64, 0.90, 1.0 - cprof), 0.0, 1.0) * cm
    glyph_inner = np.clip(_smoothstep(0.18, 0.58, 1.0 - gprof) - _smoothstep(0.66, 0.92, 1.0 - gprof), 0.0, 1.0) * gm

    alpha = params.container_core_alpha * cm
    alpha += params.container_edge_alpha * broad_interface
    alpha += params.container_interface_alpha * inner_band

    # Glyph is a denser secondary glass volume, not a hole and not a flat SVG.
    glyph_body = gm * (0.62 + 0.38 * gprof)
    alpha += params.glyph_core_alpha * glyph_body
    alpha += params.glyph_edge_alpha * glyph_interface
    alpha += params.glyph_thin_boost * thin

    if flags.explicit_rim:
        tight_rim = _smoothstep(0.86, 0.992, edge_zone) * cm
        glyph_tight = _smoothstep(0.84, 0.992, glyph_edge_zone) * gm
        alpha += 0.030 * tight_rim + 0.040 * glyph_tight

    alpha = np.clip(alpha, 0.0, 0.74)

    # Container remains nearly colorless. It is visible primarily through
    # broad curved interfaces rather than a white veil.
    tnorm = np.clip(maps.thickness / max(float(np.max(maps.thickness)), 1e-6), 0.0, 1.0)
    container_luma = 156.0 + 14.0 * tnorm + params.curvature_gain * 255.0 * curv

    c_bright = params.bright_interface_gain * broad_interface * bright_dir
    c_dark = params.dark_interface_gain * broad_interface * dark_dir
    c_internal = params.internal_interface_gain * inner_band
    luma = container_luma + 132.0 * c_bright + 54.0 * c_internal - 122.0 * c_dark

    # The glyph gets its own translucent optical mass. The body is brighter
    # than the container, but directional dark/light cues keep it readable on
    # both near-white and near-black wallpapers.
    glyph_luma = 210.0 + 22.0 * gprof + 30.0 * bright_dir - 58.0 * dark_dir
    glyph_luma += 18.0 * glyph_inner + 8.0 * np.clip(maps.local_radius / 22.0, 0.0, 1.0)
    glyph_mix = np.clip(gm * (0.78 + 0.16 * gprof), 0.0, 0.94)
    luma = luma * (1.0 - glyph_mix) + glyph_luma * glyph_mix

    # Extra edge contrast belongs only to the glyph interface, not to the
    # entire container surface.
    luma += 90.0 * glyph_interface * bright_dir
    luma -= 105.0 * glyph_interface * dark_dir

    if flags.specular:
        l3 = np.array([-0.45, -0.72, 0.53], dtype=np.float32)
        l3 /= max(float(np.linalg.norm(l3)), 1e-6)
        h = l3 + np.array([0.0, 0.0, 1.0], dtype=np.float32)
        h /= max(float(np.linalg.norm(h)), 1e-6)
        ndoth = np.clip(n[..., 0] * h[0] + n[..., 1] * h[1] + n[..., 2] * h[2], 0.0, 1.0)
        ndotv = np.clip(n[..., 2], 0.0, 1.0)
        fresnel = schlick_fresnel(ndotv, params.ior)
        surface_weight = np.clip(0.70 * container_slope + 1.05 * glyph_slope, 0.0, 1.0)
        spec = np.power(ndoth, 38.0) * (0.20 + 0.80 * fresnel) * surface_weight
        luma += 255.0 * params.specular_gain * spec
        alpha += 0.022 * spec

    if flags.shadow:
        pass

    luma = np.clip(luma, 50.0, 246.0)
    rgb = np.repeat(luma[..., None], 3, axis=2)
    rgb = np.where(cm[..., None] > 1e-4, rgb, 128.0)
    rgba = np.concatenate((rgb, (np.clip(alpha, 0.0, 1.0) * 255.0)[..., None]), axis=2)
    return np.clip(rgba, 0.0, 255.0).astype(np.uint8)
