from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .surface import SurfaceMaps


@dataclass(frozen=True)
class MaterialParams:
    ior: float = 1.50

    container_core_alpha: float = 0.010
    container_body_alpha: float = 0.018
    container_front_interface_alpha: float = 0.072
    container_back_interface_alpha: float = 0.052

    glyph_core_alpha: float = 0.178
    glyph_mass_alpha: float = 0.088
    glyph_front_interface_alpha: float = 0.132
    glyph_back_interface_alpha: float = 0.098
    glyph_thin_boost: float = 0.060

    front_bright_gain: float = 0.24
    front_dark_gain: float = 0.30
    back_bright_gain: float = 0.16
    back_dark_gain: float = 0.19
    internal_interface_gain: float = 0.060
    specular_gain: float = 0.070
    curvature_gain: float = 0.025


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


def _sample_scalar(a: np.ndarray, dx: np.ndarray, dy: np.ndarray) -> np.ndarray:
    """Bilinearly move an interface in screen space without blurring it."""
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
        a[y0, x0] * (1.0 - wx) * (1.0 - wy)
        + a[y0, x1] * wx * (1.0 - wy)
        + a[y1, x0] * (1.0 - wx) * wy
        + a[y1, x1] * wx * wy
    ).astype(np.float32)


def schlick_fresnel(ndotv: np.ndarray, ior: float) -> np.ndarray:
    f0 = ((ior - 1.0) / (ior + 1.0)) ** 2
    return (f0 + (1.0 - f0) * np.power(1.0 - np.clip(ndotv, 0.0, 1.0), 5.0)).astype(np.float32)


def _directional_response(normals: np.ndarray, lx: float, ly: float, *, invert: bool = False):
    q = normals[..., 0] * lx + normals[..., 1] * ly
    if invert:
        q = -q
    q = np.clip(q, -1.0, 1.0)
    broad_light = 0.5 + 0.5 * q
    broad_dark = 1.0 - broad_light
    bright = _smoothstep(0.020, 0.28, q)
    dark = _smoothstep(0.020, 0.28, -q)
    return q, broad_light, broad_dark, bright, dark


def bake_static_rgba(
    maps: SurfaceMaps,
    params: MaterialParams = MaterialParams(),
    flags: BakeFlags = BakeFlags(),
) -> np.ndarray:
    """Bake a wallpaper-independent V3 optical surrogate.

    V3.1 makes front/back interfaces spatially distinct. The secondary surface
    is displaced along its own projected normal by an amount derived from real
    thickness, so the result reads as a slab/lens instead of a diffuse emboss.
    """
    cm = np.clip(maps.container_mask, 0.0, 1.0)
    gm = np.clip(maps.glyph_mask, 0.0, 1.0)
    cprof = np.clip(maps.container_profile, 0.0, 1.0)
    cbprof = np.clip(maps.container_back_profile, 0.0, 1.0)
    gprof = np.clip(maps.glyph_profile, 0.0, 1.0)
    gbprof = np.clip(maps.glyph_back_profile, 0.0, 1.0)

    nf = maps.front_normals
    nb = maps.back_normals

    cfs = _norm01(maps.container_slope)
    cbs = _norm01(maps.container_back_slope)
    gfs = _norm01(maps.glyph_slope)
    gbs = _norm01(maps.glyph_back_slope)
    curv = _norm01(maps.curvature)
    back_curv = _norm01(maps.back_curvature)

    front_edge = np.clip((1.0 - cprof) * cm, 0.0, 1.0)
    back_edge = np.clip((1.0 - cbprof) * cm, 0.0, 1.0)
    glyph_front_edge = np.clip((1.0 - gprof) * gm, 0.0, 1.0)
    glyph_back_edge = np.clip((1.0 - gbprof) * gm, 0.0, 1.0)

    curved_front = np.power(front_edge, 0.70).astype(np.float32)
    curved_back = np.power(back_edge, 0.76).astype(np.float32)
    glyph_curved_front = np.power(glyph_front_edge, 0.68).astype(np.float32)
    glyph_curved_back = np.power(glyph_back_edge, 0.74).astype(np.float32)

    front_interface = np.clip(0.88 * cfs + 0.12 * curved_front, 0.0, 1.0)
    back_interface_raw = np.clip(0.86 * cbs + 0.14 * curved_back, 0.0, 1.0)
    glyph_front_interface = np.clip(0.86 * gfs + 0.14 * glyph_curved_front, 0.0, 1.0)
    glyph_back_interface_raw = np.clip(0.84 * gbs + 0.16 * glyph_curved_back, 0.0, 1.0)

    tvals = maps.thickness[cm > 0.5]
    tmax = max(float(np.percentile(tvals, 99.0)) if tvals.size else 1.0, 1e-6)
    tnorm = np.clip(maps.thickness / tmax, 0.0, 1.0)
    mass = np.sqrt(tnorm).astype(np.float32) * cm

    # Real parallax between front/back surfaces. At SIZE=640 this moves the
    # secondary interface by roughly 2..7 px, then naturally scales with icon
    # resolution because shift_scale depends on image size.
    size = float(min(cm.shape))
    shift_scale = size * (0.0030 + 0.0075 * tnorm)
    back_dx = nb[..., 0] * shift_scale
    back_dy = nb[..., 1] * shift_scale
    back_interface = _sample_scalar(back_interface_raw, back_dx, back_dy) * cm

    glyph_shift = size * (0.0040 + 0.0100 * tnorm)
    glyph_back_interface = _sample_scalar(
        glyph_back_interface_raw,
        nb[..., 0] * glyph_shift,
        nb[..., 1] * glyph_shift,
    ) * gm

    # A low-frequency displaced back-body cue gives thickness inside the edge,
    # not just exactly on the silhouette.
    back_body = _sample_scalar(curved_back, back_dx * 0.70, back_dy * 0.70) * cm
    glyph_back_body = _sample_scalar(glyph_curved_back, nb[..., 0] * glyph_shift * 0.72, nb[..., 1] * glyph_shift * 0.72) * gm

    radius_mass = np.clip(maps.local_radius / 24.0, 0.0, 1.0)
    thin = (1.0 - _smoothstep(3.0, 14.0, maps.local_radius)) * gm

    lx, ly = -0.58, -0.82
    lnorm = max((lx * lx + ly * ly) ** 0.5, 1e-6)
    lx, ly = lx / lnorm, ly / lnorm

    qf, f_light, f_dark, f_bright, f_dim = _directional_response(nf, lx, ly)
    qb, b_light, b_dark, b_bright, b_dim = _directional_response(nb, lx, ly, invert=True)

    internal = np.clip(np.abs(cprof - cbprof) * 2.4, 0.0, 1.0) * cm
    glyph_internal = np.clip(np.abs(gprof - gbprof) * 2.8, 0.0, 1.0) * gm

    # --------------------------- Alpha / transmission -----------------------
    alpha = params.container_core_alpha * cm
    alpha += params.container_body_alpha * mass
    alpha += 0.012 * curved_front + 0.010 * back_body
    alpha += params.container_front_interface_alpha * front_interface
    alpha += params.container_back_interface_alpha * back_interface
    alpha += 0.010 * internal

    # Thick glyph regions deliberately keep a transparent core. Recognition
    # comes from optical mass + front/back parallax, not from a pale decal.
    glyph_body = gm * (0.34 + 0.16 * gprof + 0.10 * (1.0 - radius_mass))
    glyph_mass = gm * (0.24 + 0.76 * radius_mass) * np.clip(0.44 * gprof + 0.56 * gbprof, 0.0, 1.0)
    alpha += params.glyph_core_alpha * glyph_body
    alpha += params.glyph_mass_alpha * glyph_mass
    alpha += 0.012 * glyph_curved_front + 0.012 * glyph_back_body
    alpha += params.glyph_front_interface_alpha * glyph_front_interface
    alpha += params.glyph_back_interface_alpha * glyph_back_interface
    alpha += params.glyph_thin_boost * thin
    alpha += 0.012 * glyph_internal

    if flags.explicit_rim:
        # Merely an anti-disappearance hairline. It is intentionally tiny.
        alpha += 0.004 * _smoothstep(0.965, 0.998, front_edge) * cm
        alpha += 0.005 * _smoothstep(0.960, 0.998, glyph_front_edge) * gm

    alpha = np.clip(alpha, 0.0, 0.60)

    # ----------------------------- Neutral luminance ------------------------
    # Start close to neutral gray so the same RGBA asset can produce positive
    # and negative contrast on dark/bright wallpapers.
    luma = 146.0 + 8.0 * mass
    luma += 17.0 * curved_front * f_light - 20.0 * curved_front * f_dark
    luma += 10.0 * back_body * b_light - 12.0 * back_body * b_dark
    luma += 255.0 * params.curvature_gain * (0.70 * curv + 0.30 * back_curv)

    luma += 122.0 * params.front_bright_gain * front_interface * f_bright
    luma -= 124.0 * params.front_dark_gain * front_interface * f_dim
    luma += 112.0 * params.back_bright_gain * back_interface * b_bright
    luma -= 116.0 * params.back_dark_gain * back_interface * b_dim
    luma += 46.0 * params.internal_interface_gain * internal * np.abs(qf - qb)

    # Glyph body is darker/more neutral than previous builds so it never reads
    # as an opaque white Octocat, while its paired interfaces stay high energy.
    glyph_luma = 158.0 + 9.0 * gprof + 8.0 * gbprof + 5.0 * radius_mass
    glyph_luma += 18.0 * f_light - 24.0 * f_dark
    glyph_luma += 9.0 * b_light - 13.0 * b_dark
    glyph_luma += 9.0 * glyph_internal

    glyph_mix = np.clip(gm * (0.66 + 0.14 * gprof), 0.0, 0.82)
    luma = luma * (1.0 - glyph_mix) + glyph_luma * glyph_mix

    luma += 90.0 * glyph_front_interface * f_bright
    luma -= 106.0 * glyph_front_interface * f_dim
    luma += 58.0 * glyph_back_interface * b_bright
    luma -= 70.0 * glyph_back_interface * b_dim

    # Directionally-separated transmission catch: broad enough to survive
    # launcher downsampling, but derived from true back-body geometry.
    luma += 18.0 * glyph_back_body * b_light
    luma -= 18.0 * glyph_back_body * b_dark

    if flags.specular:
        l3 = np.array([-0.45, -0.72, 0.53], dtype=np.float32)
        l3 /= max(float(np.linalg.norm(l3)), 1e-6)
        h = l3 + np.array([0.0, 0.0, 1.0], dtype=np.float32)
        h /= max(float(np.linalg.norm(h)), 1e-6)
        ndoth = np.clip(nf[..., 0] * h[0] + nf[..., 1] * h[1] + nf[..., 2] * h[2], 0.0, 1.0)
        ndotv = np.clip(nf[..., 2], 0.0, 1.0)
        fresnel = schlick_fresnel(ndotv, params.ior)
        surface_weight = np.clip(0.48 * cfs + 0.20 * cbs + 0.78 * gfs + 0.32 * gbs, 0.0, 1.0)
        spec = np.power(ndoth, 46.0) * (0.14 + 0.86 * fresnel) * surface_weight
        luma += 255.0 * params.specular_gain * spec
        alpha += 0.009 * spec

    # No baked shadow; depth has to survive without it.
    if flags.shadow:
        pass

    luma = np.clip(luma, 34.0, 236.0)
    rgb = np.repeat(luma[..., None], 3, axis=2)
    rgb = np.where(cm[..., None] > 1e-4, rgb, 128.0)
    rgba = np.concatenate((rgb, (np.clip(alpha, 0.0, 1.0) * 255.0)[..., None]), axis=2)
    return np.clip(rgba, 0.0, 255.0).astype(np.uint8)
