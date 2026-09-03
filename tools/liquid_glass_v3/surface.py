from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np
from PIL import Image, ImageDraw

FloatMap = np.ndarray


@dataclass(frozen=True)
class SurfaceParams:
    # Broad curved shell. The exact silhouette boundary is no longer a height
    # discontinuity: front/back surfaces taper continuously to the outline.
    edge_width_px: float = 82.0
    boundary_taper_px: float = 13.0
    center_height: float = 0.78
    edge_height: float = 0.018

    # True optical thickness is zero at the silhouette, swells just inside the
    # curved lip, then settles to a thinner clear core. This replaces the old
    # "maximum thickness at the final pixel" shape that generated derivative
    # spikes and made refraction look torn.
    back_depth: float = 0.235
    edge_thickness_gain: float = 0.275
    edge_thickness_peak: float = 0.30
    edge_thickness_width: float = 0.19

    # Glyph is a second volume, also tapered continuously at its own boundary.
    glyph_relief: float = 0.205
    glyph_mass_gain: float = 0.325
    glyph_bevel_width_px: float = 20.0
    glyph_boundary_taper_px: float = 4.5
    normal_scale: float = 2.10


@dataclass
class SurfaceMaps:
    container_mask: FloatMap
    glyph_mask: FloatMap
    container_sdf: FloatMap
    glyph_sdf: FloatMap

    container_profile: FloatMap
    container_back_profile: FloatMap
    glyph_profile: FloatMap
    glyph_back_profile: FloatMap

    glyph_relief_map: FloatMap
    glyph_back_relief_map: FloatMap

    front_height: FloatMap
    back_height: FloatMap
    thickness: FloatMap

    normals: FloatMap
    front_normals: FloatMap
    back_normals: FloatMap
    slope: FloatMap
    front_slope: FloatMap
    back_slope: FloatMap

    container_slope: FloatMap
    container_back_slope: FloatMap
    glyph_slope: FloatMap
    glyph_back_slope: FloatMap

    curvature: FloatMap
    back_curvature: FloatMap
    local_radius: FloatMap


def smootherstep(x: FloatMap) -> FloatMap:
    x = np.clip(x, 0.0, 1.0).astype(np.float32)
    return x * x * x * (x * (x * 6.0 - 15.0) + 10.0)


def squircle_mask(size: int, margin: float = 0.105, radius: float = 0.235) -> Image.Image:
    """Launcher-like rounded square mask used only as V3 geometry input."""
    px = int(round(size * margin))
    r = int(round(size * radius))
    im = Image.new("L", (size, size), 0)
    ImageDraw.Draw(im).rounded_rectangle((px, px, size - px - 1, size - px - 1), radius=r, fill=255)
    return im


def _edt_1d(f: np.ndarray) -> np.ndarray:
    """Felzenszwalb/Huttenlocher squared Euclidean distance transform, 1D."""
    n = int(f.shape[0])
    v = np.zeros(n, dtype=np.int32)
    z = np.zeros(n + 1, dtype=np.float64)
    d = np.zeros(n, dtype=np.float64)
    k = 0
    v[0] = 0
    z[0] = -np.inf
    z[1] = np.inf
    for q in range(1, n):
        fq = float(f[q])
        while True:
            vk = int(v[k])
            s = ((fq + q * q) - (float(f[vk]) + vk * vk)) / (2.0 * (q - vk))
            if s > z[k]:
                break
            k -= 1
            if k < 0:
                k = 0
                break
        k += 1
        v[k] = q
        z[k] = s
        z[k + 1] = np.inf
    k = 0
    for q in range(n):
        while z[k + 1] < q:
            k += 1
        vk = int(v[k])
        d[q] = (q - vk) * (q - vk) + float(f[vk])
    return d


def _distance_to_true(seed: np.ndarray) -> FloatMap:
    inf = 1.0e12
    f = np.where(seed, 0.0, inf).astype(np.float64)
    h, w = f.shape
    g = np.empty_like(f)
    for x in range(w):
        g[:, x] = _edt_1d(f[:, x])
    d2 = np.empty_like(g)
    for y in range(h):
        d2[y, :] = _edt_1d(g[y, :])
    return np.sqrt(np.maximum(d2, 0.0)).astype(np.float32)


def signed_distance(mask: FloatMap) -> FloatMap:
    inside = mask > 0.5
    dist_out = _distance_to_true(~inside)
    dist_in = _distance_to_true(inside)
    return np.where(inside, dist_out, -dist_in).astype(np.float32)


def _central_gradient(a: FloatMap) -> Tuple[FloatMap, FloatMap]:
    gx = np.zeros_like(a, dtype=np.float32)
    gy = np.zeros_like(a, dtype=np.float32)
    gx[:, 1:-1] = 0.5 * (a[:, 2:] - a[:, :-2])
    gx[:, 0] = a[:, 1] - a[:, 0]
    gx[:, -1] = a[:, -1] - a[:, -2]
    gy[1:-1, :] = 0.5 * (a[2:, :] - a[:-2, :])
    gy[0, :] = a[1, :] - a[0, :]
    gy[-1, :] = a[-1, :] - a[-2, :]
    return gx, gy


def height_to_normals(height: FloatMap, z_scale: float) -> FloatMap:
    gx, gy = _central_gradient(height)
    n = np.stack((-z_scale * gx, -z_scale * gy, np.ones_like(height)), axis=-1)
    length = np.linalg.norm(n, axis=-1, keepdims=True)
    return (n / np.maximum(length, 1e-8)).astype(np.float32)


def _slope(a: FloatMap) -> FloatMap:
    gx, gy = _central_gradient(a)
    return np.sqrt(gx * gx + gy * gy).astype(np.float32)


def _curvature(height: FloatMap) -> FloatMap:
    gx, gy = _central_gradient(height)
    gxx, _ = _central_gradient(gx)
    _, gyy = _central_gradient(gy)
    return (gxx + gyy).astype(np.float32)


def _img_to_mask(im: Image.Image, size: int) -> FloatMap:
    return np.asarray(im.convert("L").resize((size, size), Image.Resampling.LANCZOS), dtype=np.float32) / 255.0


def _interior_crown(sdf: FloatMap, mask: FloatMap) -> FloatMap:
    positive = np.maximum(sdf, 0.0)
    vals = positive[mask > 0.5]
    max_d = float(np.percentile(vals, 99.0)) if vals.size else 1.0
    max_d = max(max_d, 1.0)
    return smootherstep(np.clip(positive / (0.92 * max_d), 0.0, 1.0)) * (mask > 0.01)


def _effective_inside_distance(sdf: FloatMap) -> FloatMap:
    """Approximate distance from the continuous half-pixel silhouette.

    A binary EDT reports about one pixel for the first interior pixel. Removing
    0.75 px makes our geometric fields converge toward zero at the true vector
    boundary rather than jumping between the last outside and first inside texel.
    """
    return np.maximum(sdf - 0.75, 0.0).astype(np.float32)


def _gaussian_lobe(x: FloatMap, center: float, width: float) -> FloatMap:
    width = max(float(width), 1e-4)
    return np.exp(-0.5 * np.square((x - float(center)) / width)).astype(np.float32)


def build_surface_maps(
    container_mask: Image.Image,
    glyph_mask: Image.Image,
    params: SurfaceParams = SurfaceParams(),
    *,
    size: int | None = None,
) -> SurfaceMaps:
    if size is None:
        size = container_mask.size[0]

    cm = _img_to_mask(container_mask, size)
    gm = _img_to_mask(glyph_mask, size)
    csdf = signed_distance(cm)
    gsdf = signed_distance(gm)

    # ------------------------------------------------------------------ shell
    # Build a continuous convex front surface. Both height and thickness taper
    # at the true outline, so front/back normals describe a rounded volume rather
    # than two fields with discontinuous cliffs at the alpha mask boundary.
    positive_c = _effective_inside_distance(csdf)
    edge_u = np.clip(positive_c / max(params.edge_width_px, 1e-3), 0.0, 1.0)
    edge_profile = smootherstep(edge_u)
    boundary_taper = smootherstep(
        np.clip(positive_c / max(params.boundary_taper_px, 1e-3), 0.0, 1.0)
    )
    crown = _interior_crown(csdf, cm)

    cprof_raw = np.clip(0.69 * edge_profile + 0.31 * crown, 0.0, 1.0)
    cprof = (boundary_taper * cprof_raw * (cm > 0.01)).astype(np.float32)
    container_front = (
        boundary_taper
        * (params.edge_height + (params.center_height - params.edge_height) * cprof_raw)
        * (cm > 0.01)
    ).astype(np.float32)

    # Thickness is a real field. The exact silhouette tends to zero; a broad
    # subsurface lobe supplies the optically thick curved lip; the clear core
    # settles to `back_depth` instead of remaining maximally dense everywhere.
    lip = _gaussian_lobe(edge_u, params.edge_thickness_peak, params.edge_thickness_width)
    base_thickness = (
        boundary_taper
        * (params.back_depth + params.edge_thickness_gain * lip)
        * (cm > 0.01)
    ).astype(np.float32)
    container_back = (container_front - base_thickness).astype(np.float32)
    container_back = np.where(cm > 0.01, container_back, 0.0).astype(np.float32)

    max_t = max(params.back_depth + params.edge_thickness_gain, 1e-6)
    back_prof = np.clip(base_thickness / max_t, 0.0, 1.0).astype(np.float32)

    # --------------------------------------------------------------- glyph lens
    # The secondary dielectric receives the same continuity treatment. This is
    # important at launcher scale: a hard relief cliff looks embossed/plastic;
    # a tapered height/mass field reads as a small transparent optical insert.
    positive_g = _effective_inside_distance(gsdf)
    gu = np.clip(positive_g / max(params.glyph_bevel_width_px, 1e-3), 0.0, 1.0)
    g_edge_profile = smootherstep(gu)
    g_taper = smootherstep(
        np.clip(positive_g / max(params.glyph_boundary_taper_px, 1e-3), 0.0, 1.0)
    )
    g_crown = _interior_crown(gsdf, gm)
    gprof_raw = np.clip(0.72 * g_edge_profile + 0.28 * g_crown, 0.0, 1.0)
    gprof = (g_taper * gprof_raw * (gm > 0.01)).astype(np.float32)

    # Rear glyph mass is deliberately broader than the front relief, giving a
    # thick optical insert without a bright flat fill.
    gback_u = np.clip(positive_g / max(params.glyph_bevel_width_px * 1.34, 1e-3), 0.0, 1.0)
    gback_edge = smootherstep(gback_u)
    gback_raw = np.clip(0.62 * gback_edge + 0.38 * g_crown, 0.0, 1.0)
    gback_prof = (g_taper * gback_raw * (gm > 0.01)).astype(np.float32)

    glyph_relief_map = (params.glyph_relief * gprof).astype(np.float32)
    glyph_mass_map = (params.glyph_mass_gain * gback_prof).astype(np.float32)

    front = (container_front + glyph_relief_map).astype(np.float32)
    thickness = (base_thickness + glyph_mass_map).astype(np.float32)
    back = np.where(cm > 0.01, front - thickness, 0.0).astype(np.float32)
    glyph_back_relief_map = ((back - container_back) * gm).astype(np.float32)

    front_normals = height_to_normals(front, params.normal_scale)
    back_normals = height_to_normals(back, params.normal_scale)

    front_slope = _slope(front)
    back_slope = _slope(back)
    container_slope = _slope(container_front)
    container_back_slope = _slope(container_back)
    glyph_slope = _slope(glyph_relief_map)
    glyph_back_slope = _slope(glyph_back_relief_map)

    curvature = _curvature(front)
    back_curvature = _curvature(back)
    local_radius = np.where(gm > 0.5, np.maximum(gsdf, 0.0), 0.0).astype(np.float32)

    return SurfaceMaps(
        container_mask=cm,
        glyph_mask=gm,
        container_sdf=csdf,
        glyph_sdf=gsdf,
        container_profile=cprof,
        container_back_profile=back_prof,
        glyph_profile=gprof,
        glyph_back_profile=gback_prof,
        glyph_relief_map=glyph_relief_map,
        glyph_back_relief_map=glyph_back_relief_map,
        front_height=front,
        back_height=back,
        thickness=thickness,
        normals=front_normals,
        front_normals=front_normals,
        back_normals=back_normals,
        slope=front_slope,
        front_slope=front_slope,
        back_slope=back_slope,
        container_slope=container_slope,
        container_back_slope=container_back_slope,
        glyph_slope=glyph_slope,
        glyph_back_slope=glyph_back_slope,
        curvature=curvature,
        back_curvature=back_curvature,
        local_radius=local_radius,
    )
