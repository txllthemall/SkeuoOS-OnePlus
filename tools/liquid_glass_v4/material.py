from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .surface import SurfaceMaps, smootherstep


@dataclass(frozen=True)
class MaterialParams:
    ior: float = 1.50

    # Transmission stays clear; most material identity is carried by the
    # reflected neutral studio field and two independent front/back surfaces.
    container_core_alpha: float = 0.012
    container_thickness_alpha: float = 0.026
    container_reflection_alpha: float = 0.135
    container_back_alpha: float = 0.085

    glyph_core_alpha: float = 0.205
    glyph_mass_alpha: float = 0.095
    glyph_reflection_alpha: float = 0.175
    glyph_back_alpha: float = 0.115
    glyph_thin_boost: float = 0.050

    sharp_specular_alpha: float = 0.090
    glyph_specular_alpha: float = 0.130
    hairline_alpha: float = 0.010


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
    """Neutral studio environment sampled through the reflected view ray.

    This is not a decorative gradient. The broad light/dark field is evaluated
    from the actual surface normal, so curved corners and the glyph relief pick
    up different energy automatically. It is intentionally neutral because a
    production PNG must not bake wallpaper hue.
    """
    nx, ny, nz = normal[..., 0], normal[..., 1], normal[..., 2]
    # Reflection of V=(0,0,1) about N: R = 2(N·V)N - V.
    rx = 2.0 * nz * nx
    ry = 2.0 * nz * ny
    rz = 2.0 * nz * nz - 1.0

    # Soft upper-left lightbox plus darker lower-right room. Values are studio
    # luminance, not an icon-specific highlight mask.
    key = np.clip(0.5 + 0.5 * (-0.62 * rx - 0.70 * ry + 0.34 * rz), 0.0, 1.0)
    key = smootherstep(key)
    fill = np.clip(0.5 + 0.5 * (0.38 * rx - 0.22 * ry + 0.16 * rz), 0.0, 1.0)
    horizon = np.exp(-np.square((rz + 0.03) / 0.30)).astype(np.float32)
    lum = 0.20 + 0.52 * key + 0.12 * fill + 0.10 * horizon
    return np.clip(lum, 0.08, 0.96).astype(np.float32)


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
    gbs = _norm01(maps.glyph_back_slope)

    env_front = _reflection_environment(maps.container_front_normals)
    env_back = _reflection_environment(maps.container_back_normals)
    env_full = _reflection_environment(maps.front_normals)
    env_full_back = _reflection_environment(maps.back_normals)

    fres_front = _fresnel(maps.container_front_normals[..., 2], params.ior)
    fres_back = _fresnel(np.abs(maps.container_back_normals[..., 2]), params.ior)
    fres_full = _fresnel(maps.front_normals[..., 2], params.ior)
    fres_full_back = _fresnel(np.abs(maps.back_normals[..., 2]), params.ior)

    # Broad curved optical shoulders. These are area responses, not perimeter
    # strokes: slope determines coverage, Fresnel determines intensity.
    cfront_w = cm * np.clip(0.26 * cfs + 1.35 * fres_front, 0.0, 1.0)
    cback_w = cm * np.clip(0.22 * cbs + 1.00 * fres_back, 0.0, 1.0)

    # The glyph is a secondary volume. Use the difference between combined and
    # container surfaces so its interfaces stay local to the Octocat geometry.
    glyph_front_delta = np.clip(_norm01(maps.front_slope) - 0.42 * cfs, 0.0, 1.0) * gm
    glyph_back_delta = np.clip(_norm01(maps.back_slope) - 0.36 * cbs, 0.0, 1.0) * gm
    glyph_front_w = gm * np.clip(0.30 * glyph_front_delta + 1.55 * fres_full, 0.0, 1.0)
    glyph_back_w = gm * np.clip(0.26 * glyph_back_delta + 1.10 * fres_full_back, 0.0, 1.0)

    radius = np.clip(maps.local_radius / 26.0, 0.0, 1.0)
    thin = (1.0 - smootherstep(np.clip((maps.local_radius - 2.5) / 11.0, 0.0, 1.0))) * gm

    premul = np.zeros((*cm.shape, 1), dtype=np.float32)
    alpha = np.zeros_like(cm, dtype=np.float32)

    # Transmission body. Equal-channel neutral density is intentionally tiny in
    # the shell and substantially stronger in the secondary glyph volume.
    premul, alpha = _over_gray(premul, alpha, params.container_core_alpha * cm, 128.0)
    premul, alpha = _over_gray(premul, alpha, params.container_thickness_alpha * np.sqrt(t) * cm, 116.0)

    # Independent rear surface first. A reflected studio field naturally gives
    # both bright and dark cues, avoiding the old artificial two-outline look.
    premul, alpha = _over_gray(
        premul,
        alpha,
        params.container_back_alpha * cback_w,
        255.0 * np.clip(0.10 + 0.82 * env_back, 0.0, 1.0),
    )
    premul, alpha = _over_gray(
        premul,
        alpha,
        params.container_reflection_alpha * cfront_w,
        255.0 * np.clip(0.08 + 0.90 * env_front, 0.0, 1.0),
    )

    # Glyph optical mass. Core remains translucent but is deliberately dense
    # enough to survive 64–96 px launcher rendering on muted wallpapers.
    glyph_core = gm * (0.58 + 0.24 * radius)
    glyph_mass = gm * (0.30 + 0.70 * radius) * np.clip(0.38 + 0.62 * t, 0.0, 1.0)
    premul, alpha = _over_gray(premul, alpha, params.glyph_core_alpha * glyph_core, 152.0)
    premul, alpha = _over_gray(premul, alpha, params.glyph_mass_alpha * glyph_mass, 132.0)
    premul, alpha = _over_gray(premul, alpha, params.glyph_thin_boost * thin, 170.0)

    premul, alpha = _over_gray(
        premul,
        alpha,
        params.glyph_back_alpha * glyph_back_w,
        255.0 * np.clip(0.08 + 0.88 * env_full_back, 0.0, 1.0),
    )
    premul, alpha = _over_gray(
        premul,
        alpha,
        params.glyph_reflection_alpha * glyph_front_w,
        255.0 * np.clip(0.06 + 0.94 * env_full, 0.0, 1.0),
    )

    if flags.explicit_rim:
        # Only a subpixel stabilizer at the analytic silhouette. It must never
        # be the reason the object reads as glass.
        boundary = np.clip((maps.q - 0.970) / 0.030, 0.0, 1.0)
        boundary = smootherstep(boundary) * cm
        premul, alpha = _over_gray(premul, alpha, params.hairline_alpha * boundary, 210.0)

    if flags.specular:
        csp = _specular(maps.container_front_normals, 54.0) * cfs * cm
        gsp = _specular(maps.front_normals, 44.0) * np.clip(gfs + 0.55 * glyph_front_delta, 0.0, 1.0) * gm
        premul, alpha = _over_gray(premul, alpha, params.sharp_specular_alpha * csp, 255.0)
        premul, alpha = _over_gray(premul, alpha, params.glyph_specular_alpha * gsp, 255.0)

    # No external drop shadow. The flag exists only for the architecture gate.
    alpha = np.clip(alpha, 0.0, 0.80)
    rgb = np.divide(
        premul[..., 0],
        np.maximum(alpha, 1e-6),
        out=np.full_like(alpha, 128.0),
        where=alpha > 1e-6,
    )
    rgb = np.where(cm > 1e-4, np.clip(rgb, 8.0, 250.0), 128.0)
    rgba = np.stack((rgb, rgb, rgb, alpha * 255.0), axis=-1)
    return np.clip(rgba, 0.0, 255.0).astype(np.uint8)
