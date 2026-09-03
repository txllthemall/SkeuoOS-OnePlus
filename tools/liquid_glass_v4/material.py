from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .surface import SurfaceMaps, smootherstep


@dataclass(frozen=True)
class MaterialParams:
    ior: float = 1.50

    # V4.1 is intentionally much denser than V3/V4.0. The Apple reference is
    # not a nearly invisible alpha plate: the body carries a visible neutral
    # optical response while still transmitting the wallpaper.
    container_core_alpha: float = 0.045
    container_thickness_alpha: float = 0.070
    container_body_response_alpha: float = 0.095
    container_reflection_alpha: float = 0.245
    container_back_alpha: float = 0.165
    container_internal_alpha: float = 0.115

    glyph_core_alpha: float = 0.440
    glyph_mass_alpha: float = 0.165
    glyph_body_response_alpha: float = 0.155
    glyph_reflection_alpha: float = 0.310
    glyph_back_alpha: float = 0.205
    glyph_internal_alpha: float = 0.145
    glyph_thin_boost: float = 0.075

    sharp_specular_alpha: float = 0.145
    glyph_specular_alpha: float = 0.205
    hairline_alpha: float = 0.014


@dataclass(frozen=True)
class BakeFlags:
    specular: bool = True
    shadow: bool = False
    explicit_rim: bool = True


def _norm01(a: np.ndarray, p: float = 99.5) -> np.ndarray:
    vals = np.abs(a)
    nz = vals[vals > 1e-8]
    hi = float(np.percentile(nz, p)) if nz.size else 1.0
    return np.clip(vals / max(hi, 1e-8), 0.0, 1.0).astype(np.float32)


def _over_gray(premul: np.ndarray, alpha: np.ndarray, la: np.ndarray, gray: np.ndarray | float):
    la = np.clip(la.astype(np.float32), 0.0, 0.96)
    g = np.asarray(gray, dtype=np.float32)
    if g.ndim == 0:
        src = la[..., None] * float(g)
    else:
        src = la[..., None] * g[..., None]
    keep = 1.0 - la
    return src + premul * keep[..., None], la + alpha * keep


def _reflection_environment(normal: np.ndarray) -> np.ndarray:
    """Neutral studio room sampled through the reflected view ray.

    The environment is deliberately asymmetric and high dynamic range, similar
    to how a real curved transparent object picks up a large softbox and a dark
    room. Because it is evaluated from the true normal field, it bends around
    the squircle/glyph rather than looking like a pasted gradient.
    """
    nx, ny, nz = normal[..., 0], normal[..., 1], normal[..., 2]
    rx = 2.0 * nz * nx
    ry = 2.0 * nz * ny
    rz = 2.0 * nz * nz - 1.0

    key = np.clip(0.5 + 0.5 * (-0.66 * rx - 0.73 * ry + 0.30 * rz), 0.0, 1.0)
    key = smootherstep(key)
    side = np.clip(0.5 + 0.5 * (0.46 * rx - 0.18 * ry + 0.10 * rz), 0.0, 1.0)
    horizon = np.exp(-np.square((rz + 0.05) / 0.26)).astype(np.float32)
    dark_room = np.clip(0.5 + 0.5 * (0.28 * rx + 0.58 * ry - 0.20 * rz), 0.0, 1.0)

    lum = 0.08 + 0.66 * key + 0.13 * side + 0.13 * horizon - 0.16 * dark_room
    return np.clip(lum, 0.035, 0.98).astype(np.float32)


def _fresnel(nz: np.ndarray, ior: float) -> np.ndarray:
    f0 = ((ior - 1.0) / (ior + 1.0)) ** 2
    c = np.clip(nz, 0.0, 1.0)
    return (f0 + (1.0 - f0) * np.power(1.0 - c, 5.0)).astype(np.float32)


def _specular(normal: np.ndarray, exponent: float) -> np.ndarray:
    light = np.array([-0.46, -0.72, 0.518], dtype=np.float32)
    light /= max(float(np.linalg.norm(light)), 1e-8)
    halfv = light + np.array([0.0, 0.0, 1.0], dtype=np.float32)
    halfv /= max(float(np.linalg.norm(halfv)), 1e-8)
    ndh = np.clip(
        normal[..., 0] * halfv[0] + normal[..., 1] * halfv[1] + normal[..., 2] * halfv[2],
        0.0,
        1.0,
    )
    return np.power(ndh, exponent).astype(np.float32)


def bake_static_rgba(maps: SurfaceMaps, params: MaterialParams = MaterialParams(), flags: BakeFlags = BakeFlags()) -> np.ndarray:
    cm = np.clip(maps.container_mask, 0.0, 1.0)
    gm = np.clip(maps.glyph_mask, 0.0, 1.0)

    tvals = maps.thickness[cm > 0.5]
    tmax = max(float(np.percentile(tvals, 99.0)) if tvals.size else 1.0, 1e-6)
    t = np.clip(maps.thickness / tmax, 0.0, 1.0)

    cfs = _norm01(maps.container_front_slope)
    cbs = _norm01(maps.container_back_slope)
    gfs = _norm01(maps.glyph_slope)

    env_front = _reflection_environment(maps.container_front_normals)
    env_back = _reflection_environment(maps.container_back_normals)
    env_full = _reflection_environment(maps.front_normals)
    env_full_back = _reflection_environment(maps.back_normals)

    fres_front = _fresnel(maps.container_front_normals[..., 2], params.ior)
    fres_back = _fresnel(np.abs(maps.container_back_normals[..., 2]), params.ior)
    fres_full = _fresnel(maps.front_normals[..., 2], params.ior)
    fres_full_back = _fresnel(np.abs(maps.back_normals[..., 2]), params.ior)

    # Broad curved surfaces. The weights deliberately occupy a visible area,
    # matching Apple's "thick optical shoulder" rather than a perimeter line.
    cfront_w = cm * np.clip(0.48 * np.sqrt(cfs) + 1.70 * fres_front, 0.0, 1.0)
    cback_w = cm * np.clip(0.40 * np.sqrt(cbs) + 1.28 * fres_back, 0.0, 1.0)

    full_slope = _norm01(maps.front_slope)
    back_slope = _norm01(maps.back_slope)
    glyph_front_delta = np.clip(full_slope - 0.36 * cfs, 0.0, 1.0) * gm
    glyph_back_delta = np.clip(back_slope - 0.30 * cbs, 0.0, 1.0) * gm
    glyph_front_w = gm * np.clip(0.58 * np.sqrt(glyph_front_delta) + 1.88 * fres_full, 0.0, 1.0)
    glyph_back_w = gm * np.clip(0.46 * np.sqrt(glyph_back_delta) + 1.42 * fres_full_back, 0.0, 1.0)

    radius = np.clip(maps.local_radius / 26.0, 0.0, 1.0)
    thin = (1.0 - smootherstep(np.clip((maps.local_radius - 2.5) / 11.0, 0.0, 1.0))) * gm

    premul = np.zeros((*cm.shape, 1), dtype=np.float32)
    alpha = np.zeros_like(cm, dtype=np.float32)

    # Clear but visible transmitted volume. The body luminance responds to the
    # analytic studio environment, so even no-specular has a curved glass mass.
    body_luma = np.clip(128.0 + 72.0 * (env_front - 0.5), 76.0, 186.0)
    body_alpha = params.container_body_response_alpha * cm * np.clip(0.30 + 0.70 * np.sqrt(t), 0.0, 1.0)
    premul, alpha = _over_gray(premul, alpha, params.container_core_alpha * cm, 128.0)
    premul, alpha = _over_gray(premul, alpha, params.container_thickness_alpha * np.sqrt(t) * cm, 108.0)
    premul, alpha = _over_gray(premul, alpha, body_alpha, body_luma)

    # Rear and front interfaces carry different normal-derived studio samples.
    premul, alpha = _over_gray(
        premul, alpha, params.container_back_alpha * cback_w,
        255.0 * np.clip(0.04 + 0.92 * env_back, 0.0, 1.0),
    )
    premul, alpha = _over_gray(
        premul, alpha, params.container_reflection_alpha * cfront_w,
        255.0 * np.clip(0.025 + 0.97 * env_front, 0.0, 1.0),
    )

    # An internal signed interface uses disagreement between front/back studio
    # responses as a direct thickness cue. This is an area field, not a border.
    internal_signed = np.clip(env_front - env_back, -1.0, 1.0)
    internal_luma = np.where(internal_signed >= 0.0, 232.0, 28.0)
    internal_w = params.container_internal_alpha * np.abs(internal_signed) * np.sqrt(np.clip(cfs * cbs, 0.0, 1.0)) * cm
    premul, alpha = _over_gray(premul, alpha, internal_w, internal_luma)

    # Secondary dielectric glyph: much denser than the shell, but still a
    # transparent volume whose body, front, rear, and internal interface differ.
    glyph_core = gm * (0.64 + 0.28 * radius)
    glyph_mass = gm * (0.35 + 0.65 * radius) * np.clip(0.32 + 0.68 * t, 0.0, 1.0)
    glyph_body_luma = np.clip(166.0 + 96.0 * (env_full - 0.5), 92.0, 238.0)
    glyph_body_w = params.glyph_body_response_alpha * gm * np.clip(0.42 + 0.58 * radius, 0.0, 1.0)

    premul, alpha = _over_gray(premul, alpha, params.glyph_core_alpha * glyph_core, 176.0)
    premul, alpha = _over_gray(premul, alpha, params.glyph_mass_alpha * glyph_mass, 132.0)
    premul, alpha = _over_gray(premul, alpha, glyph_body_w, glyph_body_luma)
    premul, alpha = _over_gray(premul, alpha, params.glyph_thin_boost * thin, 194.0)

    premul, alpha = _over_gray(
        premul, alpha, params.glyph_back_alpha * glyph_back_w,
        255.0 * np.clip(0.025 + 0.95 * env_full_back, 0.0, 1.0),
    )
    premul, alpha = _over_gray(
        premul, alpha, params.glyph_reflection_alpha * glyph_front_w,
        255.0 * np.clip(0.018 + 0.982 * env_full, 0.0, 1.0),
    )

    g_signed = np.clip(env_full - env_full_back, -1.0, 1.0)
    g_luma = np.where(g_signed >= 0.0, 246.0, 20.0)
    g_internal = params.glyph_internal_alpha * np.abs(g_signed) * np.sqrt(np.clip(glyph_front_delta * glyph_back_delta, 0.0, 1.0)) * gm
    premul, alpha = _over_gray(premul, alpha, g_internal, g_luma)

    if flags.explicit_rim:
        boundary = smootherstep(np.clip((maps.q - 0.966) / 0.034, 0.0, 1.0)) * cm
        premul, alpha = _over_gray(premul, alpha, params.hairline_alpha * boundary, 220.0)

    if flags.specular:
        csp = _specular(maps.container_front_normals, 44.0) * np.sqrt(cfs) * cm
        gsp = _specular(maps.front_normals, 36.0) * np.sqrt(np.clip(gfs + 0.45 * glyph_front_delta, 0.0, 1.0)) * gm
        premul, alpha = _over_gray(premul, alpha, params.sharp_specular_alpha * csp, 255.0)
        premul, alpha = _over_gray(premul, alpha, params.glyph_specular_alpha * gsp, 255.0)

    # No external drop shadow: V4 must retain depth with the no-shadow gate.
    alpha = np.clip(alpha, 0.0, 0.88)
    rgb = np.divide(
        premul[..., 0], np.maximum(alpha, 1e-6),
        out=np.full_like(alpha, 128.0), where=alpha > 1e-6,
    )
    rgb = np.where(cm > 1e-4, np.clip(rgb, 6.0, 252.0), 128.0)
    rgba = np.stack((rgb, rgb, rgb, alpha * 255.0), axis=-1)
    return np.clip(rgba, 0.0, 255.0).astype(np.uint8)
