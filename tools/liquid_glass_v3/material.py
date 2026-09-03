from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .surface import SurfaceMaps


@dataclass(frozen=True)
class MaterialParams:
    ior: float = 1.50

    # V3.4 is transmission-first. Optical identity comes from paired signed
    # interfaces and the real thickness field, not a broad milky alpha veil.
    container_core_alpha: float = 0.010
    container_mass_alpha: float = 0.018
    container_edge_mass_alpha: float = 0.020
    container_front_interface_alpha: float = 0.072
    container_back_interface_alpha: float = 0.052

    glyph_core_alpha: float = 0.150
    glyph_mass_alpha: float = 0.075
    glyph_front_interface_alpha: float = 0.108
    glyph_back_interface_alpha: float = 0.078
    glyph_thin_boost: float = 0.040

    broad_environment_alpha: float = 0.014
    specular_alpha: float = 0.030


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
    """Composite one neutral optical layer into a premultiplied material.

    Static Android glass has no backdrop sample. Encoding bright and dark
    interfaces as separate premultiplied layers preserves both contrast
    polarities without turning the entire shell into a gray/white card.
    """
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
    """V3.4 wallpaper-independent static Liquid Glass surrogate.

    The previous build proved the 2.5D volume but still looked foggy because a
    large fraction of the broad curved shell shared one medium-bright RGB/alpha
    field. This baker instead encodes the material as a clear transmission body
    plus spatially separated FRONT/BACK light and dark optical interfaces. The
    result is still a single neutral RGBA PNG, but it behaves much more like a
    transparent dielectric when alpha-composited onto arbitrary wallpapers.
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

    # Curved optical zones derived from geometry. These are broad slope fields,
    # not hand-painted outlines.
    ce = np.clip((1.0 - cprof) * cm, 0.0, 1.0)
    cbe = np.clip((1.0 - cbprof) * cm, 0.0, 1.0)
    ge = np.clip((1.0 - gprof) * gm, 0.0, 1.0)
    gbe = np.clip((1.0 - gbprof) * gm, 0.0, 1.0)
    front_i = np.clip(0.88 * cfs + 0.12 * np.power(ce, 0.72), 0.0, 1.0)
    back_raw = np.clip(0.88 * cbs + 0.12 * np.power(cbe, 0.74), 0.0, 1.0)
    glyph_front_i = np.clip(0.86 * gfs + 0.14 * np.power(ge, 0.70), 0.0, 1.0)
    glyph_back_raw = np.clip(0.84 * gbs + 0.16 * np.power(gbe, 0.72), 0.0, 1.0)

    # Move the rear interface inward along the real SDF normal. Separation is
    # thickness-aware and visible after launcher downsampling, but much smaller
    # than the old 5-16 px fake bevel pair.
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

    # One coherent studio direction drives both front and back interface
    # polarity. Rear cues intentionally invert the front response.
    lx, ly = -0.60, -0.80
    q = np.clip(nf[..., 0] * lx + nf[..., 1] * ly, -1.0, 1.0)
    bright = _smoothstep(0.015, 0.26, q)
    dark = _smoothstep(0.015, 0.26, -q)
    grazing = np.sqrt(np.clip(cfs, 0.0, 1.0))
    horizon = np.exp(-np.square((q - 0.05) / 0.22)).astype(np.float32) * grazing

    premul = np.zeros((*cm.shape, 1), dtype=np.float32)
    alpha = np.zeros_like(cm, dtype=np.float32)

    # Clear body. The neutral density is intentionally tiny; wallpaper hue must
    # dominate the perceived colour of the production icon.
    premul, alpha = _over_gray(premul, alpha, params.container_core_alpha * cm, 138.0)
    premul, alpha = _over_gray(premul, alpha, params.container_mass_alpha * mass, 132.0)
    premul, alpha = _over_gray(premul, alpha, params.container_edge_mass_alpha * edge_mass, 128.0)

    # Broad environment-like catch exists even when specular is disabled. It is
    # low-energy and geometry-derived so the no-specular gate still reads glass.
    premul, alpha = _over_gray(
        premul,
        alpha,
        params.broad_environment_alpha * horizon * cm,
        224.0,
    )

    # Rear interface first, then front interface. Bright/dark polarity is
    # encoded simultaneously so a single static PNG survives both white and
    # black wallpapers without runtime adaptation.
    premul, alpha = _over_gray(
        premul,
        alpha,
        params.container_back_interface_alpha * back_i * dark,
        222.0,
    )
    premul, alpha = _over_gray(
        premul,
        alpha,
        params.container_back_interface_alpha * 0.88 * back_i * bright,
        34.0,
    )
    premul, alpha = _over_gray(
        premul,
        alpha,
        params.container_front_interface_alpha * front_i * dark,
        28.0,
    )
    premul, alpha = _over_gray(
        premul,
        alpha,
        params.container_front_interface_alpha * 0.96 * front_i * bright,
        242.0,
    )

    # Secondary volumetric glyph. Its body is denser than the shell, but still
    # translucent; recognizability comes from mass + its own paired interfaces,
    # not from a flat white SVG fill.
    glyph_body = gm * (0.50 + 0.24 * gprof + 0.10 * (1.0 - radius))
    glyph_mass = gm * (0.22 + 0.78 * radius) * np.clip(0.36 * gprof + 0.64 * gbprof, 0.0, 1.0)
    premul, alpha = _over_gray(premul, alpha, params.glyph_core_alpha * glyph_body, 156.0)
    premul, alpha = _over_gray(premul, alpha, params.glyph_mass_alpha * glyph_mass, 148.0)
    premul, alpha = _over_gray(premul, alpha, params.glyph_thin_boost * thin, 164.0)

    premul, alpha = _over_gray(
        premul,
        alpha,
        params.glyph_back_interface_alpha * glyph_back_i * dark,
        229.0,
    )
    premul, alpha = _over_gray(
        premul,
        alpha,
        params.glyph_back_interface_alpha * 0.90 * glyph_back_i * bright,
        29.0,
    )
    premul, alpha = _over_gray(
        premul,
        alpha,
        params.glyph_front_interface_alpha * glyph_front_i * dark,
        24.0,
    )
    premul, alpha = _over_gray(
        premul,
        alpha,
        params.glyph_front_interface_alpha * glyph_front_i * bright,
        246.0,
    )

    if flags.explicit_rim:
        # Hairline is deliberately negligible. Disabling it should not alter the
        # material class; it exists only to keep the exact launcher silhouette
        # stable after aggressive downsampling.
        rim = _smoothstep(0.985, 0.9995, ce) * cm
        grim = _smoothstep(0.983, 0.9995, ge) * gm
        premul, alpha = _over_gray(premul, alpha, 0.0025 * rim, 226.0)
        premul, alpha = _over_gray(premul, alpha, 0.0030 * grim, 232.0)

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

    # No external drop shadow: depth must survive the no-shadow gate unchanged.
    alpha = np.clip(alpha, 0.0, 0.72)
    rgb = np.divide(
        premul[..., 0],
        np.maximum(alpha, 1e-6),
        out=np.full_like(alpha, 128.0),
        where=alpha > 1e-6,
    )
    rgb = np.where(cm > 1e-4, np.clip(rgb, 10.0, 248.0), 128.0)
    rgba = np.stack((rgb, rgb, rgb, alpha * 255.0), axis=-1)
    return np.clip(rgba, 0.0, 255.0).astype(np.uint8)
