from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .surface import SurfaceMaps


@dataclass(frozen=True)
class MaterialParams:
    ior: float = 1.50

    # Production PNG must remain transparent, but the shell still has to read
    # as a physical object at 64-96 px. These densities are split across mass
    # and signed front/back interfaces rather than one milky fill.
    container_core_alpha: float = 0.018
    container_mass_alpha: float = 0.034
    container_edge_mass_alpha: float = 0.038
    container_front_interface_alpha: float = 0.145
    container_back_interface_alpha: float = 0.102

    # Apple-like iconography is not invisible glass. The glyph is a distinctly
    # denser secondary dielectric with a translucent body and its own paired
    # interfaces. Run #20 remained too faint at launcher scale, so recognition
    # is restored through optical mass, not a flat white SVG.
    glyph_core_alpha: float = 0.360
    glyph_mass_alpha: float = 0.155
    glyph_front_interface_alpha: float = 0.220
    glyph_back_interface_alpha: float = 0.158
    glyph_thin_boost: float = 0.066

    broad_environment_alpha: float = 0.023
    specular_alpha: float = 0.042


@dataclass(frozen=True)
class BakeFlags:
    specular: bool = True
    shadow: bool = True
    explicit_rim: bool = True


def _smoothstep(a: float, b: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - a) / max(b - a, 1e-8), 0.0, 1.0)
    return (t * t * (3.0 - 2.0 * t)).astype(np.float32)


def _norm01(a: np.ndarray, p: float = 99.5) -> np.ndarray:
    vals = np.abs(a)
    nz = vals[vals > 1e-8]
    hi = float(np.percentile(nz, p)) if nz.size else 1.0
    return np.clip(vals / max(hi, 1e-8), 0.0, 1.0).astype(np.float32)


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


def _over_gray(
    premul: np.ndarray,
    alpha: np.ndarray,
    layer_alpha: np.ndarray,
    gray: float | np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    la = np.clip(layer_alpha.astype(np.float32), 0.0, 0.98)
    g = np.asarray(gray, dtype=np.float32)
    src = la[..., None] * g[..., None] if g.ndim == 2 else la[..., None] * float(g)
    keep = 1.0 - la
    return src + premul * keep[..., None], la + alpha * keep


def bake_static_rgba(
    maps: SurfaceMaps,
    params: MaterialParams = MaterialParams(),
    flags: BakeFlags = BakeFlags(),
) -> np.ndarray:
    """Wallpaper-independent V3 static Liquid Glass surrogate."""
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
    back_raw = np.clip(0.88 * cbs + 0.12 * np.power(cbe, 0.74), 0.0, 1.0)
    glyph_front_i = np.clip(0.86 * gfs + 0.14 * np.power(ge, 0.70), 0.0, 1.0)
    glyph_back_raw = np.clip(0.84 * gbs + 0.16 * np.power(gbe, 0.72), 0.0, 1.0)

    cnx, cny = _grad(maps.container_sdf)
    gnx, gny = _grad(maps.glyph_sdf)
    tvals = maps.thickness[cm > 0.5]
    tmax = max(float(np.percentile(tvals, 99.0)) if tvals.size else 1.0, 1e-6)
    tnorm = np.clip(maps.thickness / tmax, 0.0, 1.0)
    size = float(min(cm.shape))
    cshift = size * (0.0045 + 0.0075 * tnorm) * np.clip(0.35 + 0.65 * (1.0 - cprof), 0.0, 1.0)
    gshift = size * (0.0055 + 0.0090 * tnorm) * np.clip(0.40 + 0.60 * (1.0 - gprof), 0.0, 1.0)
    back_i = _sample_scalar(back_raw, cnx * cshift, cny * cshift) * cm
    glyph_back_i = _sample_scalar(glyph_back_raw, gnx * gshift, gny * gshift) * gm

    mass = np.sqrt(tnorm) * cm
    edge_mass = np.sqrt(np.clip(tnorm * (1.0 - cprof), 0.0, 1.0)) * cm
    radius = np.clip(maps.local_radius / 24.0, 0.0, 1.0)
    thin = (1.0 - _smoothstep(3.0, 14.0, maps.local_radius)) * gm

    lx, ly = -0.60, -0.80
    q = np.clip(nf[..., 0] * lx + nf[..., 1] * ly, -1.0, 1.0)
    bright = _smoothstep(0.015, 0.26, q)
    dark = _smoothstep(0.015, 0.26, -q)
    grazing = np.sqrt(np.clip(cfs, 0.0, 1.0))
    horizon = np.exp(-np.square((q - 0.05) / 0.22)).astype(np.float32) * grazing

    premul = np.zeros((*cm.shape, 1), dtype=np.float32)
    alpha = np.zeros_like(cm, dtype=np.float32)

    # Shell: nearly clear center, denser curved lip, paired signed interfaces.
    premul, alpha = _over_gray(premul, alpha, params.container_core_alpha * cm, 140.0)
    premul, alpha = _over_gray(premul, alpha, params.container_mass_alpha * mass, 134.0)
    premul, alpha = _over_gray(premul, alpha, params.container_edge_mass_alpha * edge_mass, 128.0)
    premul, alpha = _over_gray(premul, alpha, params.broad_environment_alpha * horizon * cm, 228.0)

    premul, alpha = _over_gray(premul, alpha, params.container_back_interface_alpha * back_i * dark, 226.0)
    premul, alpha = _over_gray(premul, alpha, params.container_back_interface_alpha * 0.88 * back_i * bright, 30.0)
    premul, alpha = _over_gray(premul, alpha, params.container_front_interface_alpha * front_i * dark, 22.0)
    premul, alpha = _over_gray(premul, alpha, params.container_front_interface_alpha * 0.96 * front_i * bright, 246.0)

    # Glyph: a second dielectric. Its broad body remains transparent enough to
    # show wallpaper, while the front/rear interfaces give instant silhouette
    # recognition on both light and dark launchers.
    glyph_body = gm * (0.52 + 0.23 * gprof + 0.10 * (1.0 - radius))
    glyph_mass = gm * (0.22 + 0.78 * radius) * np.clip(0.34 * gprof + 0.66 * gbprof, 0.0, 1.0)
    premul, alpha = _over_gray(premul, alpha, params.glyph_core_alpha * glyph_body, 198.0)
    premul, alpha = _over_gray(premul, alpha, params.glyph_mass_alpha * glyph_mass, 176.0)
    premul, alpha = _over_gray(premul, alpha, params.glyph_thin_boost * thin, 202.0)

    premul, alpha = _over_gray(premul, alpha, params.glyph_back_interface_alpha * glyph_back_i * dark, 236.0)
    premul, alpha = _over_gray(premul, alpha, params.glyph_back_interface_alpha * 0.90 * glyph_back_i * bright, 25.0)
    premul, alpha = _over_gray(premul, alpha, params.glyph_front_interface_alpha * glyph_front_i * dark, 18.0)
    premul, alpha = _over_gray(premul, alpha, params.glyph_front_interface_alpha * glyph_front_i * bright, 250.0)

    if flags.explicit_rim:
        rim = _smoothstep(0.985, 0.9995, ce) * cm
        grim = _smoothstep(0.983, 0.9995, ge) * gm
        premul, alpha = _over_gray(premul, alpha, 0.0025 * rim, 230.0)
        premul, alpha = _over_gray(premul, alpha, 0.0030 * grim, 236.0)

    if flags.specular:
        light = np.array([-0.45, -0.72, 0.53], dtype=np.float32)
        light /= max(float(np.linalg.norm(light)), 1e-6)
        halfv = light + np.array([0.0, 0.0, 1.0], dtype=np.float32)
        halfv /= max(float(np.linalg.norm(halfv)), 1e-6)
        ndoth = np.clip(
            nf[..., 0] * halfv[0] + nf[..., 1] * halfv[1] + nf[..., 2] * halfv[2],
            0.0,
            1.0,
        )
        fresnel = schlick_fresnel(np.clip(nf[..., 2], 0.0, 1.0), params.ior)
        surface = np.clip(0.64 * cfs + 0.88 * gfs, 0.0, 1.0)
        sp = np.power(ndoth, 52.0) * (0.10 + 0.90 * fresnel) * surface
        premul, alpha = _over_gray(premul, alpha, params.specular_alpha * sp, 255.0)

    # No external drop shadow: no-shadow is an architectural gate, not a style.
    alpha = np.clip(alpha, 0.0, 0.78)
    rgb = np.divide(
        premul[..., 0],
        np.maximum(alpha, 1e-6),
        out=np.full_like(alpha, 128.0),
        where=alpha > 1e-6,
    )
    rgb = np.where(cm > 1e-4, np.clip(rgb, 8.0, 252.0), 128.0)
    rgba = np.stack((rgb, rgb, rgb, alpha * 255.0), axis=-1)
    return np.clip(rgba, 0.0, 255.0).astype(np.uint8)
