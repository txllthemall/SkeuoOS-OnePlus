from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .surface import SurfaceMaps


@dataclass(frozen=True)
class MaterialParams:
    ior: float = 1.50
    container_core_alpha: float = 0.008
    container_body_alpha: float = 0.014
    container_front_interface_alpha: float = 0.090
    container_back_interface_alpha: float = 0.065
    glyph_core_alpha: float = 0.165
    glyph_mass_alpha: float = 0.095
    glyph_front_interface_alpha: float = 0.145
    glyph_back_interface_alpha: float = 0.110
    glyph_thin_boost: float = 0.062
    specular_gain: float = 0.060


@dataclass(frozen=True)
class BakeFlags:
    specular: bool = True
    shadow: bool = True
    explicit_rim: bool = True


def _smoothstep(a: float, b: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - a) / max(b - a, 1e-8), 0.0, 1.0)
    return (t * t * (3.0 - 2.0 * t)).astype(np.float32)


def _norm01(a: np.ndarray, p: float = 99.5) -> np.ndarray:
    hi = float(np.percentile(np.abs(a), p)) if a.size else 1.0
    return np.clip(np.abs(a) / max(hi, 1e-8), 0.0, 1.0).astype(np.float32)


def _grad(a: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    gy, gx = np.gradient(a.astype(np.float32))
    mag = np.sqrt(gx * gx + gy * gy)
    return gx / np.maximum(mag, 1e-6), gy / np.maximum(mag, 1e-6)


def _sample_scalar(a: np.ndarray, dx: np.ndarray, dy: np.ndarray) -> np.ndarray:
    h, w = a.shape
    yy, xx = np.indices((h, w), dtype=np.float32)
    sx = np.clip(xx + dx, 0.0, w - 1.001)
    sy = np.clip(yy + dy, 0.0, h - 1.001)
    x0 = np.floor(sx).astype(np.int32)
    y0 = np.floor(sy).astype(np.int32)
    x1 = np.minimum(x0 + 1, w - 1)
    y1 = np.minimum(y0 + 1, h - 1)
    wx = sx - x0
    wy = sy - y0
    return (
        a[y0, x0] * (1 - wx) * (1 - wy)
        + a[y0, x1] * wx * (1 - wy)
        + a[y1, x0] * (1 - wx) * wy
        + a[y1, x1] * wx * wy
    ).astype(np.float32)


def schlick_fresnel(ndotv: np.ndarray, ior: float) -> np.ndarray:
    f0 = ((ior - 1.0) / (ior + 1.0)) ** 2
    return (f0 + (1.0 - f0) * np.power(1.0 - np.clip(ndotv, 0.0, 1.0), 5.0)).astype(np.float32)


def bake_static_rgba(maps: SurfaceMaps, params: MaterialParams = MaterialParams(), flags: BakeFlags = BakeFlags()) -> np.ndarray:
    """Wallpaper-independent static V3.2 material.

    The back interface is now offset along the signed-distance normal, not the
    almost-front-facing height normal. That makes apparent thickness survive
    launcher downsampling and prevents another 'same thing, different rim'
    iteration.
    """
    cm = np.clip(maps.container_mask, 0.0, 1.0)
    gm = np.clip(maps.glyph_mask, 0.0, 1.0)
    cprof = np.clip(maps.container_profile, 0.0, 1.0)
    cbprof = np.clip(maps.container_back_profile, 0.0, 1.0)
    gprof = np.clip(maps.glyph_profile, 0.0, 1.0)
    gbprof = np.clip(maps.glyph_back_profile, 0.0, 1.0)
    nf = maps.front_normals

    cfs = _norm01(maps.container_slope)
    cbs = _norm01(maps.container_back_slope)
    gfs = _norm01(maps.glyph_slope)
    gbs = _norm01(maps.glyph_back_slope)

    ce = np.clip((1.0 - cprof) * cm, 0.0, 1.0)
    cbe = np.clip((1.0 - cbprof) * cm, 0.0, 1.0)
    ge = np.clip((1.0 - gprof) * gm, 0.0, 1.0)
    gbe = np.clip((1.0 - gbprof) * gm, 0.0, 1.0)

    front_i = np.clip(0.88 * cfs + 0.12 * np.power(ce, 0.72), 0.0, 1.0)
    back_raw = np.clip(0.84 * cbs + 0.16 * np.power(cbe, 0.76), 0.0, 1.0)
    glyph_front_i = np.clip(0.86 * gfs + 0.14 * np.power(ge, 0.70), 0.0, 1.0)
    glyph_back_raw = np.clip(0.82 * gbs + 0.18 * np.power(gbe, 0.74), 0.0, 1.0)

    # Screen-space parallax from TRUE silhouette normals.
    cnx, cny = _grad(maps.container_sdf)
    gnx, gny = _grad(maps.glyph_sdf)
    tvals = maps.thickness[cm > 0.5]
    tmax = max(float(np.percentile(tvals, 99.0)) if tvals.size else 1.0, 1e-6)
    tnorm = np.clip(maps.thickness / tmax, 0.0, 1.0)
    size = float(min(cm.shape))

    cshift = size * (0.007 + 0.015 * (1.0 - cprof)) * (0.62 + 0.38 * tnorm)
    gshift = size * (0.009 + 0.019 * (1.0 - gprof)) * (0.58 + 0.42 * tnorm)
    back_i = _sample_scalar(back_raw, cnx * cshift, cny * cshift) * cm
    glyph_back_i = _sample_scalar(glyph_back_raw, gnx * gshift, gny * gshift) * gm

    back_body = _sample_scalar(np.power(cbe, 0.80), cnx * cshift * 0.72, cny * cshift * 0.72) * cm
    glyph_back_body = _sample_scalar(np.power(gbe, 0.78), gnx * gshift * 0.70, gny * gshift * 0.70) * gm

    mass = np.sqrt(tnorm) * cm
    radius = np.clip(maps.local_radius / 24.0, 0.0, 1.0)
    thin = (1.0 - _smoothstep(3.0, 14.0, maps.local_radius)) * gm

    # Neutral studio environment, evaluated from the actual front normals.
    lx, ly = -0.58, -0.82
    q = np.clip(nf[..., 0] * lx + nf[..., 1] * ly, -1.0, 1.0)
    bright = _smoothstep(0.02, 0.26, q)
    dark = _smoothstep(0.02, 0.26, -q)
    broad = 0.5 + 0.5 * q

    # Alpha: clear core + strong geometry-derived interfaces.
    alpha = params.container_core_alpha * cm + params.container_body_alpha * mass
    alpha += 0.010 * np.power(ce, 0.72) + 0.012 * back_body
    alpha += params.container_front_interface_alpha * front_i
    alpha += params.container_back_interface_alpha * back_i

    glyph_body = gm * (0.30 + 0.13 * gprof + 0.08 * (1.0 - radius))
    glyph_mass = gm * (0.22 + 0.78 * radius) * np.clip(0.42 * gprof + 0.58 * gbprof, 0.0, 1.0)
    alpha += params.glyph_core_alpha * glyph_body + params.glyph_mass_alpha * glyph_mass
    alpha += 0.012 * np.power(ge, 0.72) + 0.014 * glyph_back_body
    alpha += params.glyph_front_interface_alpha * glyph_front_i
    alpha += params.glyph_back_interface_alpha * glyph_back_i
    alpha += params.glyph_thin_boost * thin

    if flags.explicit_rim:
        alpha += 0.003 * _smoothstep(0.972, 0.999, ce) * cm
        alpha += 0.004 * _smoothstep(0.968, 0.999, ge) * gm
    alpha = np.clip(alpha, 0.0, 0.60)

    # Luminance: paired positive/negative interfaces produce a glass slab on
    # both bright and dark wallpapers. The two interfaces are spatially
    # separated, so this reads as thickness instead of Photoshop bevel.
    luma = 144.0 + 7.0 * mass
    luma += (17.0 * broad - 8.0) * np.power(ce, 0.72)
    luma += (10.0 * (1.0 - broad) - 7.0) * back_body
    luma += 46.0 * front_i * bright - 52.0 * front_i * dark
    luma += 31.0 * back_i * dark - 38.0 * back_i * bright

    # A broad neutral reflection band across the curved surface. This is based
    # on surface orientation and remains present without specular/rim.
    horizon = np.exp(-np.square((q - 0.08) / 0.21)).astype(np.float32) * cfs
    luma += 18.0 * horizon

    glyph_luma = 154.0 + 8.0 * gprof + 6.0 * gbprof + 4.0 * radius
    glyph_luma += 14.0 * broad - 7.0
    glyph_mix = np.clip(gm * (0.62 + 0.12 * gprof), 0.0, 0.76)
    luma = luma * (1.0 - glyph_mix) + glyph_luma * glyph_mix
    luma += 66.0 * glyph_front_i * bright - 78.0 * glyph_front_i * dark
    luma += 45.0 * glyph_back_i * dark - 53.0 * glyph_back_i * bright
    luma += 14.0 * glyph_back_body * (1.0 - 2.0 * broad)

    if flags.specular:
        l3 = np.array([-0.45, -0.72, 0.53], dtype=np.float32)
        l3 /= max(float(np.linalg.norm(l3)), 1e-6)
        h = l3 + np.array([0.0, 0.0, 1.0], dtype=np.float32)
        h /= max(float(np.linalg.norm(h)), 1e-6)
        ndoth = np.clip(nf[..., 0] * h[0] + nf[..., 1] * h[1] + nf[..., 2] * h[2], 0.0, 1.0)
        fresnel = schlick_fresnel(np.clip(nf[..., 2], 0.0, 1.0), params.ior)
        spec = np.power(ndoth, 48.0) * (0.12 + 0.88 * fresnel) * np.clip(0.45 * cfs + 0.75 * gfs, 0.0, 1.0)
        luma += 255.0 * params.specular_gain * spec
        alpha += 0.008 * spec

    # No baked shadow: geometry must carry the depth.
    luma = np.clip(luma, 30.0, 235.0)
    rgb = np.repeat(luma[..., None], 3, axis=2)
    rgb = np.where(cm[..., None] > 1e-4, rgb, 128.0)
    return np.clip(np.concatenate((rgb, (np.clip(alpha, 0.0, 1.0) * 255.0)[..., None]), axis=2), 0.0, 255.0).astype(np.uint8)
