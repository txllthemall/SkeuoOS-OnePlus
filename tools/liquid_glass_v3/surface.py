from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np
from PIL import Image, ImageDraw

FloatMap = np.ndarray


@dataclass(frozen=True)
class SurfaceParams:
    # The V3 shell is intentionally a broad optical volume, not a narrow bevel.
    edge_width_px: float = 78.0
    center_height: float = 0.74
    edge_height: float = 0.08

    # Back surface is derived independently through a varying thickness field.
    # The material is thinner through the clear core and substantially thicker
    # near grazing edges, which gives the baker a real second interface.
    back_depth: float = 0.22
    edge_thickness_gain: float = 0.34

    # Glyph is a second volume. Its front surface rises while its back surface
    # is slightly recessed because mass gain is greater than front relief.
    glyph_relief: float = 0.20
    glyph_mass_gain: float = 0.31
    glyph_bevel_width_px: float = 18.0
    normal_scale: float = 2.20


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

    # `normals` and `slope` remain aliases for the front surface so existing
    # diagnostics keep working, while V3 material can use both interfaces.
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
    """Exact Euclidean distance in pixels to nearest True seed."""
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
    """Low-frequency convex crown over the full interior, not just the rim."""
    positive = np.maximum(sdf, 0.0)
    vals = positive[mask > 0.5]
    max_d = float(np.percentile(vals, 99.0)) if vals.size else 1.0
    max_d = max(max_d, 1.0)
    return smootherstep(np.clip(positive / (0.92 * max_d), 0.0, 1.0)) * (mask > 0.01)


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

    # Front shell = broad edge curvature plus a weak full-body crown. This
    # removes the V2/V3-alpha "flat plateau surrounded by a rim" failure mode.
    positive_c = np.maximum(csdf, 0.0)
    edge_u = np.clip(positive_c / max(params.edge_width_px, 1e-3), 0.0, 1.0)
    edge_profile = smootherstep(edge_u)
    crown = _interior_crown(csdf, cm)
    cprof = np.clip(0.74 * edge_profile + 0.26 * crown, 0.0, 1.0) * (cm > 0.01)

    container_front = np.where(
        cm > 0.01,
        params.edge_height + (params.center_height - params.edge_height) * cprof,
        0.0,
    ).astype(np.float32)

    # Back interface follows a wider, softer profile. Its varying separation
    # from the front surface produces real thickness gradients instead of a
    # fake second outline.
    back_u = np.clip(positive_c / max(params.edge_width_px * 1.34, 1e-3), 0.0, 1.0)
    back_edge_profile = smootherstep(back_u)
    back_prof = np.clip(0.64 * back_edge_profile + 0.36 * crown, 0.0, 1.0) * (cm > 0.01)
    base_thickness = params.back_depth + params.edge_thickness_gain * (1.0 - back_prof)
    container_back = np.where(cm > 0.01, container_front - base_thickness, 0.0).astype(np.float32)

    # Glyph is an independent secondary volume. The back-interface relief is
    # negative because glyph_mass_gain > glyph_relief; this makes the mark a
    # real lens/body rather than a bright emboss painted on the shell.
    positive_g = np.maximum(gsdf, 0.0)
    gu = np.clip(positive_g / max(params.glyph_bevel_width_px, 1e-3), 0.0, 1.0)
    g_edge_profile = smootherstep(gu)
    g_crown = _interior_crown(gsdf, gm)
    gprof = np.clip(0.72 * g_edge_profile + 0.28 * g_crown, 0.0, 1.0) * (gm > 0.01)

    gback_u = np.clip(positive_g / max(params.glyph_bevel_width_px * 1.28, 1e-3), 0.0, 1.0)
    gback_edge = smootherstep(gback_u)
    gback_prof = np.clip(0.62 * gback_edge + 0.38 * g_crown, 0.0, 1.0) * (gm > 0.01)

    glyph_relief_map = (params.glyph_relief * gprof).astype(np.float32)
    glyph_mass_map = (params.glyph_mass_gain * gback_prof).astype(np.float32)

    front = container_front + glyph_relief_map
    thickness = np.where(cm > 0.01, base_thickness, 0.0).astype(np.float32) + glyph_mass_map
    back = np.where(cm > 0.01, front - thickness, 0.0).astype(np.float32)
    glyph_back_relief_map = (back - container_back) * gm

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
        container_profile=cprof.astype(np.float32),
        container_back_profile=back_prof.astype(np.float32),
        glyph_profile=gprof.astype(np.float32),
        glyph_back_profile=gback_prof.astype(np.float32),
        glyph_relief_map=glyph_relief_map,
        glyph_back_relief_map=glyph_back_relief_map.astype(np.float32),
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
