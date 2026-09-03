from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .surface import SurfaceMaps


@dataclass(frozen=True)
class MaterialParams:
    ior: float = 1.50
    container_core_alpha: float = 0.020
    container_body_alpha: float = 0.040
    container_front_interface_alpha: float = 0.155
    container_back_interface_alpha: float = 0.105
    glyph_core_alpha: float = 0.285
    glyph_mass_alpha: float = 0.135
    glyph_front_interface_alpha: float = 0.190
    glyph_back_interface_alpha: float = 0.145
    glyph_thin_boost: float = 0.070
    specular_gain: float = 0.075


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
    """V3.3: strong but still neutral static optical material.

    This build deliberately leaves the weak alpha-sketch regime. The image must
    read as a substantial glass object at 64-96 px before we spend more time on
    tiny physical refinements.
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

    front_i = np.clip(0.84 * cfs + 0.16 * np.power(ce, 0.68), 0.0, 1.0)
    back_raw = np.clip(0.80 * cbs + 0.20 * np.power(cbe, 0.72), 0.0, 1.0)
    glyph_front_i = np.clip(0.82 * gfs + 0.18 * np.power(ge, 0.66), 0.0, 1.0)
    glyph_back_raw = np.clip(0.78 * gbs + 0.22 * np.power(gbe, 0.70), 0.0, 1.0)

    cnx, cny = _grad(maps.container_sdf)
    gnx, gny = _grad(maps.glyph_sdf)
    tvals = maps.thickness[cm > 0.5]
    tmax = max(float(np.percentile(tvals, 99.0)) if tvals.size else 1.0, 1e-6)
    tnorm = np.clip(maps.thickness / tmax, 0.0, 1.0)
    size = float(min(cm.shape))

    # Deliberately visible front/back separation: 5-16 px at the 640 master,
    # which becomes about 1-2 px in launcher output after downsampling.
    cshift = size * (0.009 + 0.018 * (1.0 - cprof)) * (0.62 + 0.38 * tnorm)
    gshift = size * (0.011 + 0.023 * (1.0 - gprof)) * (0.58 + 0.42 * tnorm)
    back_i = _sample_scalar(back_raw, cnx * cshift, cny * cshift) * cm
    glyph_back_i = _sample_scalar(glyph_back_raw, gnx * gshift, gny * gshift) * gm
    back_body = _sample_scalar(np.power(cbe, 0.72), cnx * cshift * 0.64, cny * cshift * 0.64) * cm
    glyph_back_body = _sample_scalar(np.power(gbe, 0.70), gnx * gshift * 0.62, gny * gshift * 0.62) * gm

    mass = np.sqrt(tnorm) * cm
    radius = np.clip(maps.local_radius / 24.0, 0.0, 1.0)
    thin = (1.0 - _smoothstep(3.0, 14.0, maps.local_radius)) * gm

    # Fixed neutral studio environment. Unlike a hand-drawn highlight this is
    # evaluated continuously from the curved surface normal.
    lx, ly = -0.60, -0.80
    q = np.clip(nf[..., 0] * lx + nf[..., 1] * ly, -1.0, 1.0)
    bright = _smoothstep(0.00, 0.23, q)
    dark = _smoothstep(0.00, 0.23, -q)
    broad = 0.5 + 0.5 * q
    horizon = np.exp(-np.square((q - 0.06) / 0.19)).astype(np.float32) * np.clip(0.30 + 0.70 * cfs, 0.0, 1.0)

    # Stronger optical density, but center still leaves wallpaper visible.
    alpha = params.container_core_alpha * cm + params.container_body_alpha * mass
    alpha += 0.020 * np.power(ce, 0.68) + 0.023 * back_body
    alpha += params.container_front_interface_alpha * front_i
    alpha += params.container_back_interface_alpha * back_i

    glyph_body = gm * (0.40 + 0.18 * gprof + 0.08 * (1.0 - radius))
    glyph_mass = gm * (0.25 + 0.75 * radius) * np.clip(0.42 * gprof + 0.58 * gbprof, 0.0, 1.0)
    alpha += params.glyph_core_alpha * glyph_body + params.glyph_mass_alpha * glyph_mass
    alpha += 0.020 * np.power(ge, 0.68) + 0.024 * glyph_back_body
    alpha += params.glyph_front_interface_alpha * glyph_front_i
    alpha += params.glyph_back_interface_alpha * glyph_back_i
    alpha += params.glyph_thin_boost * thin

    if flags.explicit_rim:
        alpha += 0.004 * _smoothstep(0.970, 0.999, ce) * cm
        alpha += 0.005 * _smoothstep(0.966, 0.999, ge) * gm
    alpha = np.clip(alpha, 0.0, 0.76)

    # Neutral transmission body with visibly separate optical interfaces.
    luma = 150.0 + 12.0 * mass
    luma += (28.0 * broad - 13.0) * np.power(ce, 0.68)
    luma += (18.0 * (1.0 - broad) - 9.0) * back_body
    luma += 72.0 * front_i * bright - 78.0 * front_i * dark
    luma += 50.0 * back_i * dark - 58.0 * back_i * bright
    luma += 27.0 * horizon

    # The glyph is a denser second piece of glass. Keep the body neutral rather
    # than white, then make its two interfaces do most of the recognition work.
    glyph_luma = 166.0 + 13.0 * gprof + 9.0 * gbprof + 6.0 * radius
    glyph_luma += 20.0 * broad - 9.0
    glyph_mix = np.clip(gm * (0.72 + 0.14 * gprof), 0.0, 0.86)
    luma = luma * (1.0 - glyph_mix) + glyph_luma * glyph_mix
    luma += 94.0 * glyph_front_i * bright - 108.0 * glyph_front_i * dark
    luma += 67.0 * glyph_back_i * dark - 76.0 * glyph_back_i * bright
    luma += 20.0 * glyph_back_body * (1.0 - 2.0 * broad)

    if flags.specular:
        l3 = np.array([-0.45, -0.72, 0.53], dtype=np.float32)
        l3 /= max(float(np.linalg.norm(l3)), 1e-6)
        h = l3 + np.array([0.0, 0.0, 1.0], dtype=np.float32)
        h /= max(float(np.linalg.norm(h)), 1e-6)
        ndoth = np.clip(nf[..., 0] * h[0] + nf[..., 1] * h[1] + nf[..., 2] * h[2], 0.0, 1.0)
        fresnel = schlick_fresnel(np.clip(nf[..., 2], 0.0, 1.0), params.ior)
        spec = np.power(ndoth, 46.0) * (0.12 + 0.88 * fresnel) * np.clip(0.50 * cfs + 0.82 * gfs, 0.0, 1.0)
        luma += 255.0 * params.specular_gain * spec
        alpha += 0.010 * spec

    # No baked drop shadow. The no-shadow gate must remain visually valid.
    luma = np.clip(luma, 26.0, 242.0)
    rgb = np.repeat(luma[..., None], 3, axis=2)
    rgb = np.where(cm[..., None] > 1e-4, rgb, 128.0)
    return np.clip(np.concatenate((rgb, (np.clip(alpha, 0.0, 1.0) * 255.0)[..., None]), axis=2), 0.0, 255.0).astype(np.uint8)
