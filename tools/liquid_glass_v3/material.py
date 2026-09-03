from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .surface import SurfaceMaps


@dataclass(frozen=True)
class MaterialParams:
    ior: float = 1.50

    # Static PNG transmission. Core stays clear; optical identity is carried by
    # broad front/back interface response and thickness, not a frosted fill.
    container_core_alpha: float = 0.014
    container_body_alpha: float = 0.026
    container_front_interface_alpha: float = 0.060
    container_back_interface_alpha: float = 0.042

    # Glyph is a denser secondary volume, but still transmits wallpaper.
    glyph_core_alpha: float = 0.255
    glyph_mass_alpha: float = 0.060
    glyph_front_interface_alpha: float = 0.115
    glyph_back_interface_alpha: float = 0.082
    glyph_thin_boost: float = 0.060

    front_bright_gain: float = 0.22
    front_dark_gain: float = 0.27
    back_bright_gain: float = 0.13
    back_dark_gain: float = 0.16
    internal_interface_gain: float = 0.050
    specular_gain: float = 0.080
    curvature_gain: float = 0.030


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


def _directional_response(normals: np.ndarray, lx: float, ly: float, *, invert: bool = False):
    q = normals[..., 0] * lx + normals[..., 1] * ly
    if invert:
        q = -q
    q = np.clip(q, -1.0, 1.0)
    broad_light = 0.5 + 0.5 * q
    broad_dark = 1.0 - broad_light
    bright = _smoothstep(0.025, 0.30, q)
    dark = _smoothstep(0.025, 0.30, -q)
    return q, broad_light, broad_dark, bright, dark


def bake_static_rgba(
    maps: SurfaceMaps,
    params: MaterialParams = MaterialParams(),
    flags: BakeFlags = BakeFlags(),
) -> np.ndarray:
    """Bake a wallpaper-independent V3 static optical surrogate.

    This path deliberately uses TWO geometric interfaces. The front crown and
    the variable-thickness back surface have independent normals/slopes, so the
    resulting PNG can encode a paired light/dark optical transition without
    falling back to concentric alpha rims.
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

    # Broad geometric zones. These occupy significant area and survive removal
    # of explicit rim/specular layers.
    front_edge = np.clip((1.0 - cprof) * cm, 0.0, 1.0)
    back_edge = np.clip((1.0 - cbprof) * cm, 0.0, 1.0)
    glyph_front_edge = np.clip((1.0 - gprof) * gm, 0.0, 1.0)
    glyph_back_edge = np.clip((1.0 - gbprof) * gm, 0.0, 1.0)

    curved_front = np.power(front_edge, 0.66).astype(np.float32)
    curved_back = np.power(back_edge, 0.72).astype(np.float32)
    glyph_curved_front = np.power(glyph_front_edge, 0.66).astype(np.float32)
    glyph_curved_back = np.power(glyph_back_edge, 0.72).astype(np.float32)

    front_interface = np.clip(0.84 * cfs + 0.16 * curved_front, 0.0, 1.0)
    back_interface = np.clip(0.82 * cbs + 0.18 * curved_back, 0.0, 1.0)
    glyph_front_interface = np.clip(0.82 * gfs + 0.18 * glyph_curved_front, 0.0, 1.0)
    glyph_back_interface = np.clip(0.80 * gbs + 0.20 * glyph_curved_back, 0.0, 1.0)

    thin = (1.0 - _smoothstep(3.0, 14.0, maps.local_radius)) * gm

    # One neutral virtual environment. The back interface uses reversed XY
    # orientation so the pair reads as an actual slab transition, not two
    # coincident outlines.
    lx, ly = -0.58, -0.82
    lnorm = max((lx * lx + ly * ly) ** 0.5, 1e-6)
    lx, ly = lx / lnorm, ly / lnorm

    qf, f_light, f_dark, f_bright, f_dim = _directional_response(nf, lx, ly)
    qb, b_light, b_dark, b_bright, b_dim = _directional_response(nb, lx, ly, invert=True)

    # Thickness is now a real independent map. Use it as optical mass, but keep
    # the center transparent enough for wallpaper identity to dominate.
    tmax = max(float(np.percentile(maps.thickness[cm > 0.5], 99.0)) if np.any(cm > 0.5) else 1.0, 1e-6)
    tnorm = np.clip(maps.thickness / tmax, 0.0, 1.0)
    mass = np.sqrt(tnorm).astype(np.float32) * cm

    # Weak secondary internal bands generated from the two different profiles.
    internal = np.clip(np.abs(cprof - cbprof) * 2.4, 0.0, 1.0) * cm
    glyph_internal = np.clip(np.abs(gprof - gbprof) * 2.8, 0.0, 1.0) * gm

    # --------------------------- Alpha / transmission -----------------------
    alpha = params.container_core_alpha * cm
    alpha += params.container_body_alpha * mass
    alpha += 0.022 * curved_front + 0.016 * curved_back
    alpha += params.container_front_interface_alpha * front_interface
    alpha += params.container_back_interface_alpha * back_interface
    alpha += 0.016 * internal

    glyph_body = gm * (0.60 + 0.40 * gprof)
    glyph_mass = gm * np.clip(0.52 * gprof + 0.48 * gbprof, 0.0, 1.0)
    alpha += params.glyph_core_alpha * glyph_body
    alpha += params.glyph_mass_alpha * glyph_mass
    alpha += 0.025 * glyph_curved_front + 0.020 * glyph_curved_back
    alpha += params.glyph_front_interface_alpha * glyph_front_interface
    alpha += params.glyph_back_interface_alpha * glyph_back_interface
    alpha += params.glyph_thin_boost * thin
    alpha += 0.020 * glyph_internal

    if flags.explicit_rim:
        # Tiny hairline only. Turning it off must not collapse the form.
        tight_front = _smoothstep(0.955, 0.998, front_edge) * cm
        tight_glyph = _smoothstep(0.948, 0.998, glyph_front_edge) * gm
        alpha += 0.008 * tight_front + 0.010 * tight_glyph

    alpha = np.clip(alpha, 0.0, 0.68)

    # ----------------------------- Neutral luminance ------------------------
    # Container body is deliberately mid-neutral so it creates both positive
    # contrast on dark wallpaper and negative contrast on bright wallpaper.
    luma = 150.0 + 10.0 * mass
    luma += 21.0 * curved_front * f_light - 24.0 * curved_front * f_dark
    luma += 12.0 * curved_back * b_light - 14.0 * curved_back * b_dark
    luma += 255.0 * params.curvature_gain * (0.72 * curv + 0.28 * back_curv)

    # Paired front/back interfaces. The secondary interface is lower-energy and
    # spatially different because it comes from the back surface itself.
    luma += 118.0 * params.front_bright_gain * front_interface * f_bright
    luma -= 116.0 * params.front_dark_gain * front_interface * f_dim
    luma += 108.0 * params.back_bright_gain * back_interface * b_bright
    luma -= 110.0 * params.back_dark_gain * back_interface * b_dim
    luma += 44.0 * params.internal_interface_gain * internal * np.abs(qf - qb)

    # Glyph body: denser and optically separated, but not a white SVG. A mid
    # neutral base deliberately survives both near-black and near-white hosts.
    radius_mass = np.clip(maps.local_radius / 22.0, 0.0, 1.0)
    glyph_luma = 184.0 + 14.0 * gprof + 12.0 * gbprof + 12.0 * radius_mass
    glyph_luma += 24.0 * f_light - 30.0 * f_dark
    glyph_luma += 12.0 * b_light - 16.0 * b_dark
    glyph_luma += 12.0 * glyph_internal

    glyph_mix = np.clip(gm * (0.80 + 0.14 * gprof), 0.0, 0.94)
    luma = luma * (1.0 - glyph_mix) + glyph_luma * glyph_mix

    luma += 70.0 * glyph_front_interface * f_bright
    luma -= 84.0 * glyph_front_interface * f_dim
    luma += 42.0 * glyph_back_interface * b_bright
    luma -= 50.0 * glyph_back_interface * b_dim

    # Restrained specular comes LAST. The no-specular test must retain volume.
    if flags.specular:
        l3 = np.array([-0.45, -0.72, 0.53], dtype=np.float32)
        l3 /= max(float(np.linalg.norm(l3)), 1e-6)
        h = l3 + np.array([0.0, 0.0, 1.0], dtype=np.float32)
        h /= max(float(np.linalg.norm(h)), 1e-6)

        ndoth = np.clip(nf[..., 0] * h[0] + nf[..., 1] * h[1] + nf[..., 2] * h[2], 0.0, 1.0)
        ndotv = np.clip(nf[..., 2], 0.0, 1.0)
        fresnel = schlick_fresnel(ndotv, params.ior)
        surface_weight = np.clip(0.52 * cfs + 0.22 * cbs + 0.82 * gfs + 0.34 * gbs, 0.0, 1.0)
        spec = np.power(ndoth, 44.0) * (0.16 + 0.84 * fresnel) * surface_weight
        luma += 255.0 * params.specular_gain * spec
        alpha += 0.012 * spec

    # Deliberately no baked drop shadow. V3 depth must come from the object.
    if flags.shadow:
        pass

    luma = np.clip(luma, 42.0, 242.0)
    rgb = np.repeat(luma[..., None], 3, axis=2)
    rgb = np.where(cm[..., None] > 1e-4, rgb, 128.0)
    rgba = np.concatenate((rgb, (np.clip(alpha, 0.0, 1.0) * 255.0)[..., None]), axis=2)
    return np.clip(rgba, 0.0, 255.0).astype(np.uint8)
